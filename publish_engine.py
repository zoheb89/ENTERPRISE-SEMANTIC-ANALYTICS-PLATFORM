"""
Enterprise Semantic Analytics Platform — Publish Orchestration.

Ties semantic_engine.py (analysis) and security_fabric.py (grants +
Genie) together into one end-to-end publish operation: write Delta
tables, create a real Unity Catalog Metric View, grant the reader
principal access, and register the new asset with the shared Genie
space — all in one call, no manual Databricks step in between.

Schema isolation is enforced structurally: every domain gets its own
schema in the dedicated Invent catalog, name-validated before any write
happens, so two domains uploaded back-to-back can never collide.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st
from databricks import sql as dbsql

import security_fabric as security
from semantic_engine import SemanticModel, _looks_like_id_column, _looks_non_additive, _looks_like_rating_or_category_column


def _sanitize_identifier(name: str) -> str:
    n = re.sub(r'\.(csv|xlsx?)$', '', name, flags=re.IGNORECASE)
    n = re.sub(r'[^a-zA-Z0-9_]', '_', n).lower()
    n = re.sub(r'_+', '_', n).strip('_')
    return n or "table"


def _validate_domain_schema_name(domain_name: str) -> str:
    safe = _sanitize_identifier(domain_name)
    return f"domain_{safe}"


def get_sql_connection():
    """Uses PAT auth (see security_fabric._pat_config for why) — the
    catalog= parameter is required here too: without it the connector
    defaults to the workspace's own default catalog rather than the
    one configured, a real bug traced and fixed earlier in this
    project's history."""
    hostname = st.secrets["DATABRICKS_HOST"].replace("https://", "").replace("http://", "")
    cfg = security._pat_config()
    return dbsql.connect(
        server_hostname=hostname,
        http_path=f"/sql/1.0/warehouses/{st.secrets['DATABRICKS_WAREHOUSE_ID']}",
        credentials_provider=lambda: cfg.authenticate,
        catalog=st.secrets["DATABRICKS_CATALOG"],
    )


def _infer_sql_type(series: pd.Series) -> str:
    dtype = str(series.dtype)
    if "int" in dtype:
        return "BIGINT"
    if "float" in dtype:
        return "DOUBLE"
    if "bool" in dtype:
        return "BOOLEAN"
    if "datetime" in dtype:
        return "TIMESTAMP"
    return "STRING"


def _write_dataframe_as_table(cursor, df: pd.DataFrame, full_table_name: str, max_rows_inline: int = 2000):
    if len(df) > max_rows_inline:
        raise ValueError(
            f"{full_table_name}: {len(df)} rows exceeds the {max_rows_inline}-row inline publish limit "
            f"for this demo build. Production-scale uploads need a Volume + COPY INTO path instead."
        )
    cols_ddl = ", ".join(f"`{c}` {_infer_sql_type(df[c])}" for c in df.columns)
    cursor.execute(f"DROP TABLE IF EXISTS {full_table_name}")
    cursor.execute(f"CREATE TABLE {full_table_name} ({cols_ddl}) USING DELTA")
    if len(df) == 0:
        return
    col_names = ", ".join(f"`{c}`" for c in df.columns)
    values_rows = []
    for _, row in df.iterrows():
        vals = []
        for v in row:
            if pd.isna(v):
                vals.append("NULL")
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                vals.append("'" + str(v).replace("'", "''") + "'")
        values_rows.append(f"({', '.join(vals)})")
    cursor.execute(f"INSERT INTO {full_table_name} ({col_names}) VALUES {', '.join(values_rows)}")


