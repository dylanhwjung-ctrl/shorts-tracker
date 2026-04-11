"""
해외 채널 트래커 탭 — watched_channels + channel_daily_stats + channel_recent_shorts
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

SUBCATEGORY_OPTIONS = {
    "engineering": ["전체", "산업/중장비", "공학/기계", "밀리터리", "소방/안전", "과학/자연"],
    "gaming":      ["전체", "게임 로어/세계관", "게임 비하인드", "게임 이스터에그", "게임 역사"],
}

CATEGORY_LABELS = {
    "engineering": "⚙️ 공학/과학",
    "gaming":      "🎮 게임",
}

COUNTRY_FLAGS = {
    "US": "🇺🇸",
    "KR": "🇰🇷",
    "JP": "🇯🇵",
}

REVENUE_RATE = 0.2  # 조회수당 예상 수익 (원)


def fmt_num(n) -> str:
    n = int(n or 0)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    elif n >= 10_000:
        return f"{n / 10_000:.0f}만"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}천"
    return f"{n:,}"


def fmt_increase(n) -> str:
    n = int(n or 0)
    if n == 0:
        return ""
    sign = "+" if n > 0 else ""
    return f"{sign}{fmt_num(n)}"


def fmt_revenue(views: int) -> str:
    won = int(views * REVENUE_RATE)
    if won >= 10_000:
        return f"약 {won // 10_000}만원"
    return f"약 {won:,}원"


def render_channels_tab():
    # ── 사이드바 필터 ────────────────────────────────────────────────
    with st.sidebar:
        category = st.radio(
            "카테고리",
            ["engineering", "gaming"],
            format_func=lambda x: CATEGORY_LABELS[x],
        )

        subcategory = st.radio("서브카테고리", SUBCATEGORY_OPTIONS[category])

        country_options = ["전체", "🇺🇸 미국", "🇯🇵 일본", "🇰🇷 한국"]
        country_filter = st.radio("국가", country_options)
        country_map = {"🇺🇸 미국": "US", "🇯🇵 일본": "JP", "🇰🇷 한국": "KR"}
        selected_country = country_map.get(country_filter)

        only_favorites = st.checkbox("⭐ 즐겨찾기만 보기")

        sort_by = st.radio(
            "정렬",
            ["일일 조회수 증가순", "구독자 많은순", "총 조회수 높은순"],
        )

        st.caption("※ 일일 증감: 전날 데이터와 비교\n(최초 수집일은 0 표시)")

    # ── 메인 콘텐츠 ─────────────────────────────────────────────────
    client = get_client()

    ch_query = (
        client.table("watched_channels")
        .select("channel_id,channel_name,handle,country,subcategory,thumbnail_url,is_favorite")
        .eq("category", category)
    )
    if subcategory != "전체":
        ch_query = ch_query.eq("subcategory", subcategory)
    if selected_country:
        ch_query = ch_query.eq("country", selected_country)
    if only_favorites:
        ch_query = ch_query.eq("is_favorite", True)

    channels = ch_query.execute().data

    if not channels:
        st.info("등록된 채널이 없습니다.\n\n채널 발굴 실행:\n```\npython crawlers/channel_crawler.py discover engineering\npython crawlers/channel_crawler.py discover gaming\n```")
        return

    channel_ids = [ch["channel_id"] for ch in channels]
    ch_map = {ch["channel_id"]: ch for ch in channels}

    # 최신 통계
    stats_rows = (
        client.table("channel_daily_stats")
        .select("*")
        .in_("channel_id", channel_ids)
        .order("collected_date", desc=True)
        .limit(len(channel_ids) * 2)
        .execute()
        .data
    )
    latest_stats: dict[str, dict] = {}
    for row in stats_rows:
        cid = row["channel_id"]
        if cid not in latest_stats:
            latest_stats[cid] = row

    # 최근 쇼츠
    shorts_rows = (
        client.table("channel_recent_shorts")
        .select("*")
        .in_("channel_id", channel_ids)
        .order("published_at", desc=True)
        .limit(len(channel_ids) * 10)
        .execute()
        .data
    )
    channel_shorts: dict[str, list] = {}
    for s in shorts_rows:
        cid = s["channel_id"]
        if cid not in channel_shorts:
            channel_shorts[cid] = []
        if len(channel_shorts[cid]) < 5:
            channel_shorts[cid].append(s)

    # 정렬
    def sort_key(cid):
        s = latest_stats.get(cid, {})
        if sort_by == "일일 조회수 증가순":
            return int(s.get("view_increase", 0))
        elif sort_by == "구독자 많은순":
            return int(s.get("subscriber_count", 0))
        else:
            return int(s.get("total_views", 0))

    sorted_ids = sorted(channel_ids, key=sort_key, reverse=True)

    st.caption(f"총 {len(sorted_ids)}개 채널")

    for cid in sorted_ids:
        ch = ch_map[cid]
        stats = latest_stats.get(cid, {})
        shorts = channel_shorts.get(cid, [])

        name       = ch.get("channel_name", "")
        handle     = ch.get("handle", "")
        country    = ch.get("country", "")
        sub_cat    = ch.get("subcategory", "")
        thumb      = ch.get("thumbnail_url", "")
        is_fav     = ch.get("is_favorite", False)

        subs      = int(stats.get("subscriber_count", 0))
        view_inc  = int(stats.get("view_increase", 0))
        sub_inc   = int(stats.get("subscriber_increase", 0))
        video_cnt = int(stats.get("video_count", 0))

        flag   = COUNTRY_FLAGS.get(country, "🌐")
        yt_url = f"https://www.youtube.com/@{handle.lstrip('@')}" if handle else f"https://www.youtube.com/channel/{cid}"

        with st.container(border=True):
            info_col, fav_col = st.columns([10, 1])

            with info_col:
                img_col, text_col = st.columns([1, 6])
                with img_col:
                    if thumb:
                        st.image(thumb, width=56)
                    else:
                        st.write("📺")
                with text_col:
                    st.markdown(f"**[{name}]({yt_url})** {flag}")
                    st.caption(f"{sub_cat} · 구독자 {fmt_num(subs)} · 영상 {video_cnt}개")

                    if view_inc > 0 or sub_inc > 0:
                        parts = []
                        if view_inc > 0:
                            rev = f" ({fmt_revenue(view_inc)})"
                            parts.append(f"조회수 {fmt_increase(view_inc)}{rev}")
                        if sub_inc > 0:
                            parts.append(f"구독자 {fmt_increase(sub_inc)}")
                        st.markdown(f"📈 **{' · '.join(parts)}** (어제 기준)")
                    else:
                        st.caption("📈 증감 데이터 수집 중 (다음 날 업데이트)")

            with fav_col:
                star = "⭐" if is_fav else "☆"
                if st.button(star, key=f"fav_{cid}", help="즐겨찾기"):
                    client.table("watched_channels").update(
                        {"is_favorite": not is_fav}
                    ).eq("channel_id", cid).execute()
                    st.rerun()

            # 최근 쇼츠 썸네일
            if shorts:
                st.caption("최근 쇼츠")
                thumb_cols = st.columns(len(shorts))
                for col, s in zip(thumb_cols, shorts):
                    with col:
                        vid_url = f"https://www.youtube.com/shorts/{s['video_id']}"
                        if s.get("thumbnail_url"):
                            st.markdown(f"[![]({s['thumbnail_url']})]({vid_url})")
                        else:
                            st.markdown(f"[▶]({vid_url})")
