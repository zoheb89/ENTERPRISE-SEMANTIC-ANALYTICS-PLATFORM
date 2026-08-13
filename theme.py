"""
Enterprise Semantic Analytics Platform — shared visual system.
"""

import streamlit as st
from pathlib import Path

NAVY = "#0F1F35"
NAVY_DEEP = "#0A1626"
TEAL = "#1B7A8C"
TEAL_LIGHT = "#E4EEF0"
AMBER = "#C97D3F"
AMBER_LIGHT = "#FBF0E4"
CANVAS = "#F7F6F3"
PANEL = "#FFFFFF"
SLATE = "#22303F"
SLATE_SOFT = "#5C6B7A"
LINE = "#E2E1DB"
RED = "#B0473F"
RED_LIGHT = "#FBEBE9"
GREEN = "#2E8B57"
GREEN_LIGHT = "#E9F4EE"


def inject_base_css():
    st.markdown(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');

          #MainMenu {{visibility: hidden;}}
          footer {{visibility: hidden;}}

          html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
          .stApp {{ background: {CANVAS}; }}
          .block-container {{ padding-top: 1.5rem; max-width: 1200px; }}

          [data-testid="stHeader"] {{ background: {NAVY_DEEP} !important; }}
          [data-testid="stHeader"] * {{ color: #C9D3DD !important; }}
          [data-testid="stHeader"] svg {{ fill: #C9D3DD !important; }}

          [data-testid="stSidebar"] {{ background: {NAVY_DEEP} !important; }}
          [data-testid="stSidebar"] * {{ color: #C9D3DD !important; }}
          [data-testid="stSidebarHeader"] {{
            padding: 18px 16px 10px 16px !important;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            margin-bottom: 6px;
          }}
          [data-testid="stSidebarHeader"] img {{ height: 40px !important; width: auto !important; }}
          [data-testid="stSidebar"] [aria-current="page"] {{ background: rgba(27,122,140,0.28) !important; }}
          [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{ border-radius: 7px !important; margin-bottom: 2px; }}

          .platform-topbar {{
            background: {PANEL}; border: 1px solid {LINE}; border-radius: 10px;
            padding: 16px 24px; margin-bottom: 20px;
          }}
          .platform-topbar h1 {{ font-family: 'Source Serif 4', serif; font-size: 22px; font-weight: 600; color: {NAVY}; margin: 0; }}
          .platform-topbar-sub {{ font-size: 12.5px; color: {SLATE_SOFT}; margin-top: 3px; }}

          [data-testid="stMetric"] {{
            background: {PANEL}; border: 1px solid {LINE}; border-radius: 10px; padding: 16px 18px;
          }}
          [data-testid="stMetricLabel"] {{
            color: {SLATE_SOFT} !important; font-size: 11px !important; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.4px;
          }}
          [data-testid="stMetricValue"] {{
            font-family: 'Source Serif 4', serif !important; color: {NAVY} !important;
            font-size: 25px !important; font-weight: 600 !important;
          }}

          .platform-card-title {{ font-family: 'Source Serif 4', serif; font-size: 16px; font-weight: 600; color: {NAVY}; margin-bottom: 2px; }}
          .platform-card-sub {{ font-size: 12px; color: {SLATE_SOFT}; margin-bottom: 10px; }}

          .platform-tag {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
          .platform-tag.fact {{ background: {TEAL_LIGHT}; color: {TEAL}; }}
          .platform-tag.dim {{ background: {AMBER_LIGHT}; color: #A2661E; }}
          .platform-tag.pii {{ background: {RED_LIGHT}; color: {RED}; }}
          .platform-tag.ai {{ background: {AMBER_LIGHT}; color: #A2661E; }}
          .platform-tag.ok {{ background: {GREEN_LIGHT}; color: {GREEN}; }}

          .platform-banner {{
            background: {AMBER_LIGHT}; border: 1px solid #EAD3A8; border-radius: 8px;
            padding: 10px 14px; font-size: 12.5px; color: #6B4E1E; margin-bottom: 14px;
          }}
          .platform-banner.info {{ background: #EAF4FB; border-color: #C7E2F4; color: #2C5A7A; }}
          .platform-banner.warn {{ background: {RED_LIGHT}; border-color: #F0C9C6; color: {RED}; }}
          .platform-banner.ok {{ background: {GREEN_LIGHT}; border-color: #C8E3D0; color: #1F5A3D; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand():
    logo_path = Path(__file__).resolve().parent / "assets" / "platform_logo.svg"

    if logo_path.is_file():
        try:
            st.logo(str(logo_path), size="large")
            return
        except Exception:
            pass

    st.sidebar.markdown(
        """
        <div style="
            padding: 10px 8px 14px 8px;
            margin-bottom: 8px;
        ">
            <div style="
                font-size: 20px;
                font-weight: 700;
            ">
                Enterprise Semantic
            </div>
            <div style="
                font-size: 12px;
                opacity: 0.65;
            ">
                Analytics Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="platform-topbar">
          <h1>{title}</h1>
          <div class="platform-topbar-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = ""):
    sub_html = f'<div class="platform-card-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="platform-card-title">{title}</div>{sub_html}', unsafe_allow_html=True)