def _model_to_metric_view_yaml(model: SemanticModel, fact_table: str, schema: str, catalog: str) -> tuple[str, list[str], list[str]]:
    """Returns (yaml_text, real_measure_names, real_dimension_names).
    Both name lists are the single source of truth for what actually
    exists in the published view — callers (the registry writer) must
    use THESE lists, not re-derive names independently, to avoid drift.
    See publish_domain().

    Dimension fields are aliased ({alias}_{column}, e.g.
    department_department_name) to avoid collisions when two joined
    dimensions share a column name. An earlier version of the registry
    writer (pages/4_Business_Model.py) stored the raw, un-aliased source
    column name instead of this real aliased name -- causing
    SELECT {dimension} in analytics_engine.py to reference a column that
    never existed in the Metric View, and Databricks correctly rejected
    the query at runtime. Fixed the same way the earlier measure-name
    drift bug was: return the real names from here, stop re-deriving
    them elsewhere."""
    fact_profile = model.tables[fact_table]
    fact_safe = _sanitize_identifier(fact_table)
    joins_yaml, fields_yaml, measures_yaml = [], [], []
    measure_names: list[str] = []
    dimension_names: list[str] = []

    related = [
        r for r in model.relationships
        if r.from_table == fact_table
        and r.to_table not in model.facts
    ]
    for rel in related:
        alias = _sanitize_identifier(rel.to_table)
        joins_yaml.append(
            f"  - name: {alias}\n    source: {catalog}.{schema}.{alias}\n"
            f"    on: source.{rel.from_column} = {alias}.{rel.to_column}\n    cardinality: many_to_one"
        )
        dim_profile = model.tables[rel.to_table]
        for c in dim_profile.columns:
            if c.name == rel.to_column or "int" in c.dtype or "float" in c.dtype:
                continue
            field_name = f"{alias}_{c.name}"
            fields_yaml.append(f"  - name: {field_name}\n    expr: {alias}.{c.name}")
            dimension_names.append(field_name)

    for c in fact_profile.columns:
        if any(r.from_column == c.name for r in related):
            continue
        is_id = _looks_like_id_column(c.name, c.dtype)
        is_rating = _looks_like_rating_or_category_column(c, fact_profile.row_count)
        is_non_additive = _looks_non_additive(c.name)
        if ("int" in c.dtype or "float" in c.dtype) and not is_id and not is_rating:
            if is_non_additive:
                # AVG(), not SUM() -- summing a rate/measurement column
                # (heart_rate, conversion_rate) is meaningless. Matches
                # generate_metrics()'s AVG() generation for the same
                # column type, so the registry's measure list and the
                # real published measure stay in sync (same discipline
                # as the earlier total_/count naming fix).
                measure_name = f"avg_{c.name}"
                measures_yaml.append(f"  - name: {measure_name}\n    expr: AVG(source.{c.name})")
            else:
                measure_name = f"total_{c.name}"
                measures_yaml.append(f"  - name: {measure_name}\n    expr: SUM(source.{c.name})")
            measure_names.append(measure_name)
        elif not is_id:
            fields_yaml.append(f"  - name: {c.name}\n    expr: source.{c.name}")

    # A COUNT(*) measure is always added, matching one generate_metrics()
    # always appends per fact table in semantic_engine.py. Both this
    # measure list and that BusinessMetric list feed the registry — this
    # function's return value is now what the registry actually uses.
    count_measure_name = f"{fact_safe}_count"
    measures_yaml.append(f"  - name: {count_measure_name}\n    expr: COUNT(*)")
    measure_names.append(count_measure_name)

    yaml_text = f"""version: 1.1
source: {catalog}.{schema}.{fact_safe}
comment: "Published by Enterprise Semantic Analytics Platform — domain: {model.domain_name}"

joins:
{chr(10).join(joins_yaml) if joins_yaml else "  []"}

fields:
{chr(10).join(fields_yaml) if fields_yaml else "  []"}

measures:
{chr(10).join(measures_yaml) if measures_yaml else "  []"}
"""
    return yaml_text, measure_names, dimension_names



