"""
유튜브 급상승 탭 — youtube_videos 테이블 데이터 표시
channelfinder.kr 스타일: 국가별 탭 + 조회수 증가량 강조
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

COUNTRY_LABELS = {
    "KR": "🇰🇷 한국",
    "JP": "🇯🇵 일본",
    "US": "🇺🇸 미국",
}

CATEGORY_LABELS = {
    "gaming":      "🎮 게임",
    "engineering": "⚙️ 과학/기술",
}


def fmt_views(n: int) -> str:
    """조회수를 읽기 쉬운 형태로 변환"""
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    elif n >= 10_000:
        return f"{n / 10_000:.0f}만"
    else:
        return f"{n:,}"


def render_country_videos(videos: list[dict]):
    if not videos:
        st.info("데이터 없음")
        return
    for video in videos:
        video_id = video.get("video_id", "")
        title = video.get("title", "")
        channel = video.get("channel_name") or ""
        views = video.get("views") or 0
        view_increase = video.get("view_increase") or 0
        collected_date = video.get("collected_date") or ""

        yt_url = f"https://www.youtube.com/watch?v={video_id}"

        st.markdown(f"**[{title}]({yt_url})**")
        increase_str = f" · 📈 +{fmt_views(view_increase)}" if view_increase > 0 else ""
        st.caption(f"{channel} · 👁 {fmt_views(views)}{increase_str} · {collected_date}")
        st.divider()


def render_youtube_tab():
    col_filter, col_main = st.columns([1, 3])

    with col_filter:
        st.subheader("필터")

        category = st.radio(
            "카테고리",
            options=["gaming", "engineering"],
            format_func=lambda x: CATEGORY_LABELS.get(x, x),
        )

        sort_by = st.radio("정렬", ["조회수 높은순", "최신 수집순"])

    with col_main:
        client = get_client()

        tab_kr, tab_jp, tab_us = st.tabs(["🇰🇷 한국", "🇯🇵 일본", "🇺🇸 미국"])

        for tab, country in zip([tab_kr, tab_jp, tab_us], ["KR", "JP", "US"]):
            with tab:
                query = (
                    client.table("youtube_videos")
                    .select("*")
                    .eq("category", category)
                    .eq("country", country)
                )
                if sort_by == "조회수 높은순":
                    query = query.order("views", desc=True)
                else:
                    query = query.order("collected_at", desc=True)

                result = query.limit(50).execute()
                render_country_videos(result.data)
