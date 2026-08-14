from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text()
THEME = (ROOT / "theme.py").read_text()

# INVENT must remain a single browser document. Native multipage navigation
# creates deep URLs that can be restored by the browser after F5/reboot.
assert "st.navigation(" not in APP.replace("st.navigation()/st.Page()/st.switch_page()", "")
assert "st.Page(" not in APP.replace("st.navigation()/st.Page()/st.switch_page()", "")
assert "st.switch_page(" not in APP.replace("st.navigation()/st.Page()/st.switch_page()", "")
assert "runpy.run_path" in APP
assert '"_invent_current_page"' in APP
assert '"Home"' in APP

# No page may bypass the internal router.
for page in (ROOT / "pages").glob("*.py"):
    text = page.read_text()
    assert "st.switch_page(" not in text, page.name

# Ask AI must use the internal router for its fallback navigation.
ask_ai = (ROOT / "pages" / "6_Ask_AI.py").read_text()
assert "navigate_to(" in ask_ai
assert "st.switch_page(" not in ask_ai

onboarding = (ROOT / "pages" / "1_Data_Onboarding.py").read_text()
assert '"xml"' in onboarding

# Router must expose the core INVENT pages.
for page_name in [
    "Home", "Data Onboarding", "AI Analysis", "Semantic Intelligence",
    "Business Model", "Analytics", "Ask AI", "Security Center", "Genie Agent"
]:
    assert f'"{page_name}"' in APP

print("INVENT ROUTING QA: PASS")
