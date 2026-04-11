"""
YouTube 채널 트래커 — 해외 쇼츠 채널 발굴 및 일별 통계 수집
두 가지 모드:
  discover : 키워드로 새 채널 탐색 → watched_channels 에 추가
  update   : 기존 채널 통계 갱신 → channel_daily_stats 에 저장
"""
import os
import re
import sys
from datetime import date, timedelta

from googleapiclient.discovery import build
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

load_dotenv()

MAX_CHANNELS = 300  # 전체 채널 상한

# ── 카테고리/서브카테고리별 탐색 설정 (keyword, regionCode) ────────────────
DISCOVERY_CONFIG = {
    "engineering": {
        "산업/중장비": [
            ("heavy equipment machine shorts", "US"),
            ("mining truck industrial process", "US"),
            ("重機 工場 機械", "JP"),
        ],
        "공학/기계": [
            ("mechanical engineering explained shorts", "US"),
            ("how machines work principles", "US"),
            ("機械 仕組み 解説", "JP"),
        ],
        "밀리터리": [
            ("military weapons technology shorts", "US"),
            ("fighter jet secrets military equipment", "US"),
            ("軍事 兵器 技術 解説", "JP"),
        ],
        "소방/안전": [
            ("firefighter equipment secrets shorts", "US"),
            ("fire rescue technology safety", "US"),
            ("消防 救助 技術", "JP"),
        ],
        "과학/자연": [
            ("science experiment amazing shorts", "US"),
            ("physics chemistry explained simple", "US"),
            ("科学 実験 解説", "JP"),
        ],
    },
    "gaming": {
        "게임 로어/세계관": [
            ("video game lore explained shorts", "US"),
            ("game story lore secrets shorts", "US"),
        ],
        "게임 비하인드": [
            ("video game development secrets shorts", "US"),
            ("game dev behind scenes facts", "US"),
        ],
        "게임 이스터에그": [
            ("video game easter eggs shorts", "US"),
            ("hidden game secrets discovered shorts", "US"),
        ],
        "게임 역사": [
            ("video game history facts shorts", "US"),
            ("retro gaming history explained", "US"),
        ],
    },
    "baseball": {
        "MLB 하이라이트": [
            ("MLB highlights amazing moments shorts", "US"),
            ("baseball best plays catches shorts", "US"),
        ],
        "야구 역사/기록": [
            ("baseball history records facts shorts", "US"),
            ("MLB legendary moments history shorts", "US"),
        ],
        "야구 팩트/분석": [
            ("baseball facts you didn't know shorts", "US"),
            ("MLB stats analysis explained shorts", "US"),
        ],
    },
}


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    return build("youtube", "v3", developerKey=api_key)


def parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


# ── 채널 발굴 ─────────────────────────────────────────────────────────

def search_channels(youtube, keyword: str, country: str, max_results: int = 10) -> list[dict]:
    try:
        resp = youtube.search().list(
            part="snippet",
            type="channel",
            q=keyword,
            regionCode=country,
            maxResults=max_results,
        ).execute()
        return resp.get("items", [])
    except Exception as e:
        print(f"  [오류] 채널 검색 실패 ({keyword}): {e}")
        return []


def fetch_channel_info(youtube, channel_ids: list[str]) -> list[dict]:
    if not channel_ids:
        return []
    try:
        resp = youtube.channels().list(
            part="snippet,statistics",
            id=",".join(channel_ids),
            maxResults=50,
        ).execute()
        return resp.get("items", [])
    except Exception as e:
        print(f"  [오류] 채널 정보 조회 실패: {e}")
        return []


def remove_low_performers(client, n: int) -> int:
    """조회수 증가량 하위 채널 n개 제거 (즐겨찾기·통계없는 신규 채널 제외)"""
    if n <= 0:
        return 0

    week_ago = (date.today() - timedelta(days=7)).isoformat()

    stats = (
        client.table("channel_daily_stats")
        .select("channel_id,view_increase")
        .gte("collected_date", week_ago)
        .execute()
        .data
    )

    # 채널별 7일 평균 조회수 증가량
    sums: dict[str, int] = {}
    counts: dict[str, int] = {}
    for row in stats:
        cid = row["channel_id"]
        sums[cid] = sums.get(cid, 0) + int(row.get("view_increase", 0))
        counts[cid] = counts.get(cid, 0) + 1
    avg = {cid: sums[cid] / counts[cid] for cid in sums}

    # 즐겨찾기가 아닌 채널 중 통계가 있는 것만 대상
    all_channels = (
        client.table("watched_channels")
        .select("channel_id,is_favorite")
        .execute()
        .data
    )
    removable = [
        ch["channel_id"] for ch in all_channels
        if not ch.get("is_favorite") and ch["channel_id"] in avg
    ]

    # 평균 조회수 증가량 오름차순 → 하위부터 제거
    removable.sort(key=lambda cid: avg.get(cid, 0))
    to_remove = removable[:n]

    if to_remove:
        client.table("watched_channels").delete().in_("channel_id", to_remove).execute()
        print(f"  → 하위 채널 {len(to_remove)}개 제거 (7일 평균 조회수 증가 기준)")

    return len(to_remove)


