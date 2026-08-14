"""INVENT shared visual system and stable single-document navigation."""

from pathlib import Path
import streamlit as st

NAVY = "#10233D"
NAVY_DEEP = "#0B1A2D"
TEAL = "#1E8192"
TEAL_HOVER = "#176B79"
TEAL_LIGHT = "#E8F3F5"
AMBER = "#C97A3D"
CANVAS = "#F5F7F9"
PANEL = "#FFFFFF"
SLATE = "#243447"
SLATE_SOFT = "#667587"
LINE = "#DCE3E8"
RED = "#B5473F"
RED_LIGHT = "#FCEDEC"
GREEN = "#287A50"
GREEN_LIGHT = "#EAF5EE"

NAV_GROUPS = [
    ("CREATE", [
        ("Data Onboarding", "↳"),
        ("AI Analysis", "✦"),
        ("Semantic Intelligence", "◈"),
        ("Business Model", "◇"),
        ("QA Validation", "✓"),
    ]),
    ("ANALYZE", [
        ("Analytics", "▥"),
        ("Ask AI", "▤"),
        ("Genie Agent", "✧"),
    ]),
    ("GOVERN", [
        ("Security Center", "◇"),
    ]),
]


def inject_base_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');

        #MainMenu, footer {{ visibility:hidden; }}
        html, body, [class*="css"] {{ font-family:'Inter', sans-serif; }}
        .stApp {{ background:{CANVAS}; color:{SLATE}; }}
        .block-container {{ max-width:1240px; padding:2rem 2.2rem 3.5rem; }}

        /* Keep the Streamlit host chrome quiet and consistent with INVENT. */
        [data-testid="stHeader"] {{ background:#FFFFFF !important; border-bottom:1px solid {LINE}; }}
        [data-testid="stHeader"] * {{ color:{SLATE_SOFT} !important; }}
        [data-testid="stHeader"] svg {{ fill:{SLATE_SOFT} !important; }}

        /* INVENT sidebar */
        [data-testid="stSidebar"] {{
            background:{NAVY_DEEP} !important;
            border-right:1px solid rgba(255,255,255,.07);
        }}
        [data-testid="stSidebar"] > div:first-child {{ padding:0.9rem 0.85rem 1.2rem; }}
        [data-testid="stSidebarContent"] {{ padding-bottom:1rem; }}
        [data-testid="stSidebar"] [data-testid="stButton"] {{ width:100%; }}
        [data-testid="stSidebar"] [data-testid="stButton"] button {{
            width:100% !important;
            min-height:38px !important;
            border-radius:8px !important;
            border:1px solid transparent !important;
            background:transparent !important;
            color:#C9D5E0 !important;
            box-shadow:none !important;
            justify-content:flex-start !important;
            text-align:left !important;
            padding:0.45rem 0.72rem !important;
            font-size:13px !important;
            font-weight:500 !important;
            transition:background .12s ease, color .12s ease;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover {{
            background:rgba(255,255,255,.08) !important;
            color:#FFFFFF !important;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {{
            background:{TEAL} !important;
            border-color:{TEAL} !important;
            color:#FFFFFF !important;
            font-weight:700 !important;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover {{
            background:{TEAL_HOVER} !important;
            border-color:{TEAL_HOVER} !important;
        }}
        .invent-brand {{
            display:flex; align-items:center; gap:10px; padding:7px 5px 16px;
            margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,.10);
        }}
        .invent-brand-mark {{
            width:34px; height:34px; border-radius:9px; background:{TEAL};
            display:flex; align-items:center; justify-content:center;
            color:#FFFFFF; font-weight:800; font-size:16px;
            box-shadow:0 5px 16px rgba(0,0,0,.18);
        }}
        .invent-brand-name {{ color:#FFFFFF; font-weight:700; font-size:15px; line-height:1.05; }}
        .invent-brand-sub {{ color:#93A7B9; font-size:10px; margin-top:3px; letter-spacing:.2px; }}
        .invent-nav-heading {{
            color:#7F95A8; font-size:9px; font-weight:800; letter-spacing:1.7px;
            margin:19px 6px 6px;
        }}
        .invent-home-spacer {{ height:3px; }}

        /* Page surfaces */
        .platform-topbar {{
            background:{PANEL}; border:1px solid {LINE}; border-radius:12px;
            padding:18px 24px; margin-bottom:20px;
            box-shadow:0 1px 2px rgba(16,35,61,.03);
        }}
        .platform-topbar h1 {{
            font-family:'Source Serif 4', serif; font-size:25px; font-weight:700;
            color:{NAVY}; margin:0;
        }}
        .platform-topbar-sub {{ font-size:13px; color:{SLATE_SOFT}; margin-top:4px; }}
        .platform-card-title {{ font-family:'Source Serif 4',serif; font-size:17px; font-weight:700; color:{NAVY}; margin-bottom:2px; }}
        .platform-card-sub {{ font-size:12px; color:{SLATE_SOFT}; margin-bottom:10px; }}
        [data-testid="stMetric"] {{ background:{PANEL}; border:1px solid {LINE}; border-radius:11px; padding:16px 18px; }}
        [data-testid="stMetricLabel"] {{ color:{SLATE_SOFT} !important; font-size:11px !important; font-weight:700; text-transform:uppercase; letter-spacing:.4px; }}
        [data-testid="stMetricValue"] {{ font-family:'Source Serif 4',serif !important; color:{NAVY} !important; font-size:25px !important; font-weight:700 !important; }}
        .platform-tag {{ display:inline-block; padding:4px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
        .platform-tag.fact {{ background:{TEAL_LIGHT}; color:{TEAL}; }}
        .platform-tag.dim {{ background:#FFF1E5; color:#A45F1D; }}
        .platform-tag.pii {{ background:{RED_LIGHT}; color:{RED}; }}
        .platform-tag.ai {{ background:#FFF1E5; color:#A45F1D; }}
        .platform-tag.ok {{ background:{GREEN_LIGHT}; color:{GREEN}; }}
        .platform-banner {{ background:#FFF6E9; border:1px solid #EFD6AA; border-radius:9px; padding:11px 14px; font-size:12.5px; color:#6B4E1E; margin-bottom:14px; }}
        .platform-banner.info {{ background:#EDF7FB; border-color:#C9E3EE; color:#2C5A7A; }}
        .platform-banner.warn {{ background:{RED_LIGHT}; border-color:#F0C9C6; color:{RED}; }}
        .platform-banner.ok {{ background:{GREEN_LIGHT}; border-color:#C9E3D5; color:#1F5A3D; }}

        /* Main buttons */
        .stButton > button {{ border-radius:9px !important; min-height:40px; font-weight:600; }}
        .stButton > button[kind="primary"] {{ background:{TEAL} !important; border-color:{TEAL} !important; color:#FFFFFF !important; }}
        .stButton > button[kind="primary"]:hover {{ background:{TEAL_HOVER} !important; border-color:{TEAL_HOVER} !important; }}
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{ border-radius:8px !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def navigate_to(page_name: str):
    valid = {"Home"} | {name for _, pages in NAV_GROUPS for name, _ in pages}
    if page_name not in valid:
        page_name = "Home"
    st.session_state["_invent_current_page"] = page_name
    # A separate internal-navigation marker allows the router to distinguish
    # a genuine navigation action from a fresh session.
    st.session_state["_invent_internal_navigation"] = True
    st.rerun()


def render_sidebar_brand():
    if st.session_state.get("_invent_sidebar_brand_rendered"):
        return
    st.session_state["_invent_sidebar_brand_rendered"] = True
    with st.sidebar:
        st.markdown(
            """
            <div class="invent-brand">
              <div class="invent-brand-mark">IN</div>
              <div>
                <div class="invent-brand-name">INVENT</div>
                <div class="invent-brand-sub">Enterprise Semantic Analytics</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar_navigation():
    """Render the only INVENT navigation system; never use st.navigation/radio."""
    current = st.session_state.get("_invent_current_page", "Home")
    with st.sidebar:
        st.markdown('<div class="invent-home-spacer"></div>', unsafe_allow_html=True)
        if st.button("⌂  Home", key="nav_home", use_container_width=True,
                     type="primary" if current == "Home" else "secondary"):
            navigate_to("Home")

        for heading, page_names in NAV_GROUPS:
            st.markdown(f'<div class="invent-nav-heading">{heading}</div>', unsafe_allow_html=True)
            for page_name, icon in page_names:
                label = f"{icon}  {page_name}"
                if st.button(label, key=f"nav_{page_name.lower().replace(' ', '_')}",
                             use_container_width=True,
                             type="primary" if current == page_name else "secondary"):
                    navigate_to(page_name)


def page_header(title: str, subtitle: str):
    st.markdown(
        f'<div class="platform-topbar"><h1>{title}</h1><div class="platform-topbar-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = ""):
    sub_html = f'<div class="platform-card-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="platform-card-title">{title}</div>{sub_html}', unsafe_allow_html=True)
