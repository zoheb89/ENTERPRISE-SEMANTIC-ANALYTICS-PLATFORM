"""
Enterprise Semantic Analytics Platform — core AI engine.

This module implements the full analysis pipeline: Data Intelligence
(ingest -> profile -> quality -> security) and Semantic Intelligence
(entities -> relationships -> facts/dimensions -> measures -> metrics ->
glossary). Analytics Intelligence (dashboards, KPIs, Ask AI) lives in
analytics_engine.py and reads only the SemanticModel this module
produces — it never contains domain-specific logic itself.

Every step below is real, explainable logic — heuristic and statistical,
not a simulated animation. Steps that benefit from an LLM (fuzzy
relationship matching, richer glossary drafting) call out to Databricks
Foundation Model APIs in ai_engine.py and are clearly labeled as
AI-assisted suggestions requiring human review, never auto-applied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

PII_COLUMN_PATTERNS = {
    "name": ["full_name", "first_name", "last_name", "patient_name", "customer_name", "employee_name", "doctor_name", "physician_name"],
    "contact": ["email", "phone", "mobile", "address", "zip", "postal"],
    "identifier": ["ssn", "social_security", "passport", "national_id", "tax_id", "npi"],
    "financial": ["account_number", "card_number", "iban", "routing_number", "salary", "compensation"],
    "health": ["diagnosis", "medication", "condition", "blood_pressure", "heart_rate", "medical_record", "mrn"],
    "dob": ["date_of_birth", "dob", "birth_date"],
}
# Note: bare "name" is deliberately excluded from the "name" category —
# it over-matched reference/lookup columns like site_name or
# product_name, which are not personal data, producing false PII
# positives. Only specific person-identifying name patterns are flagged.


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_pct: float
    distinct_count: int
    row_count: int
    uniqueness_ratio: float
    sample_values: list
    pii_category: str | None = None


@dataclass
class TableProfile:
    name: str
    row_count: int
    columns: list[ColumnProfile]
    df: pd.DataFrame = field(repr=False)
    duplicate_row_count: int = 0
    quality_warnings: list[str] = field(default_factory=list)


@dataclass
class RelationshipCandidate:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    confidence: float
    reason: str
    is_ai_suggested: bool = False
    is_many_to_many: bool = False


@dataclass
class BusinessMetric:
    name: str
    expression: str
    table: str
    description: str


@dataclass
class GlossaryEntry:
    term: str
    definition: str
    source_column: str


@dataclass
class SemanticModel:
    domain_name: str
    tables: dict[str, TableProfile]
    relationships: list[RelationshipCandidate]
    facts: list[str]
    dimensions: list[str]
    metrics: list[BusinessMetric] = field(default_factory=list)
    glossary: list[GlossaryEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pii_findings: dict[str, list[str]] = field(default_factory=dict)


def scan_metadata(files: dict[str, pd.DataFrame]) -> dict[str, TableProfile]:
    profiles = {}
    for name, df in files.items():
        row_count = len(df)
        dup_count = int(df.duplicated().sum()) if row_count else 0
        columns = []
        for col in df.columns:
            series = df[col]
            distinct = series.nunique(dropna=True)
            null_pct = series.isna().mean() * 100 if row_count else 0.0
            uniqueness = (distinct / row_count) if row_count else 0.0
            sample = series.dropna().unique()[:5].tolist()
            columns.append(ColumnProfile(
                name=col, dtype=str(series.dtype), null_pct=round(null_pct, 1),
                distinct_count=int(distinct), row_count=row_count,
                uniqueness_ratio=round(uniqueness, 4), sample_values=sample,
            ))
        profiles[name] = TableProfile(name=name, row_count=row_count, columns=columns, df=df, duplicate_row_count=dup_count)
    return profiles


def detect_data_quality_issues(profiles: dict[str, TableProfile]) -> None:
    for profile in profiles.values():
        if profile.duplicate_row_count > 0:
            pct = (profile.duplicate_row_count / profile.row_count * 100) if profile.row_count else 0
            profile.quality_warnings.append(
                f"{profile.duplicate_row_count} duplicate row(s) detected ({pct:.1f}% of table)"
            )
        for col in profile.columns:
            if col.null_pct > 30:
                profile.quality_warnings.append(f"Column '{col.name}' is {col.null_pct:.0f}% null")
            if col.distinct_count == 1 and profile.row_count > 1:
                profile.quality_warnings.append(f"Column '{col.name}' has only one distinct value across {profile.row_count} rows")


def classify_pii(profiles: dict[str, TableProfile]) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {}
    for table_name, profile in profiles.items():
        flagged = []
        for col in profile.columns:
            col_lower = col.name.lower()
            for category, patterns in PII_COLUMN_PATTERNS.items():
                if any(p in col_lower for p in patterns):
                    col.pii_category = category
                    flagged.append(col.name)
                    break
        if flagged:
            findings[table_name] = flagged
    return findings


def _normalize_col_name(name: str) -> str:
    n = re.sub(r'[^a-z0-9]', '', name.lower())
    n = re.sub(r'^(fk|pk)', '', n)
    return n


def _value_overlap_ratio(series_a: pd.Series, series_b: pd.Series, sample_size: int = 500) -> float:
    a_vals = set(series_a.dropna().astype(str).unique()[:sample_size])
    if not a_vals:
        return 0.0
    b_vals = set(series_b.dropna().astype(str).unique()[:sample_size * 4])
    if not b_vals:
        return 0.0
    return len(a_vals & b_vals) / len(a_vals)


def detect_relationships(profiles: dict[str, TableProfile]) -> list[RelationshipCandidate]:
    candidates: list[RelationshipCandidate] = []
    table_names = list(profiles.keys())

    for i, t1 in enumerate(table_names):
        for t2 in table_names[i + 1:]:
            p1, p2 = profiles[t1], profiles[t2]
            for c1 in p1.columns:
                for c2 in p2.columns:
                    if _normalize_col_name(c1.name) != _normalize_col_name(c2.name):
                        continue
                    if _normalize_col_name(c1.name) in ("", "name", "date", "description"):
                        continue

                    overlap = _value_overlap_ratio(p1.df[c1.name], p2.df[c2.name])
                    if overlap < 0.5:
                        continue

                    asymmetry = abs(c1.uniqueness_ratio - c2.uniqueness_ratio)
                    confidence = min(1.0, 0.5 * overlap + 0.3 * (1 if asymmetry > 0.3 else 0.5) + 0.2)

                    if c1.uniqueness_ratio >= c2.uniqueness_ratio:
                        pk_table, pk_col, fk_table, fk_col = t1, c1.name, t2, c2.name
                        pk_uniqueness, fk_uniqueness = c1.uniqueness_ratio, c2.uniqueness_ratio
                    else:
                        pk_table, pk_col, fk_table, fk_col = t2, c2.name, t1, c1.name
                        pk_uniqueness, fk_uniqueness = c2.uniqueness_ratio, c1.uniqueness_ratio

                    is_m2m = pk_uniqueness < 0.8 and fk_uniqueness < 0.8

                    reason = (
                        f"Column names match ({c1.name} ~ {c2.name}); "
                        f"{overlap*100:.0f}% of values overlap; "
                        f"{pk_table}.{pk_col} looks like the primary key "
                        f"(uniqueness {pk_uniqueness*100:.0f}%)"
                    )
                    if is_m2m:
                        reason += " — neither side is highly unique; possible many-to-many relationship"

                    candidates.append(RelationshipCandidate(
                        from_table=fk_table, from_column=fk_col,
                        to_table=pk_table, to_column=pk_col,
                        confidence=round(confidence, 2), reason=reason,
                        is_many_to_many=is_m2m,
                    ))

    candidates.sort(key=lambda c: -c.confidence)
    seen = set()
    deduped = []
    for c in candidates:
        key = (c.from_table, c.from_column)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


def _looks_like_id_column(col_name: str, dtype: str) -> bool:
    if "float" in dtype:
        return False
    name_lower = col_name.lower()
    return name_lower.endswith("id") or name_lower == "id"


CATEGORY_NAME_SIGNALS = [
    "decile", "rating", "score", "tier", "grade", "level", "rank",
    "class", "category", "segment", "quartile", "quintile", "stars",
]


def _looks_like_rating_or_category_column(col: ColumnProfile, row_count: int) -> bool:
    """
    A column is treated as a rating/category (excluded from metrics) only
    if it's BOTH low-cardinality AND named like a rating/category.
    Cardinality alone is not sufficient: a genuine additive count column
    (e.g. nrx_count, ranging 0-7 in practice) can have very few distinct
    values without being a rating scale — excluding it on cardinality
    alone was a real false positive, caught by testing against real
    data, that silently dropped a legitimate metric a domain expert
    would expect to see (e.g. "Total New Prescriptions").
    """
    if "int" not in col.dtype or row_count == 0:
        return False
    name_lower = col.name.lower()
    name_signals = any(sig in name_lower for sig in CATEGORY_NAME_SIGNALS)
    low_cardinality = col.distinct_count <= 15 and (col.distinct_count / row_count) < 0.5
    return low_cardinality and name_signals


NON_ADDITIVE_PATTERNS = [
    "rate", "ratio", "percent", "pct", "score", "average", "avg",
    "age", "temperature", "pressure", "index", "level",
]


def _looks_non_additive(col_name: str) -> bool:
    """
    A column whose name signals it's a measurement/rate/ratio rather than
    a genuine additive quantity (heart_rate, conversion_rate, avg_score,
    blood_pressure) should never be proposed as a SUM() metric — summing
    a rate or a percentage across rows produces a number with no real
    business meaning. These are legitimate candidates for AVG() instead,
    which the metric generator does not yet propose automatically (a
    human reviewing the draft can add it) — the point of this check is
    only to keep an obviously wrong SUM() out of the auto-generated set.
    """
    name_lower = col_name.lower()
    return any(p in name_lower for p in NON_ADDITIVE_PATTERNS)


def classify_tables(profiles: dict[str, TableProfile], relationships: list[RelationshipCandidate]) -> tuple[list[str], list[str]]:
    fk_from_tables = {r.from_table for r in relationships}
    pk_to_tables = {r.to_table for r in relationships}

    facts, dimensions = [], []
    for name, profile in profiles.items():
        if name in pk_to_tables:
            dimensions.append(name)
            continue

        numeric_cols = [c for c in profile.columns if "int" in c.dtype or "float" in c.dtype]
        genuine_measures = [
            c for c in numeric_cols
            if not _looks_like_id_column(c.name, c.dtype)
            and not _looks_like_rating_or_category_column(c, profile.row_count)
        ]
        has_outgoing_fk = name in fk_from_tables

        if has_outgoing_fk and len(genuine_measures) >= 1:
            facts.append(name)
        else:
            dimensions.append(name)

    return facts, dimensions


def generate_metrics(model_tables: dict[str, TableProfile], facts: list[str], relationships: list[RelationshipCandidate]) -> list[BusinessMetric]:
    metrics = []
    for fact_name in facts:
        profile = model_tables[fact_name]
        related_fk_cols = {r.from_column for r in relationships if r.from_table == fact_name}
        for c in profile.columns:
            if c.name in related_fk_cols:
                continue
            is_id = _looks_like_id_column(c.name, c.dtype)
            is_rating = _looks_like_rating_or_category_column(c, profile.row_count)
            is_non_additive = _looks_non_additive(c.name)
            if ("int" in c.dtype or "float" in c.dtype) and not is_id and not is_rating:
                if is_non_additive:
                    # A rate/measurement/score column (e.g. heart_rate,
                    # conversion_rate) shouldn't be summed, but AVG() is
                    # a genuinely meaningful metric for it -- excluding
                    # it entirely was a real gap: a healthcare demo
                    # naming "average heart rate" as an expected metric
                    # would otherwise never see it generated.
                    metrics.append(BusinessMetric(
                        name=f"Average {c.name.replace('_', ' ').title()}",
                        expression=f"AVG({c.name})",
                        table=fact_name,
                        description=f"Average {c.name} across all {fact_name} records",
                    ))
                else:
                    metrics.append(BusinessMetric(
                        name=f"Total {c.name.replace('_', ' ').title()}",
                        expression=f"SUM({c.name})",
                        table=fact_name,
                        description=f"Sum of {c.name} across all {fact_name} records",
                    ))
        clean_name = fact_name.replace(".csv", "").replace(".xlsx", "").replace("_", " ").title()
        metrics.append(BusinessMetric(
            name=f"{clean_name} Count", expression="COUNT(*)", table=fact_name,
            description=f"Total number of {fact_name} records",
        ))
    return metrics


def generate_glossary(model_tables: dict[str, TableProfile]) -> list[GlossaryEntry]:
    entries = []
    seen_terms = set()
    for table_name, profile in model_tables.items():
        for c in profile.columns:
            term = c.name.replace("_", " ").title()
            if term in seen_terms:
                continue
            seen_terms.add(term)
            entries.append(GlossaryEntry(
                term=term, definition=f"Column '{c.name}' from {table_name} ({c.dtype})",
                source_column=f"{table_name}.{c.name}",
            ))
    return entries


def run_full_analysis(files: dict[str, pd.DataFrame], domain_name: str) -> SemanticModel:
    profiles = scan_metadata(files)
    detect_data_quality_issues(profiles)
    pii_findings = classify_pii(profiles)
    relationships = detect_relationships(profiles)
    facts, dimensions = classify_tables(profiles, relationships)
    metrics = generate_metrics(profiles, facts, relationships)
    glossary = generate_glossary(profiles)

    warnings = []
    for r in relationships:
        if r.is_many_to_many:
            warnings.append(f"Many-to-many candidate: {r.from_table}.{r.from_column} <-> {r.to_table}.{r.to_column}")
    if not facts:
        warnings.append("No fact table confidently identified — upload a table with a numeric measure and a foreign key to another table")
    referenced = {r.to_table for r in relationships}
    fk_sources = {r.from_table for r in relationships}
    unreferenced_dims = [d for d in dimensions if d not in referenced and d not in fk_sources]
    for d in unreferenced_dims:
        warnings.append(f"'{d}' has no detected relationship to any other table — possible missing dimension link")

    return SemanticModel(
        domain_name=domain_name, tables=profiles, relationships=relationships,
        facts=facts, dimensions=dimensions, metrics=metrics, glossary=glossary,
        warnings=warnings, pii_findings=pii_findings,
    )
