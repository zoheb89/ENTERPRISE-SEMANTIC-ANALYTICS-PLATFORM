import runpy
from pathlib import Path

import streamlit as st

from theme import inject_base_css, render_sidebar_brand, render_sidebar_navigation

st.set_page_config(
    page_title="Enterprise Semantic Analytics Platform",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# IMPORTANT: INVENT deliberately uses one browser document. Do not reintroduce
# st.navigation()/st.Page()/st.switch_page(); those create deep URLs that a
# browser refresh can restore instead of returning to Home.
if "_invent_current_page" not in st.session_state:
    st.session_state["_invent_current_page"] = "Home"

PAGE_FILES = {
    "Home": "0_Home.py",
    "Data Onboarding": "1_Data_Onboarding.py",
    "AI Analysis": "2_AI_Analysis.py",
    "Semantic Intelligence": "3_Semantic_Intelligence.py",
    "Business Model": "4_Business_Model.py",
    "Analytics": "5_Analytics.py",
    "Ask AI": "6_Ask_AI.py",
    "Security Center": "7_Security_Center.py",
    "Genie Agent": "8_Genie.py",
}

# QA Validation is an optional page in some builds; only expose it when the
# module actually exists so an incomplete deployment cannot crash navigation.
qa_file = Path(__file__).parent / "pages" / "9_QA_Validation.py"
if qa_file.exists():
    PAGE_FILES["QA Validation"] = "9_QA_Validation.py"

inject_base_css()
render_sidebar_brand()
render_sidebar_navigation()

current = st.session_state.get("_invent_current_page", "Home")
if current not in PAGE_FILES:
    current = "Home"
    st.session_state["_invent_current_page"] = current

page_path = Path(__file__).parent / "pages" / PAGE_FILES[current]
runpy.run_path(str(page_path), run_name="__invent_page__")
