"""
YouTube 크롤러 — 국가별 급상승 영상 수집 (KR / JP / US)
YouTube Data API v3 사용
"""
import os
import sys
from datetime import date

from googleapiclient.discovery import build
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

load_dotenv()

# 카테고리별 YouTube 카테고리 ID
YOUTUBE_CATEGORY_IDS = {
    "gaming":      "20",  # 게임
    "movies":      "1",   # 영화 & 애니메이션
    "it_gadgets":  "28",  # 과학 & 기술
    "engineering": "28",  # 과학 & 기술 (공학/과학 카테고리)
}

COUNTRIES = ["KR", "JP", "US"]


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    return build("youtube", "v3", developerKey=api_key)


def fetch_trending(youtube, region: str, category_id: str, max_results: int = 30) -> list[dict]:
    try:
        response = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=region,
            videoCategoryId=category_id,
            maxResults=max_results,
        ).execute()
        return response.get("items", [])
    except Exception as e:
        print(f"  [오류] {region} 급상승 조회 실패: {e}")
        # 카테고리 필터 없이 재시도 (해당 국가에 카테고리 데이터 없을 수 있음)
        try:
            response = youtube.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=region,
                maxResults=max_results,
            ).execute()
            return response.get("items", [])
        except Exception as e2:
            print(f"  [오류] {region} 재시도 실패: {e2}")
            return []


def save_videos(videos: list[dict], country: str, period: str, category: str) -> int:
    client = get_client()
    today = date.today().isoformat()
    rows = []

    for v in videos:
        stats = v.get("statistics", {})
        snippet = v.get("snippet", {})
        rows.append({
            "video_id":      v["id"],
            "title":         snippet.get("title", ""),
            "channel_name":  snippet.get("channelTitle", ""),
            "country":       country,
            "period":        period,
            "views":         int(stats.get("viewCount", 0)),
            "view_increase": 0,   # 초기값 0, 나중에 이전 데이터와 비교해 계산
            "category":      category,
            "collected_date": today,
        })

    if not rows:
        return 0

    # 같은 날짜·영상·기간이면 업데이트 (upsert)
    client.table("youtube_videos").upsert(
        rows, on_conflict="video_id,period,collected_date"
    ).execute()
    return len(rows)


def run(category: str = "gaming", countries: list = None, period: str = "daily"):
    if countries is None:
        countries = COUNTRIES

    category_id = YOUTUBE_CATEGORY_IDS.get(category, "20")
    youtube = get_youtube_client()
    total = 0

    for country in countries:
        print(f"  [{country}] 급상승 영상 수집 중...")
        videos = fetch_trending(youtube, country, category_id)
        saved = save_videos(videos, country, period, category)
        total += saved
        print(f"  → {saved}개 저장 완료")

    print(f"YouTube 크롤링 완료: 총 {total}개 저장")
    return total


if __name__ == "__main__":
    run()
