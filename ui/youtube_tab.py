"""
유튜브 급상승 탭 — youtube_videos 테이블 데이터 표시
국가별 탭 + 숏폼/롱폼 필터 + 조회수 증가량 표시
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

CATEGORY_LABELS = {
    "gaming":      "🎮 게임",
    "engineering": "⚙️ 과학/기술",
}


def fmt_views(n: int) -> str:
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    elif n >= 10_000:
        return f"{n / 10_000:.0f}만"
    else:
        return f"{n:,}"


def fmt_duration(seconds: int) -> str:
    if seconds <= 0:
        return ""
    if seconds < 60:
        return f"{seconds}초"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}분 {s}초"
    h, m = divmod(m, 60)
    return f"{h}시간 {m}분"


def render_country_videos(videos: list[dict], format_filter: str):
    # 형식 필터 (Python 레벨)
    if format_filter == "숏폼 (≤60초)":
        videos = [v for v in videos if 0 < (v.get("duration_seconds") or 0) <= 60]
    elif format_filter == "롱폼 (>60초)":
        videos = [v for v in videos if (v.get("duration_seconds") or 0) > 60]

    if not videos:
        st.info("해당 조건의 영상이 없습니다.")
        return

    for video in videos:
        video_id = video.get("video_id", "")
        title = video.get("title", "")
        channel = video.get("channel_name") or ""
        views = video.get("views") or 0
        view_increase = video.get("view_increase") or 0
        collected_date = video.get("collected_date") or ""
        duration_sec = video.get("duration_seconds") or 0

        yt_url = f"https://www.youtube.com/watch?v={video_id}"

        # 숏폼 뱃지
        badge = " 🩳숏폼" if 0 < duration_sec <= 60 else ""
        duration_str = f" · ⏱ {fmt_duration(duration_sec)}" if duration_sec > 0 else ""
        increase_str = f" · 📈 +{fmt_views(view_increase)}" if view_increase > 0 else ""

        st.markdown(f"**[{title}]({yt_url})**{badge}")
        st.caption(f"{channel} · 👁 {fmt_views(views)}{increase_str}{duration_str} · {collected_date}")
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

        format_filter = st.radio(
            "형식",
            options=["전체", "숏폼 (≤60초)", "롱폼 (>60초)"],
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

                result = query.limit(100).execute()
                render_country_videos(result.data, format_filter)
