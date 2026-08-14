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

# INVENT startup behavior:
# A brand-new browser/session load always starts at Home, even if the browser
# restores a deep-link URL such as /Business_Model. Once the user has entered
# the application, normal Streamlit navigation is preserved.
#
# This is intentionally session-scoped: clicking between INVENT pages does not
# bounce the user back to Home, while a fresh/rebooted session gets the Home page.
if "_invent_session_booted" not in st.session_state:
    st.session_state["_invent_session_booted"] = True
    st.switch_page("pages/0_Home.py")

pg.run()
