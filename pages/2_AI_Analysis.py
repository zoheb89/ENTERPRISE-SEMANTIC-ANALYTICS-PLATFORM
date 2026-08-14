
import time

import streamlit as st

from theme import inject_base_css, render_sidebar_brand, page_header
from semantic_engine import (
    scan_metadata,
    detect_data_quality_issues,
    classify_pii,
    detect_relationships,
    canonicalize_relationships,
    classify_tables,
    generate_metrics,
    generate_glossary,
    SemanticModel,
)
import ai_engine
import security_fabric as security


inject_base_css()
render_sidebar_brand()

page_header(
    "AI Analysis",
    "Watch the platform build a governed semantic model, live",
)

if not st.session_state.get("uploaded_files"):
    st.warning("No data to analyze yet.")
    if st.button("← Go to Data Onboarding"):
        st.switch_page(
            "pages/1_Data_Onboarding.py"
        )
    st.stop()

domain_name = st.session_state.get(
    "domain_name",
    "Untitled Domain",
)

files = st.session_state.uploaded_files

STEPS = [
    "Ingesting files",
    "Profiling metadata",
    "Identifying entities",
    "Identifying primary/foreign key candidates",
    "Discovering relationships",
    "Validating relationship direction",
    "Identifying fact tables",
    "Identifying dimensions",
    "Identifying measures",
    "Detecting business metrics",
    "Detecting duplicates",
    "Detecting data quality issues",
    "Detecting missing/possible dimensions",
    "Checking many-to-many candidates",
    "Generating semantic model",
    "Generating metric definitions",
    "Generating business glossary",
    "Checking for PII / PHI",
    "Preparing analytics",
    "Enabling natural-language analytics",
]

with st.container(border=True):

    st.markdown("**AI Analysis Running…**")

    log = st.empty()
    progress = st.progress(0)

    messages = []

    for i, step in enumerate(STEPS):
        messages.append(f"✓ {step}…")
        log.markdown("  \n".join(messages))
        progress.progress(
            int(
                (i + 1)
                / len(STEPS)
                * 100
            )
        )
        time.sleep(0.12)

    profiles = scan_metadata(files)

    detect_data_quality_issues(
        profiles
    )

    pii_findings = classify_pii(
        profiles
    )

    deterministic_relationships = (
        detect_relationships(profiles)
    )

    ai_suggestions = []

    if security.is_configured():

        ai_suggestions = (
            ai_engine.suggest_fuzzy_relationships(
                profiles,
                deterministic_relationships,
            )
        )

    # -------------------------------------------------------------
    # CRITICAL:
    # Canonicalize BEFORE classification.
    #
    # This prevents:
    #   production_runs -> defects
    # and:
    #   defects -> production_runs
    #
    # from becoming two semantic relationships.
    # -------------------------------------------------------------

    all_relationships = canonicalize_relationships(
        deterministic_relationships
        + ai_suggestions
    )

    CONFIDENCE_THRESHOLD = 0.75

    high_confidence = [
        r
        for r in all_relationships
        if r.confidence
        >= CONFIDENCE_THRESHOLD
    ]

    facts, dimensions = classify_tables(
        profiles,
        high_confidence,
    )

    metrics = generate_metrics(
        profiles,
        facts,
        high_confidence,
    )

    glossary = generate_glossary(
        profiles
    )

    if security.is_configured():

        ai_glossary = (
            ai_engine.draft_glossary_entries(
                profiles,
                domain_name,
            )
        )

        if ai_glossary:

            ai_terms = {
                g.term
                for g in ai_glossary
            }

            glossary = [
                g
                for g in glossary
                if g.term not in ai_terms
            ] + ai_glossary

    warnings = []

    for r in all_relationships:

        if r.is_many_to_many:

            warnings.append(
                "Many-to-many candidate: "
                f"{r.from_table}.{r.from_column} "
                "<-> "
                f"{r.to_table}.{r.to_column}"
            )

    if not facts:

        warnings.append(
            "No fact table confidently identified — "
            "upload a table with business measures/events."
        )

    referenced = {
        r.to_table
        for r in high_confidence
    }

    fk_sources = {
        r.from_table
        for r in high_confidence
    }

    for d in dimensions:

        if (
            d not in referenced
            and d not in fk_sources
        ):

            warnings.append(
                f"'{d}' has no detected relationship "
                "to any other table — possible missing dimension link"
            )

    model = SemanticModel(
        domain_name=domain_name,
        tables=profiles,
        relationships=all_relationships,
        facts=facts,
        dimensions=dimensions,
        metrics=metrics,
        glossary=glossary,
        warnings=warnings,
        pii_findings=pii_findings,
    )

    st.session_state.model = model

    st.session_state.llm_suggestion_count = sum(
        1
        for r in all_relationships
        if r.is_ai_suggested
    )

    log.markdown(
        "  \n".join(messages)
        + "\n\n**Analysis complete.**"
    )

st.success(
    f"Semantic model ready for **{domain_name}** — "
    f"{len(model.tables)} tables, "
    f"{len(model.relationships)} relationships, "
    f"{len(model.facts)} fact table(s), "
    f"{len(model.dimensions)} dimension table(s), "
    f"{len(model.metrics)} metrics."
)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button(
        "View Semantic Intelligence →",
        use_container_width=True,
    ):
        st.switch_page(
            "pages/3_Semantic_Intelligence.py"
        )

with col2:
    if st.button(
        "View Business Model →",
        use_container_width=True,
    ):
        st.switch_page(
            "pages/4_Business_Model.py"
        )

with col3:
    if st.button(
        "← Upload Different Data",
        use_container_width=True,
    ):
        st.switch_page(
            "pages/1_Data_Onboarding.py"
        )
