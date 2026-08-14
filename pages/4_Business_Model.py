import datetime

import streamlit as st

from theme import inject_base_css, render_sidebar_brand, page_header, section_title
import security_fabric as security
import publish_engine
from registry import RegistryEntry, ensure_registry_exists, register_domain

inject_base_css()
render_sidebar_brand()

page_header("Business Model", "The governed semantic model, visualized — review before publishing")

model = st.session_state.get("model")
if not model:
    st.warning("No semantic model yet.")
    if st.button("← Go to Data Onboarding"):
        st.switch_page("pages/1_Data_Onboarding.py")
    st.stop()

with st.container(border=True):
    section_title(
        "Semantic Graph",
        f"Domain: {model.domain_name}",
    )

    if not model.facts:
        st.info(
            "No fact table identified — the graph needs at least "
            "one business event/fact with measures."
        )
    else:

        # Build an undirected graph for visualization/path discovery.
        adjacency = {
            table: []
            for table in model.tables
        }

        for rel in model.relationships:
            if rel.from_table == rel.to_table:
                continue

            adjacency.setdefault(
                rel.from_table,
                [],
            ).append(
                (
                    rel.to_table,
                    rel,
                )
            )

            adjacency.setdefault(
                rel.to_table,
                [],
            ).append(
                (
                    rel.from_table,
                    rel,
                )
            )

        # -------------------------------------------------------------
        # Direct relationships
        # -------------------------------------------------------------

        for fact in model.facts:

            direct = [
                r
                for r in model.relationships
                if r.from_table == fact
                and r.from_table != r.to_table
            ]

            st.markdown(
                f"### 🔵 {fact} — FACT"
            )

            if not direct:
                st.caption(
                    "No direct relationships detected."
                )
                continue

            direct_targets = set()

            for rel in direct:

                direct_targets.add(
                    rel.to_table
                )

                st.markdown(
                    f"""
                    **🟠 {rel.to_table} — "
                    f"DIRECT DIMENSION / RELATED ENTITY**  
                    `{rel.from_column} = {rel.to_column}`  
                    **{rel.confidence * 100:.0f}% confidence** · N:1
                    """
                )

                st.caption(
                    rel.reason
                )

            # ---------------------------------------------------------
            # Indirect paths.
            #
            # Example:
            # production_runs -> machines -> plants
            #
            # If production_runs also has a direct plant_id -> plants
            # relationship, show Plant once as DIRECT and do not render
            # it again as a fake linear child.
            # ---------------------------------------------------------

            indirect_paths = []

            def find_paths(
                current,
                target,
                visited,
                path,
                max_depth=3,
            ):
                if len(path) > max_depth:
                    return

                if current == target:
                    indirect_paths.append(
                        list(path)
                    )
                    return

                for nxt, edge in adjacency.get(
                    current,
                    [],
                ):

                    if nxt in visited:
                        continue

                    # Only use paths that don't simply return through
                    # an already direct target.
                    find_paths(
                        nxt,
                        target,
                        visited | {nxt},
                        path + [edge],
                        max_depth=max_depth,
                    )

            all_tables = set(model.tables)

            for target in all_tables:

                if target == fact:
                    continue

                if target in direct_targets:
                    # It is already represented directly.
                    continue

                indirect_paths.clear()

                find_paths(
                    fact,
                    target,
                    {fact},
                    [],
                    max_depth=3,
                )

                if not indirect_paths:
                    continue

                # Use the shortest path.
                shortest = min(
                    indirect_paths,
                    key=len,
                )

                if len(shortest) < 2:
                    continue

                path_tables = [fact]

                current = fact

                for edge in shortest:
                    if edge.from_table == current:
                        nxt = edge.to_table
                    else:
                        nxt = edge.from_table

                    path_tables.append(nxt)
                    current = nxt

                st.markdown(
                    f"🟣 **{target} — INDIRECT DIMENSION / RELATED ENTITY**"
                )

                st.caption(
                    " → ".join(
                        path_tables
                    )
                    + "  "
                    + " · ".join(
                        f"{e.from_column}={e.to_column}"
                        for e in shortest
                    )
                )

            st.divider()

    # -------------------------------------------------------------
    # Relationship summary
    # -------------------------------------------------------------

    direct_count = sum(
        1
        for r in model.relationships
        if (
            r.from_table in model.facts
            and r.to_table not in model.facts
        )
    )

    fact_to_fact_count = sum(
        1
        for r in model.relationships
        if (
            r.from_table in model.facts
            and r.to_table in model.facts
        )
    )

    st.markdown(
        f"""
        **Facts:** {len(model.facts)}  
        **Dimensions:** {len(model.dimensions)}  
        **Relationships:** {len(model.relationships)}  
        **Direct fact relationships:** {direct_count}  
        **Fact-to-fact relationships:** {fact_to_fact_count}  
        **Many-to-many:** {
            sum(
                1
                for r in model.relationships
                if r.is_many_to_many
            )
        }
        """
    )