def discover(category: str = "engineering", max_per_keyword: int = 5):
    """새 채널 발굴 — 300개 상한 초과 시 하위 채널 자동 교체"""
    client = get_client()
    youtube = get_youtube_client()

    existing = {r["channel_id"] for r in client.table("watched_channels").select("channel_id").execute().data}

    cat_config = DISCOVERY_CONFIG.get(category, {})
    if not cat_config:
        print(f"  [오류] 알 수 없는 카테고리: {category}")
        return 0

    added_total = 0

    for subcategory, searches in cat_config.items():
        print(f"\n  [{subcategory}] 채널 탐색 중...")
        found_ids: set[str] = set()

        for keyword, country in searches:
            items = search_channels(youtube, keyword, country, max_results=max_per_keyword)
            for item in items:
                cid = item["snippet"]["channelId"]
                if cid not in existing:
                    found_ids.add(cid)

        if not found_ids:
            print(f"  → 신규 채널 없음")
            continue

        channels = fetch_channel_info(youtube, list(found_ids))
        rows = []
        for ch in channels:
            cid = ch["id"]
            snippet = ch.get("snippet", {})
            ch_country = snippet.get("country", "US")
            rows.append({
                "channel_id":    cid,
                "channel_name":  snippet.get("title", ""),
                "handle":        snippet.get("customUrl", ""),
                "country":       ch_country,
                "category":      category,
                "subcategory":   subcategory,
                "thumbnail_url": (snippet.get("thumbnails", {}).get("default", {}) or {}).get("url", ""),
            })

        if rows:
            # 상한 초과 시 하위 채널 먼저 제거
            current_count = len(existing)
            overflow = (current_count + len(rows)) - MAX_CHANNELS
            if overflow > 0:
                print(f"  채널 상한({MAX_CHANNELS}) 초과 예상 → 하위 {overflow}개 제거 중...")
                removed = remove_low_performers(client, overflow)
                existing = {r["channel_id"] for r in client.table("watched_channels").select("channel_id").execute().data}

            client.table("watched_channels").upsert(rows, on_conflict="channel_id").execute()
            added_total += len(rows)
            existing.update(r["channel_id"] for r in rows)
            print(f"  → {len(rows)}개 채널 추가")

    print(f"\n채널 발굴 완료: 총 {added_total}개 신규 추가")
    return added_total


# ── 일별 통계 갱신 ────────────────────────────────────────────────────

def fetch_recent_shorts(youtube, channel_id: str, max_results: int = 5) -> list[dict]:
    """playlistItems.list 사용 (2 유닛/채널, search.list 대비 50배 절약)"""
    try:
        # 업로드 플레이리스트 ID: UC→UU 치환
        uploads_playlist_id = "UU" + channel_id[2:]

        resp = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results * 3,  # Shorts 필터 후 max_results 보장
        ).execute()

        items = resp.get("items", [])
        if not items:
            return []

        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in items]

        detail_resp = youtube.videos().list(
            part="contentDetails,snippet",
            id=",".join(video_ids),
        ).execute()

        shorts = []
        for v in detail_resp.get("items", []):
            dur = parse_duration(v.get("contentDetails", {}).get("duration", ""))
            if dur <= 60:
                snippet = v.get("snippet", {})
                thumb = (snippet.get("thumbnails", {}).get("medium", {}) or {}).get("url", "")
                shorts.append({
                    "video_id":         v["id"],
                    "channel_id":       channel_id,
                    "title":            snippet.get("title", ""),
                    "thumbnail_url":    thumb,
                    "published_at":     snippet.get("publishedAt", ""),
                    "duration_seconds": dur,
                })
                if len(shorts) >= max_results:
                    break
        return shorts
    except Exception as e:
        print(f"  [오류] 쇼츠 조회 실패 ({channel_id}): {e}")
        return []


def update():
    """등록된 모든 채널 통계를 오늘 날짜로 갱신"""
    client = get_client()
    youtube = get_youtube_client()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    channels = client.table("watched_channels").select("channel_id,channel_name,subcategory").execute().data

    if not channels:
        print("  등록된 채널이 없습니다. 먼저 discover 모드를 실행하세요.")
        return 0

    print(f"  {len(channels)}개 채널 통계 갱신 중...")

    yesterday_stats = {}
    y_rows = (
        client.table("channel_daily_stats")
        .select("channel_id,subscriber_count,total_views")
        .eq("collected_date", yesterday)
        .execute()
        .data
    )
    for r in y_rows:
        yesterday_stats[r["channel_id"]] = r

    channel_ids = [ch["channel_id"] for ch in channels]
    all_channel_info = []
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        all_channel_info.extend(fetch_channel_info(youtube, batch))

    stat_rows = []
    for ch_info in all_channel_info:
        cid = ch_info["id"]
        stats = ch_info.get("statistics", {})
        subs  = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        vids  = int(stats.get("videoCount", 0))

        prev = yesterday_stats.get(cid, {})
        sub_inc  = subs  - int(prev.get("subscriber_count", subs))
        view_inc = views - int(prev.get("total_views", views))

        stat_rows.append({
            "channel_id":          cid,
            "collected_date":      today,
            "subscriber_count":    subs,
            "total_views":         views,
            "video_count":         vids,
            "subscriber_increase": sub_inc,
            "view_increase":       view_inc,
        })

    if stat_rows:
        client.table("channel_daily_stats").upsert(
            stat_rows, on_conflict="channel_id,collected_date"
        ).execute()

    shorts_rows = []
    for ch in channels:
        shorts = fetch_recent_shorts(youtube, ch["channel_id"])
        shorts_rows.extend(shorts)

    if shorts_rows:
        client.table("channel_recent_shorts").upsert(
            shorts_rows, on_conflict="video_id"
        ).execute()

    print(f"  → {len(stat_rows)}개 채널 통계, {len(shorts_rows)}개 쇼츠 저장")
    return len(stat_rows)


def run(category: str = "engineering", mode: str = "update"):
    if mode == "discover":
        print(f"[채널 발굴] 카테고리={category}")
        return discover(category)
    else:
        print(f"[채널 통계 갱신] 전체 채널")
        return update()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "update"
    category = sys.argv[2] if len(sys.argv) > 2 else "engineering"
    run(category=category, mode=mode)
