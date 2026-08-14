from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text()
THEME = (ROOT / "theme.py").read_text()

# Streamlit's reserved pages/ directory must not exist: INVENT owns one
# browser document and performs navigation through session state.
assert not (ROOT / "pages").exists(), "Reserved Streamlit pages/ directory must not exist"
assert (ROOT / "views").is_dir(), "INVENT views directory is missing"
assert "st.navigation(" not in APP
assert "st.Page(" not in APP
assert "st.switch_page(" not in APP
assert "runpy.run_path" in APP
assert '"_invent_current_page"' in APP
assert '"Home"' in APP
assert '"views"' in APP
assert "st.sidebar.radio(" not in THEME
assert "st.switch_page(" not in THEME

for view in (ROOT / "views").glob("*.py"):
    text = view.read_text()
    assert "st.switch_page(" not in text, view.name

for page_name in [
    "Home", "Data Onboarding", "AI Analysis", "Semantic Intelligence",
    "Business Model", "QA Validation", "Analytics", "Ask AI",
    "Genie Agent", "Security Center"
]:
    assert f'"{page_name}"' in APP

onboarding = (ROOT / "views" / "1_Data_Onboarding.py").read_text()
assert '"xml"' in onboarding

print("INVENT ROUTING QA: PASS")
