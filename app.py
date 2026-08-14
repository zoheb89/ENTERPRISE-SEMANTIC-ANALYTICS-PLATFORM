import streamlit as st

st.set_page_config(
    page_title="Enterprise Semantic Analytics Platform",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

home = st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True)
onboarding = st.Page("pages/1_Data_Onboarding.py", title="Data Onboarding", icon=":material/upload_file:")
analysis = st.Page("pages/2_AI_Analysis.py", title="AI Analysis", icon=":material/psychology:")
intelligence = st.Page("pages/3_Semantic_Intelligence.py", title="Semantic Intelligence", icon=":material/hub:")
business_model = st.Page("pages/4_Business_Model.py", title="Business Model", icon=":material/schema:")
analytics = st.Page("pages/5_Analytics.py", title="Analytics", icon=":material/bar_chart:")
ask_ai = st.Page("pages/6_Ask_AI.py", title="Ask AI", icon=":material/chat:")
security = st.Page("pages/7_Security_Center.py", title="Security Center", icon=":material/shield:")
genie = st.Page("pages/8_Genie.py", title="Genie Agent", icon=":material/smart_toy:")
qa_validation = st.Page("pages/9_QA_Validation.py", title="QA & Validation", icon=":material/verified:")

pg = st.navigation(
    {
        "": [home],
        "Create — Data to Semantic Model": [onboarding, analysis, intelligence, qa_validation, business_model],
        "Analyze — Semantic Model to Insight": [analytics, ask_ai, genie],
        "Govern": [security],
    }
)

# ---------------------------------------------------------------------------
# INVENT STARTUP ROUTING
# ---------------------------------------------------------------------------
# Streamlit can restore the last deep-linked pathname (for example
# /Business_Model) after a browser refresh or after a server/app restart.
# `default=True` alone does not override an existing pathname.
#
# Use a process/app-instance token from cache_resource:
#   * same app instance + normal navigation -> stay on the selected page
#   * new browser session -> go to Home
#   * app/server reboot -> token changes -> go to Home
#
# This avoids the previous session-only flag, which could survive a reconnect
# and therefore fail to return users to the INVENT Home page after reboot.
@st.cache_resource
def _invent_app_instance_id() -> str:
    import uuid
    return str(uuid.uuid4())

_app_instance_id = _invent_app_instance_id()

_previous_instance = st.session_state.get("_invent_app_instance_id")
if _previous_instance != _app_instance_id:
    st.session_state["_invent_app_instance_id"] = _app_instance_id
    st.switch_page("pages/0_Home.py")

pg.run()
