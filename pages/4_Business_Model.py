import datetime

import streamlit as st

from theme import (
    inject_base_css,
    render_sidebar_brand,
    page_header,
    section_title,
)
import security_fabric as security
import publish_engine
from registry import (
    RegistryEntry,
    ensure_registry_exists,
    register_domain,
)


inject_base_css()
render_sidebar_brand()

page_header(
    "Business Model",
    "The governed semantic model, visualized — review before publishing",
)

model = st.session_state.get("model")

if not model:
    st.warning("No semantic model yet.")
    if st.button("← Go to Data Onboarding"):
        st.switch_page("pages/1_Data_Onboarding.py")
    st.stop()


# ============================================================
# GOVERNED GRAPH
# ============================================================

relationships = list(
    getattr(model, "relationships", []) or []
)

governed_relationships = [
    r for r in relationships
    if not getattr(r, "is_ai_suggested", False)
]

ai_relationships = [
    r for r in relationships
    if getattr(r, "is_ai_suggested", False)
]


# Direct dimensions are dimensions directly referenced by a fact.
direct_dimensions = set()

for rel in governed_relationships:
    if rel.from_table in model.facts:
        direct_dimensions.add(rel.to_table)


# Indirect dimensions are reachable through a direct dimension.
indirect_dimensions = set()

for rel in governed_relationships:
    if rel.from_table in direct_dimensions:
        if rel.to_table not in direct_dimensions:
            indirect_dimensions.add(rel.to_table)


# ============================================================
# SEMANTIC GRAPH
# ============================================================

with st.container(border=True):

    section_title(
        "Semantic Graph",
        f"Domain: {model.domain_name}",
    )

    # Native Streamlit rendering — no literal HTML span leakage.
    legend = st.columns(4)

    with legend[0]:
        st.markdown("🔵 **FACT**")

    with legend[1]:
        st.markdown("🟠 **DIRECT DIMENSION**")

    with legend[2]:
        st.markdown("🟣 **INDIRECT DIMENSION**")

    with legend[3]:
        st.markdown("⚪ **AI SUGGESTION — REVIEW**")

    st.divider()

    if not model.facts:

        st.info(
            "No fact table identified — the graph needs at least "
            "one fact table with a relationship to a dimension."
        )

    else:

        for fact in model.facts:

            st.markdown(
                f"### {fact}"
            )

            st.caption("FACT")

            fact_relationships = [
                r
                for r in governed_relationships
                if r.from_table == fact
            ]

            if not fact_relationships:

                st.caption(
                    "No direct dimension relationships detected."
                )

            for rel in fact_relationships:

                st.markdown("↓")

                st.markdown(
                    f"**{rel.to_table}**"
                )

                st.caption(
                    "DIRECT DIMENSION"
                )

                st.code(
                    f"{rel.from_column} = {rel.to_column}",
                    language="text",
                )

                st.caption(
                    f"N:1 · {rel.confidence * 100:.0f}% confidence"
                )

                # One level of indirect dimensions is enough for
                # the current governed graph visualization.
                indirect = [
                    r
                    for r in governed_relationships
                    if r.from_table == rel.to_table
                ]

                for child in indirect:

                    st.markdown("　↓")

                    st.markdown(
                        f"**{child.to_table}**"
                    )

                    st.caption(
                        "INDIRECT DIMENSION"
                    )

                    st.code(
                        f"{child.from_column} = "
                        f"{child.to_column}",
                        language="text",
                    )

                    st.caption(
                        f"N:1 · {child.confidence * 100:.0f}% confidence"
                    )


# ============================================================
# SUMMARY
# ============================================================

st.divider()

summary = st.columns(4)

summary[0].metric(
    "Direct dimensions",
    len(direct_dimensions),
)

summary[1].metric(
    "Indirect dimensions",
    len(indirect_dimensions),
)

summary[2].metric(
    "Relationships",
    len(governed_relationships),
)

summary[3].metric(
    "Many-to-many",
    sum(
        1
        for r in governed_relationships
        if getattr(r, "is_many_to_many", False)
    ),
)


# ============================================================
# AI SUGGESTIONS
# ============================================================

