from pathlib import Path
import runpy
import streamlit as st

from theme import inject_base_css, render_sidebar_brand, render_sidebar_navigation

st.set_page_config(
    page_title="INVENT — Enterprise Semantic Analytics",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# One Streamlit document only. No reserved pages/ directory, no native
# multipage navigation, and no deep page URLs.
if "_invent_current_page" not in st.session_state:
    st.session_state["_invent_current_page"] = "Home"

VIEW_FILES = {
    "Home": "0_Home.py",
    "Data Onboarding": "1_Data_Onboarding.py",
    "AI Analysis": "2_AI_Analysis.py",
    "Semantic Intelligence": "3_Semantic_Intelligence.py",
    "Business Model": "4_Business_Model.py",
    "QA Validation": "9_QA_Validation.py",
    "Analytics": "5_Analytics.py",
    "Ask AI": "6_Ask_AI.py",
    "Genie Agent": "8_Genie.py",
    "Security Center": "7_Security_Center.py",
}

inject_base_css()
render_sidebar_brand()
render_sidebar_navigation()

current = st.session_state.get("_invent_current_page", "Home")
if current not in VIEW_FILES:
    current = "Home"
    st.session_state["_invent_current_page"] = "Home"

view_path = Path(__file__).parent / "views" / VIEW_FILES[current]
if not view_path.is_file():
    st.error(f"INVENT view is missing: {view_path.name}")
    st.stop()

runpy.run_path(str(view_path), run_name="__invent_view__")