st.divider()

with st.container(border=True):
    section_title("Publish", "Creates real Delta tables and a governed Metric View — with automatic security actions, no manual Databricks step")

    if not security.is_configured():
        st.markdown(
            '<div class="platform-banner warn">Databricks is not configured for this deployment — publishing is shown disabled '
            "rather than faked. See README.md for setup.</div>",
            unsafe_allow_html=True,
        )
        st.button("Publish", disabled=True)
    elif not model.facts:
        st.warning("No fact table identified — nothing to publish yet.")
    else:
        fact_choice = st.selectbox("Fact table to publish", model.facts)

        if model.pii_findings:
            st.markdown(
                '<div class="platform-banner warn">This model contains PII/PHI-flagged columns. '
                "Publishing proceeds, but masking and access review are recommended in the Security Center "
                "before granting broader access — this platform does not auto-apply masking without review.</div>",
                unsafe_allow_html=True,
            )

        if st.button("Publish This Domain", type="primary"):
            with st.spinner("Publishing — creating tables, Metric View, and issuing security grants automatically…"):
                try:
                    # Under PAT auth the publishing identity already owns
                    # what it creates. reader_principal is only set if a
                    # separate, more restricted identity is deliberately
                    # configured for read access -- optional, not required.
                    reader_principal = st.secrets.get("READER_PRINCIPAL_ID")
                    genie_space_id = st.secrets.get("GENIE_SPACE_ID")

                    result = publish_engine.publish_domain(model, fact_choice, genie_space_id, reader_principal)

                    ensure_registry_exists()
                    register_domain(RegistryEntry(
                        domain_name=model.domain_name, catalog=result["catalog"], schema=result["schema"],
                        metric_view=result["metric_view"], fact_table=fact_choice,
                        measures=result["measures"],
                        dimensions=result["dimensions"][:8],
                        default_kpi=result["measures"][0] if result["measures"] else "",
                        row_count=model.tables[fact_choice].row_count,
                        published_at=datetime.datetime.utcnow().isoformat(),
                        genie_space_id=result.get("genie_space_id"),
                    ))

                    st.session_state.last_published_domain = model.domain_name
                    st.session_state.security_actions = result["security_actions"]

                    st.success(f"**{model.domain_name}** published successfully — now live in Analytics, no redeploy needed.")
                    st.markdown(f"**Catalog:** `{result['catalog']}`  \n**Schema:** `{result['schema']}`  \n**Metric View:** `{result['metric_view']}`")

                    st.markdown("**Publication status:**")

                    genie_actions = [
                        a for a in result["security_actions"]
                        if a.action == "Genie Agent"
                    ]
                    other_actions = [
                        a for a in result["security_actions"]
                        if a.action != "Genie Agent"
                    ]

                    st.markdown(
                        "✅ Delta tables published  \n"
                        "✅ Governed Metric View(s) published"
                    )

                    if genie_actions:
                        successful_genie = [
                            a for a in genie_actions
                            if a.status == "success"
                        ]
                        failed_genie = [
                            a for a in genie_actions
                            if a.status == "failed"
                        ]

                        if successful_genie:
                            st.markdown(
                                "🧞 **Genie Agent connected**"
                            )
                            if result.get("genie_space_id"):
                                st.caption(
                                    f"Domain Genie Agent: "
                                    f"`{result['genie_space_id']}`"
                                )

                        if failed_genie:
                            st.warning(
                                "Genie Agent could not be configured. "
                                "The semantic publish succeeded; review "
                                "the Genie permissions/configuration."
                            )
                            for action in failed_genie:
                                st.caption(action.detail)

                        if not successful_genie and not failed_genie:
                            st.info(
                                "Genie Agent was not configured for this domain."
                            )

                    if other_actions:
                        for action in other_actions:
                            if action.status == "success":
                                st.markdown(
                                    f"✅ **{action.action}** — {action.detail}"
                                )
                            elif action.status == "failed":
                                st.warning(
                                    f"⚠️ **{action.action}** — {action.detail}"
                                )

                except Exception as e:
                    st.error(f"Publish failed: {e}")

st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Semantic Intelligence", use_container_width=True):
        st.switch_page("pages/3_Semantic_Intelligence.py")
with col2:
    if st.button("Go to Analytics →", use_container_width=True, type="primary"):
        st.switch_page("pages/5_Analytics.py")
