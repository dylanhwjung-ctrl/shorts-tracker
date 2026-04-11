"""
유튜브 급상승 탭 — youtube_videos 테이블 데이터 표시
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


def render_youtube_tab():
    col_filter, col_main = st.columns([1, 3])

    with col_filter:
        st.subheader("필터")
        countries = st.multiselect(
            "국가",
            options=["KR", "JP", "US"],
            default=["KR", "JP", "US"],
            format_func=lambda x: COUNTRY_LABELS.get(x, x),
        )
        sort_by = st.radio("정렬", ["조회수 높은순", "최신 수집순"])

    with col_main:
        if not countries:
            st.info("국가를 하나 이상 선택하세요.")
            return

        client = get_client()
        query = client.table("youtube_videos").select("*").in_("country", countries)

        if sort_by == "조회수 높은순":
            query = query.order("views", desc=True)
        else:
            query = query.order("collected_at", desc=True)

        result = query.limit(100).execute()
        videos = result.data

        if not videos:
            st.info("표시할 영상이 없습니다. 크롤러가 아직 실행되지 않았을 수 있습니다.")
            return

        st.caption(f"총 {len(videos)}개 영상 (최대 100개)")

        for video in videos:
            video_id = video.get("video_id", "")
            title = video.get("title", "")
            channel = video.get("channel_name") or ""
            country = COUNTRY_LABELS.get(video.get("country", ""), video.get("country", ""))
            views = video.get("views") or 0
            collected_date = video.get("collected_date") or ""

            yt_url = f"https://www.youtube.com/watch?v={video_id}"

            st.markdown(f"**[{title}]({yt_url})**")
            st.caption(f"{country} · {channel} · 조회수 {views:,} · {collected_date}")
            st.divider()