with st.container(border=True):

    section_title(
        "AI Relationship Suggestions",
        "Potential relationships detected by AI — review before publishing",
    )

    if ai_relationships:

        st.warning(
            f"{len(ai_relationships)} AI-suggested relationship(s) "
            "are intentionally excluded from the governed graph."
        )

        for rel in ai_relationships:

            with st.container(border=True):

                st.markdown(
                    f"**{rel.from_table}.{rel.from_column}** "
                    f"→ "
                    f"**{rel.to_table}.{rel.to_column}**"
                )

                st.caption(
                    f"Confidence: "
                    f"{rel.confidence * 100:.0f}%"
                )

                if getattr(rel, "reason", None):

                    st.caption(
                        f"AI reasoning: {rel.reason}"
                    )

    else:

        st.success(
            "No additional AI relationship suggestions require review."
        )


# ============================================================
# PUBLISH
# ============================================================

st.divider()

with st.container(border=True):

    section_title(
        "Publish",
        "Creates real Delta tables and a governed Metric View — "
        "with automatic security actions and no manual SQL step",
    )

    if not security.is_configured():

        st.warning(
            "Databricks is not configured for this deployment."
        )

        st.button(
            "Publish",
            disabled=True,
        )

    elif not model.facts:

        st.warning(
            "No fact table identified — nothing to publish."
        )

    else:

        fact_choice = st.selectbox(
            "Fact table to publish",
            model.facts,
        )

        if model.pii_findings:

            st.warning(
                "PII/PHI was detected. Review the Security Center "
                "before wider access."
            )

        if st.button(
            "Publish This Domain",
            type="primary",
        ):

            with st.spinner(
                "Publishing semantic model…"
            ):

                try:

                    reader_principal = st.secrets.get(
                        "READER_PRINCIPAL_ID"
                    )

                    # IMPORTANT:
                    # GENIE_SPACE_ID is optional.
                    # Do not require it for semantic publication.
                    genie_space_id = st.secrets.get(
                        "GENIE_SPACE_ID"
                    )

                    result = publish_engine.publish_domain(
                        model,
                        fact_choice,
                        genie_space_id,
                        reader_principal,
                    )

                    ensure_registry_exists()

                    registry_dimensions = result.get(
                        "dimensions",
                        [],
                    )

                    register_domain(
                        RegistryEntry(
                            domain_name=model.domain_name,
                            catalog=result["catalog"],
                            schema=result["schema"],
                            metric_view=result["metric_view"],
                            fact_table=fact_choice,
                            measures=result["measures"],
                            dimensions=registry_dimensions,
                            default_kpi=(
                                result["measures"][0]
                                if result["measures"]
                                else ""
                            ),
                            row_count=model.tables[
                                fact_choice
                            ].row_count,
                            published_at=(
                                datetime.datetime.utcnow()
                                .isoformat()
                            ),
                            genie_space_id=result.get(
                                "genie_space_id"
                            ),
                        )
                    )

                    st.session_state[
                        "last_published_domain"
                    ] = model.domain_name

                    st.session_state[
                        "security_actions"
                    ] = result[
                        "security_actions"
                    ]

                    st.success(
                        f"**{model.domain_name}** published successfully."
                    )

                    st.markdown(
                        f"**Catalog:** `{result['catalog']}`  \n"
                        f"**Schema:** `{result['schema']}`  \n"
                        f"**Metric View:** `{result['metric_view']}`"
                    )

                    st.markdown(
                        "**Security / publication actions:**"
                    )

                    for action in result[
                        "security_actions"
                    ]:

                        if action.status == "success":
                            icon = "✅"
                        elif action.status == "skipped":
                            icon = "ℹ️"
                        else:
                            icon = "⚠️"

                        st.markdown(
                            f"{icon} **{action.action}** — "
                            f"`{action.target}` — "
                            f"{action.detail}"
                        )

                except Exception as exc:

                    st.error(
                        f"Publish failed: {exc}"
                    )


# ============================================================
# NAVIGATION
# ============================================================

st.divider()

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "← Back to Semantic Intelligence",
        use_container_width=True,
    ):

        st.switch_page(
            "pages/3_Semantic_Intelligence.py"
        )

with col2:

    if st.button(
        "Go to Analytics →",
        use_container_width=True,
        type="primary",
    ):

        st.switch_page(
            "pages/5_Analytics.py"
        )