def publish_domain(
    model: SemanticModel,
    fact_table: str,
    genie_space_id: str | None = None,
    reader_principal: str | None = None,
) -> dict:
    """
    Production publish pipeline for one metadata-driven domain.

    Creates:
      * one isolated schema
      * one Delta table per uploaded asset
      * one Metric View per detected fact table
      * one domain Genie Agent (existing mapped ID or automatic creation)
      * registry-ready metadata for the selected primary fact

    The selected fact remains the primary analytics entry point, while all
    detected facts are published so the domain semantic model is complete.
    """

    catalog = st.secrets["DATABRICKS_CATALOG"]
    schema = _validate_domain_schema_name(
        model.domain_name
    )

    if fact_table not in model.facts:
        raise ValueError(
            f"'{fact_table}' is not a governed fact table."
        )

    security_actions = []
    created_tables = []
    metric_views = {}

    with get_sql_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                f"CREATE SCHEMA IF NOT EXISTS "
                f"{catalog}.{schema}"
            )

            # ---------------------------------------------------------
            # Publish every uploaded table as a real Delta table.
            # ---------------------------------------------------------
            for table_name, profile in model.tables.items():

                safe_name = _sanitize_identifier(
                    table_name
                )

                full_name = (
                    f"{catalog}.{schema}.{safe_name}"
                )

                _write_dataframe_as_table(
                    cur,
                    profile.df,
                    full_name,
                )

                created_tables.append(
                    full_name
                )

            # ---------------------------------------------------------
            # Publish one governed Metric View per fact.
            # ---------------------------------------------------------
            for current_fact in model.facts:

                fact_safe = _sanitize_identifier(
                    current_fact
                )

                view_name = (
                    f"{catalog}.{schema}."
                    f"mv_{fact_safe}"
                )

                (
                    yaml_body,
                    measure_names,
                    dimension_names,
                ) = _model_to_metric_view_yaml(
                    model,
                    current_fact,
                    schema,
                    catalog,
                )

                cur.execute(
                    f"""
                    CREATE OR REPLACE VIEW
                    {view_name}
                    WITH METRICS
                    LANGUAGE YAML
                    AS $${yaml_body}$$
                    """
                )

                metric_views[current_fact] = {
                    "metric_view": view_name,
                    "measures": measure_names,
                    "dimensions": dimension_names,
                }

    # -------------------------------------------------------------
    # Optional reader permissions.
    # -------------------------------------------------------------
    if reader_principal:
        security_actions.append(
            security.grant_select_on_schema(
                f"{catalog}.{schema}",
                reader_principal,
            )
        )

    # -------------------------------------------------------------
    # Genie — domain-scoped and automatic.
    #
    # Preferred configuration:
    #   [GENIE_SPACES]
    #   Retail = "..."
    #
    # Legacy fallback:
    #   GENIE_SPACE_ID = "..."
    #
    # If neither is present and GENIE_AUTO_CREATE=true, INVENT creates
    # a Genie Agent for this domain.
    # -------------------------------------------------------------

    resolved_space_id = (
        str(genie_space_id).strip()
        if genie_space_id
        else security.genie_space_id_from_secrets(
            model.domain_name
        )
    )

    ordered_facts = [
        fact_table
    ] + [
        f
        for f in model.facts
        if f != fact_table
    ]

    first_genie_action = None

    for current_fact in ordered_facts:

        mv = metric_views[current_fact]

        sample_questions = [
            f"What are the key KPIs for {model.domain_name}?",
            (
                f"Show {mv['measures'][0]} by "
                f"the main business dimensions."
                if mv["measures"]
                else (
                    f"Show the main trends for "
                    f"{model.domain_name}."
                )
            ),
        ]

        resolved_space_id, action = (
            security.register_table_with_genie_space(
                resolved_space_id,
                table_full_name=(
                    f"{catalog}.{schema}."
                    f"{_sanitize_identifier(current_fact)}"
                ),
                metric_view_full_name=mv[
                    "metric_view"
                ],
                domain_name=model.domain_name,
                measures=mv["measures"],
                dimensions=mv["dimensions"],
                sample_questions=sample_questions,
            )
        )

        security_actions.append(action)

        if first_genie_action is None:
            first_genie_action = action

    # If no facts were present this would have failed earlier, but keep
    # the result deterministic.
    if first_genie_action is None:
        security_actions.append(
            security.record_genie_not_configured(
                model.domain_name
            )
        )

    primary = metric_views[
        fact_table
    ]

    return {
        "catalog": catalog,
        "schema": schema,
        "tables_created": created_tables,
        "metric_view": primary["metric_view"],
        "metric_views": metric_views,
        "measures": primary["measures"],
        "dimensions": primary["dimensions"],
        "genie_space_id": resolved_space_id,
        "security_actions": security_actions,
    }
