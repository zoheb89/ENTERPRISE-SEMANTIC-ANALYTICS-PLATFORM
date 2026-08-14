
import streamlit as st
import pandas as pd

from theme import (
    inject_base_css,
    render_sidebar_brand,
    page_header,
    section_title,
)
from qa_engine import run_qa

inject_base_css()
render_sidebar_brand()

page_header(
    "QA & Validation",
    "Automated quality gate for the metadata-driven semantic model",
)

model = st.session_state.get("model")

if not model:
    st.warning("No semantic model is available for QA.")
    if st.button("← Go to Data Onboarding"):
        st.switch_page("pages/1_Data_Onboarding.py")
    st.stop()

# Re-run on demand so the page is deterministic even after a Streamlit
# rerun or a model object was modified during review.
result = run_qa(model)
st.session_state.qa_result = result

score = result["score"]
status = result["status"]

if status == "PASS":
    st.success(f"QA PASS — Semantic Quality Score {score}/100")
elif status == "WARN":
    st.warning(
        f"QA PASS WITH WARNINGS — Semantic Quality Score {score}/100"
    )
else:
    st.error(
        f"QA BLOCKED — Semantic Quality Score {score}/100"
    )

c1, c2, c3, c4 = st.columns(4)
c1.metric("Score", f"{score}/100")
c2.metric("Passed", result["passed"])
c3.metric("Warnings", result["warnings"])
c4.metric("Blocking Failures", result["blocking_failures"])

section_title(
    "Quality Gate",
    "Blocking semantic errors prevent publication; warnings remain visible for review.",
)

rows = []
for check in result["checks"]:
    rows.append(
        {
            "Category": check.category,
            "Check": check.name,
            "Status": check.status,
            "Blocking": "Yes" if check.blocking else "No",
            "Result": check.message,
        }
    )

df = pd.DataFrame(rows)

for category in df["Category"].unique():
    st.markdown(f"### {category}")
    category_rows = df[df["Category"] == category]

    for _, row in category_rows.iterrows():
        icon = {
            "PASS": "✅",
            "WARN": "⚠️",
            "FAIL": "❌",
        }.get(row["Status"], "•")

        with st.container(border=True):
            st.markdown(
                f"**{icon} {row['Check']}**"
                + (
                    " · **BLOCKING**"
                    if row["Blocking"] == "Yes"
                    else ""
                )
            )
            st.caption(row["Result"])

st.divider()

with st.container(border=True):
    section_title(
        "Publish Readiness",
        "The same QA result controls the Business Model publish gate.",
    )

    if result["publish_allowed"]:
        st.success(
            "This semantic model is eligible for publication."
        )
        if result["warnings"]:
            st.caption(
                "Warnings do not block publication, but they should be "
                "reviewed before broader enterprise access."
            )
    else:
        st.error(
            "Publication is blocked until the blocking QA failures are fixed."
        )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "View Business Model →",
            use_container_width=True,
            type="primary" if result["publish_allowed"] else "secondary",
        ):
            st.switch_page("pages/4_Business_Model.py")

    with c2:
        if st.button(
            "View Semantic Intelligence →",
            use_container_width=True,
        ):
            st.switch_page("pages/3_Semantic_Intelligence.py")
