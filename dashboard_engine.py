
"""Capgemini DataPrepAI — governed AI/BI dashboard execution layer.

Phase 2:
1. Read the published semantic metadata.
2. Query the canonical Databricks Metric View using MEASURE().
3. Return real governed results for KPI cards and visualizations.
4. Never query the raw uploaded files for dashboard results.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import pandas as pd


@dataclass
class DashboardCard:
    title: str
    visualization: str
    measure: str
    dimension: str = ""
    rationale: str = ""


def _safe_identifier(value: str) -> str:
    value = str(value or "")
    return value.replace("`", "")


def recommend_dashboard(model):
    measures=[getattr(m,"name",str(m)) for m in getattr(model,"metrics",[])][:8]
    dims=list(getattr(model,"dimensions",[]))[:8]
    cards=[]
    for m in measures[:4]:
        cards.append(DashboardCard(
            title=str(m).replace("_"," ").title(),
            visualization="KPI",
            measure=str(m),
            rationale="Published semantic measure selected as an executive KPI."
        ))
    if measures and dims:
        # Prefer categorical dimensions and avoid internal fact_type for the
        # first-pass executive layout.
        preferred=[d for d in dims if str(d).lower() != "fact_type"]
        preferred=preferred[:3] or dims[:2]
        for m in measures[:4]:
            for d in preferred[:2]:
                cards.append(DashboardCard(
                    title=f"{str(m).replace('_',' ').title()} by {str(d).replace('_',' ').title()}",
                    visualization="Bar",
                    measure=str(m), dimension=str(d),
                    rationale="Measure × governed dimension is a natural analytical breakdown."
                ))
    time_dims=[d for d in dims if any(k in str(d).lower() for k in ("date","month","year","time"))]
    if measures and time_dims:
        cards.append(DashboardCard(
            title=f"{str(measures[0]).replace('_',' ').title()} Trend",
            visualization="Line", measure=str(measures[0]), dimension=str(time_dims[0]),
            rationale="Time-like governed dimension detected; trend visualization recommended."
        ))
    return cards[:12]


def _qident(name: str) -> str:
    """Quote a metric-view field/measure identifier."""
    return "`" + _safe_identifier(name) + "`"


def _qvalue(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _execute(sql: str) -> pd.DataFrame:
    from publish_engine import get_sql_connection
    with get_sql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
    return pd.DataFrame(rows, columns=cols)

def query_metric_view(metric_view: str, measure: str, dimension: str|None=None,
                      filters: dict[str, object]|None=None, limit: int=50) -> pd.DataFrame:
    """Query ONLY the canonical Metric View.

    Databricks Metric Views require MEASURE() around measure references.
    """
    mv=_safe_identifier(metric_view)
    m=_qident(measure)
    where=[]
    for field,value in (filters or {}).items():
        if value not in (None, "", "All"):
            where.append(f"{_qident(field)} = {_qvalue(value)}")
    where_sql=(" WHERE "+" AND ".join(where)) if where else ""

    if dimension:
        d=_qident(dimension)
        sql=f"""
        SELECT {d} AS dimension_value,
               MEASURE({m}) AS metric_value
        FROM {mv}
        {where_sql}
        GROUP BY {d}
        ORDER BY metric_value DESC
        LIMIT {int(max(1,min(limit,500)))}
        """
    else:
        sql=f"""
        SELECT MEASURE({m}) AS metric_value
        FROM {mv}
        {where_sql}
        """
    return _execute(sql)


def query_distinct_dimension(metric_view: str, dimension: str,
                             filters: dict[str, object]|None=None,
                             limit: int=100) -> list[str]:
    mv=_safe_identifier(metric_view)
    where=[]
    for field,value in (filters or {}).items():
        if field == dimension or value in (None, "", "All"):
            continue
        where.append(f"{_qident(field)} = {_qvalue(value)}")
    where_sql=(" WHERE "+" AND ".join(where)) if where else ""
    sql=f"""
    SELECT DISTINCT {_qident(dimension)} AS dimension_value
    FROM {mv}
    {where_sql}
    ORDER BY dimension_value
    LIMIT {int(max(1,min(limit,500)))}
    """
    df=_execute(sql)
    if df.empty:
        return []
    return [x for x in df["dimension_value"].tolist() if x is not None]


def query_dashboard_kpis(metric_view: str, measures: list[str],
                         filters: dict[str, object]|None=None) -> pd.DataFrame:
    mv=_safe_identifier(metric_view)
    select=", ".join(f"MEASURE({_qident(m)}) AS {_qident(m)}" for m in measures)
    where=[]
    for field,value in (filters or {}).items():
        if value not in (None, "", "All"):
            where.append(f"{_qident(field)} = {_qvalue(value)}")
    where_sql=(" WHERE "+" AND ".join(where)) if where else ""
    return _execute(f"SELECT {select} FROM {mv}{where_sql}")


def build_narrative(kpis: dict[str, object], active_filters: dict[str, object]) -> str:
    parts=[]
    for name,value in kpis.items():
        label=str(name).replace("_"," ").title()
        try:
            if pd.isna(value): continue
        except Exception:
            pass
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            parts.append(f"{label} is {value:,.2f}" if float(value)%1 else f"{label} is {value:,.0f}")
        else:
            parts.append(f"{label} is {value}")
    filter_text=[f"{str(k).replace('_',' ').title()} = {v}" for k,v in active_filters.items() if v not in (None,"","All")]
    if filter_text:
        return " • ".join(parts) + (" • Filters: " + ", ".join(filter_text) if parts else "Filters: "+", ".join(filter_text))
    return " • ".join(parts) if parts else "No governed results were returned for the selected filters."


def dashboard_status(metric_view: str) -> dict:
    """Lightweight execution readiness check."""
    try:
        df=_execute(f"SELECT 1 AS ready FROM { _safe_identifier(metric_view) } LIMIT 1")
        return {"ready": True, "message": "Governed Metric View is queryable.", "rows": len(df)}
    except Exception as exc:
        return {"ready": False, "message": str(exc), "rows": 0}
