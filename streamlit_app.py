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
    pass

from ui.community_tab import render_community_tab
from ui.channels_tab import render_channels_tab

st.set_page_config(
    page_title="Shorts Trend Tracker",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Shorts Trend Tracker")

page = st.sidebar.radio(
    "페이지",
    ["🗨️ 커뮤니티 트렌드", "📡 해외 채널 트래커"],
    label_visibility="collapsed",
)
st.sidebar.divider()

if page == "🗨️ 커뮤니티 트렌드":
    render_community_tab()
else:
    render_channels_tab()
