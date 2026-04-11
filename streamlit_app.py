"""
Shorts Trend Tracker — 메인 대시보드
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Streamlit Cloud 시크릿 → 환경변수 주입 (로컬은 .env 사용)
try:
    for key in ["SUPABASE_URL", "SUPABASE_ANON_KEY"]:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # 로컬: secrets.toml 없으면 .env 파일 사용

from ui.community_tab import render_community_tab
from ui.youtube_tab import render_youtube_tab

st.set_page_config(
    page_title="Shorts Trend Tracker",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Shorts Trend Tracker")
st.caption("유튜브 쇼츠 소재 발굴 대시보드 — 커뮤니티 화제글 + 유튜브 급상승")

tab1, tab2 = st.tabs(["🗨️ 커뮤니티 트렌드", "▶️ 유튜브 급상승"])

with tab1:
    render_community_tab()

with tab2:
    render_youtube_tab()
