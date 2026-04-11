"""
커뮤니티 트렌드 탭 — posts 테이블 데이터 표시
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

SOURCE_LABELS = {
    "reddit":  "Reddit",
    "ruliweb": "루리웹",
}

CATEGORY_LABELS = {
    "gaming":      "🎮 게임 스토리/덕질",
    "engineering": "⚙️ 공학/과학/밀리터리",
}


def render_community_tab():
    col_filter, col_main = st.columns([1, 3])

    with col_filter:
        st.subheader("필터")

        category = st.radio(
            "카테고리",
            options=["gaming", "engineering"],
            format_func=lambda x: CATEGORY_LABELS.get(x, x),
        )

        sources = st.multiselect(
            "소스",
            options=["reddit", "ruliweb"],
            default=["reddit", "ruliweb"],
            format_func=lambda x: SOURCE_LABELS.get(x, x),
        )

        sort_by = st.radio("정렬", ["점수 높은순", "최신순"])

    with col_main:
        if not sources:
            st.info("소스를 하나 이상 선택하세요.")
            return

        client = get_client()
        query = (
            client.table("posts")
            .select("*")
            .eq("category", category)
            .in_("source", sources)
        )

        if sort_by == "점수 높은순":
            query = query.order("score", desc=True)
        else:
            query = query.order("collected_at", desc=True)

        result = query.limit(100).execute()
        posts = result.data

        if not posts:
            st.info("표시할 게시글이 없습니다. 크롤러가 아직 실행되지 않았을 수 있습니다.")
            return

        st.caption(f"총 {len(posts)}개 게시글 (최대 100개)")

        for post in posts:
            title = post.get("title", "")
            url = post.get("url", "#")
            source = SOURCE_LABELS.get(post.get("source", ""), post.get("source", ""))
            board = post.get("board_name") or ""
            score = post.get("score") or 0
            comments = post.get("comment_count") or 0
            collected = (post.get("collected_at") or "")[:10]

            board_str = f" · {board}" if board else ""
            st.markdown(f"**[{title}]({url})**")
            st.caption(f"{source}{board_str} · 점수 {score:,} · 댓글 {comments}개 · {collected}")
            st.divider()
