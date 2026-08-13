"""
Enterprise Semantic Analytics Platform
Metadata-driven Analytics Engine.

This module intentionally contains NO domain-specific logic.

Finance, Healthcare, Retail, Banking, etc. are discovered from the
metadata registry and rendered using the same dashboard engine.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st

from registry import list_domains


def _safe_identifier(value: str) -> str:
    """
    Protect SQL identifiers generated from registry metadata.
    """
    if not value or not re.fullmatch(r"[A-Za-z0-9_.$]+", value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def _get_sql_connection():
    """
    Reuse the application's Databricks SQL connection.

    publish_engine already owns the Databricks connection logic, so the
    analytics layer does not duplicate authentication.
    """
    from publish_engine import get_sql_connection

    return get_sql_connection()


def _query(sql: str) -> pd.DataFrame:
    """
    Execute a read-only analytics query.
    """
    with _get_sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)

            rows = cursor.fetchall()
            description = cursor.description or []

            columns = [
                column[0]
                for column in description
            ]

    return pd.DataFrame(rows, columns=columns)


def _metric_name_to_sql(metric: str) -> str:
    """
    Convert a registry metric name to a safe SQL expression.

    Metric View measures are expected to be used through MEASURE().
    """
    metric = str(metric).strip()

    if not metric:
        raise ValueError("Empty metric name.")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", metric):
        raise ValueError(f"Unsafe metric name: {metric}")

    return f"MEASURE(`{metric}`)"


def _dimension_name_to_sql(dimension: str) -> str:
    dimension = str(dimension).strip()

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dimension):
        raise ValueError(f"Unsafe dimension name: {dimension}")

    return f"`{dimension}`"


def _entry_value(entry: Any, name: str, default=None):
    """
    Registry entries may be dataclasses or dictionaries depending on
    the version of the registry module.
    """
    if isinstance(entry, dict):
        return entry.get(name, default)

    return getattr(entry, name, default)


def _get_domain_entry(domain_name: str):
    domains = list_domains()

    for entry in domains:
        if _entry_value(entry, "domain_name") == domain_name:
            return entry

    return None


def _metric_view(entry) -> str:
    value = _entry_value(entry, "metric_view")

    if not value:
        raise ValueError(
            f"No Metric View is registered for "
            f"{_entry_value(entry, 'domain_name', 'selected domain')}."
        )

    return _safe_identifier(value)


def _get_measures(entry) -> list[str]:
    measures = _entry_value(entry, "measures", [])

    if measures is None:
        return []

    return [str(x) for x in measures if str(x).strip()]


def _get_dimensions(entry) -> list[str]:
    dimensions = _entry_value(entry, "dimensions", [])

    if dimensions is None:
        return []

    return [str(x) for x in dimensions if str(x).strip()]


def _render_kpi_cards(entry):
    """
    Render metadata-driven KPI cards.

    No Finance/Healthcare/Retail-specific code exists here.
    """
    measures = _get_measures(entry)

    if not measures:
        st.info("No measures are registered for this domain yet.")
        return

    # Display at most four KPIs in the first row.
    selected = measures[:4]

    columns = st.columns(len(selected))

    metric_view = _metric_view(entry)

    for column, measure in zip(columns, selected):
        try:
            expression = _metric_name_to_sql(measure)

            sql = f"""
                SELECT {expression} AS metric_value
                FROM {metric_view}
            """

            result = _query(sql)

            value = None

            if not result.empty:
                value = result.iloc[0]["metric_value"]

            with column:
                st.metric(
                    label=measure.replace("_", " ").title(),
                    value=_format_value(value),
                )

        except Exception as exc:
            with column:
                st.metric(
                    label=measure.replace("_", " ").title(),
                    value="—",
                )
                st.caption(f"Unable to calculate: {exc}")


def _format_value(value) -> str:
    if value is None:
        return "—"

    if pd.isna(value):
        return "—"

    if isinstance(value, float):
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"

        if abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"

        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    try:
        number = float(value)

        if abs(number) >= 1_000_000:
            return f"{number / 1_000_000:.2f}M"

        if abs(number) >= 1_000:
            return f"{number / 1_000:.1f}K"

    except Exception:
        pass

    return str(value)


def _render_dimension_analysis(entry):
    """
    Render a generic dimension-versus-measure analysis.

    The first registered dimension and first registered measure are used.
    The dashboard automatically changes when the domain changes.
    """
    dimensions = _get_dimensions(entry)
    measures = _get_measures(entry)

    if not dimensions:
        st.info("No dimensions are registered for this domain.")
        return

    if not measures:
        st.info("No measures are registered for this domain.")
        return

    dimension = dimensions[0]
    measure = measures[0]

    metric_view = _metric_view(entry)

    dim_sql = _dimension_name_to_sql(dimension)
    measure_sql = _metric_name_to_sql(measure)

    sql = f"""
        SELECT
            {dim_sql} AS dimension_value,
            {measure_sql} AS metric_value
        FROM {metric_view}
        GROUP BY {dim_sql}
        ORDER BY metric_value DESC
        LIMIT 15
    """

    result = _query(sql)

    if result.empty:
        st.info("No analytical results are available for this domain.")
        return

    st.subheader(
        f"{measure.replace('_', ' ').title()} by "
        f"{dimension.replace('_', ' ').title()}"
    )

    st.bar_chart(
        result.set_index("dimension_value")["metric_value"]
    )

    with st.expander("View underlying result"):
        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True,
        )


def _render_dimension_selector(entry):
    dimensions = _get_dimensions(entry)
    measures = _get_measures(entry)

    if not dimensions or not measures:
        return

    selected_dimension = st.selectbox(
        "Analyze by",
        dimensions,
        key=f"analytics_dimension_{_entry_value(entry, 'domain_name')}",
    )

    selected_measure = st.selectbox(
        "Measure",
        measures,
        key=f"analytics_measure_{_entry_value(entry, 'domain_name')}",
    )

    metric_view = _metric_view(entry)

    dimension_sql = _dimension_name_to_sql(selected_dimension)
    measure_sql = _metric_name_to_sql(selected_measure)

    sql = f"""
        SELECT
            {dimension_sql} AS dimension_value,
            {measure_sql} AS metric_value
        FROM {metric_view}
        GROUP BY {dimension_sql}
        ORDER BY metric_value DESC
        LIMIT 25
    """

    result = _query(sql)

    if result.empty:
        st.info("No data returned for this analysis.")
        return

    st.bar_chart(
        result.set_index("dimension_value")["metric_value"]
    )

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True,
    )


def render_domain_dashboard(domain_name: str):
    """
    Main public rendering function used by pages/5_Analytics.py.

    Completely metadata-driven:
        domain → registry → Metric View → measures/dimensions → dashboard

    There is intentionally no domain-specific branching here.
    """
    entry = _get_domain_entry(domain_name)

    if entry is None:
        st.error(
            f"Domain '{domain_name}' is not present in the semantic registry."
        )
        return

    metric_view = _metric_view(entry)
    measures = _get_measures(entry)
    dimensions = _get_dimensions(entry)

    st.caption(
        f"Governed source: `{metric_view}`"
    )

    st.markdown("### Key Metrics")

    try:
        _render_kpi_cards(entry)
    except Exception as exc:
        st.warning(
            f"KPI calculation could not be completed: {exc}"
        )

    st.divider()

    st.markdown("### Semantic Analytics")

    try:
        _render_dimension_analysis(entry)
    except Exception as exc:
        st.warning(
            f"Automatic analysis could not be completed: {exc}"
        )

    st.divider()

    st.markdown("### Explore the Semantic Model")

    if dimensions:
        st.write(
            "**Dimensions:** "
            + ", ".join(
                d.replace("_", " ")
                for d in dimensions
            )
        )

    if measures:
        st.write(
            "**Measures:** "
            + ", ".join(
                m.replace("_", " ")
                for m in measures
            )
        )

    with st.expander("Custom dimension / measure analysis"):
        try:
            _render_dimension_selector(entry)
        except Exception as exc:
            st.warning(
                f"Custom analysis could not be completed: {exc}"
            )
