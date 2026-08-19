
"""Capgemini DataPrepAI — metadata-driven AI/BI dashboard planner."""
from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass
class DashboardCard:
    title: str
    visualization: str
    measure: str
    dimension: str = ""
    rationale: str = ""

def _safe(v):
    return re.sub(r"[^A-Za-z0-9_.$ -]","",str(v or ""))

def recommend_dashboard(model):
    measures=[m.name for m in getattr(model,"metrics",[])][:8]
    dims=list(getattr(model,"dimensions",[]))[:8]
    cards=[]
    for i,m in enumerate(measures[:4]):
        cards.append(DashboardCard(
            title=m.replace("_"," ").title(),
            visualization="KPI",
            measure=m,
            rationale="Published semantic measure selected as an executive KPI."
        ))
    if measures and dims:
        for m in measures[:4]:
            for d in dims[:2]:
                cards.append(DashboardCard(
                    title=f"{m.replace('_',' ').title()} by {d.replace('_',' ').title()}",
                    visualization="Bar",
                    measure=m, dimension=d,
                    rationale="Measure × governed dimension is a natural analytical breakdown."
                ))
    if measures and any("date" in d.lower() or "time" in d.lower() for d in dims):
        d=next(d for d in dims if "date" in d.lower() or "time" in d.lower())
        cards.append(DashboardCard(
            title=f"{measures[0].replace('_',' ').title()} Trend",
            visualization="Line", measure=measures[0], dimension=d,
            rationale="Time-like dimension detected; trend visualization recommended."
        ))
    return cards[:12]
