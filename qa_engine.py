
"""
INVENT runtime Quality Gate.

The QA engine is metadata-driven. It never contains domain-specific rules.
It validates the in-memory SemanticModel before publication and returns
structured results suitable for both UI display and CI regression tests.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable

from semantic_engine import SemanticModel


@dataclass
class QACheck:
    category: str
    name: str
    status: str  # PASS / WARN / FAIL
    message: str
    blocking: bool = False

    def to_dict(self):
        return asdict(self)


def _check(
    checks: list[QACheck],
    category: str,
    name: str,
    status: str,
    message: str,
    blocking: bool = False,
):
    checks.append(
        QACheck(
            category=category,
            name=name,
            status=status,
            message=message,
            blocking=blocking,
        )
    )


def validate_semantic_model(model: SemanticModel) -> dict:
    checks: list[QACheck] = []

    # ---------------------------------------------------------------
    # Model integrity
    # ---------------------------------------------------------------
    _check(
        checks, "Model", "Tables profiled",
        "PASS" if model.tables else "FAIL",
        f"{len(model.tables)} table(s) profiled.",
        not bool(model.tables),
    )

    _check(
        checks, "Model", "Fact classification",
        "PASS" if model.facts else "FAIL",
        f"{len(model.facts)} fact table(s) identified.",
        not bool(model.facts),
    )

    _check(
        checks, "Model", "Dimension classification",
        "PASS" if model.dimensions else "WARN",
        f"{len(model.dimensions)} dimension table(s) identified.",
    )

    # Every classified table must belong to exactly one role.
    classified = set(model.facts) | set(model.dimensions)
    unclassified = set(model.tables) - classified
    overlap = set(model.facts) & set(model.dimensions)

    _check(
        checks, "Semantic", "Every table classified",
        "FAIL" if unclassified else "PASS",
        (
            f"Unclassified table(s): {', '.join(sorted(unclassified))}"
            if unclassified
            else "Every table has a fact or dimension role."
        ),
        bool(unclassified),
    )

    _check(
        checks, "Semantic", "Fact/dimension exclusivity",
        "FAIL" if overlap else "PASS",
        (
            f"Table(s) classified as both fact and dimension: "
            f"{', '.join(sorted(overlap))}"
            if overlap
            else "Fact and dimension roles are mutually exclusive."
        ),
        bool(overlap),
    )

    # ---------------------------------------------------------------
    # Relationship integrity
    # ---------------------------------------------------------------
    relationship_keys = set()
    reverse_duplicates = []

    for rel in model.relationships:
        endpoints = frozenset(
            [
                (rel.from_table, rel.from_column),
                (rel.to_table, rel.to_column),
            ]
        )

        if endpoints in relationship_keys:
            reverse_duplicates.append(
                f"{rel.from_table}.{rel.from_column} ↔ "
                f"{rel.to_table}.{rel.to_column}"
            )
        relationship_keys.add(endpoints)

    _check(
        checks, "Relationships", "Duplicate/reverse relationships",
        "FAIL" if reverse_duplicates else "PASS",
        (
            f"Duplicate/reverse edge(s): "
            f"{', '.join(reverse_duplicates)}"
            if reverse_duplicates
            else "No duplicate or reverse relationship edges."
        ),
        bool(reverse_duplicates),
    )

    self_refs = [
        r for r in model.relationships
        if r.from_table == r.to_table
    ]

    _check(
        checks, "Relationships", "Self-reference validity",
        "PASS",
        f"{len(self_refs)} self-referencing relationship(s) retained.",
    )

    m2m = [
        r for r in model.relationships
        if r.is_many_to_many
    ]

    _check(
        checks, "Relationships", "Many-to-many candidates",
        "FAIL" if m2m else "PASS",
        (
            f"{len(m2m)} many-to-many candidate(s) require correction."
            if m2m
            else "No many-to-many relationship remains in the governed graph."
        ),
        bool(m2m),
    )

    invalid_endpoints = [
        r for r in model.relationships
        if r.from_table not in model.tables
        or r.to_table not in model.tables
    ]

    _check(
        checks, "Relationships", "Relationship endpoints",
        "FAIL" if invalid_endpoints else "PASS",
        (
            "One or more relationships reference unknown tables."
            if invalid_endpoints
            else "All relationship endpoints exist in the model."
        ),
        bool(invalid_endpoints),
    )

    fact_to_fact = [
        r for r in model.relationships
        if r.from_table in model.facts
        and r.to_table in model.facts
    ]

    _check(
        checks, "Relationships", "Fact-to-fact relationships",
        "WARN" if fact_to_fact else "PASS",
        (
            f"{len(fact_to_fact)} fact-to-fact relationship(s) detected. "
            "These are retained as facts and must not be labelled dimensions."
            if fact_to_fact
            else "No fact-to-fact relationships detected."
        ),
    )

    # ---------------------------------------------------------------
    # Metrics
    # ---------------------------------------------------------------
    metric_names = [m.name for m in model.metrics]
    duplicate_metrics = {
        n for n in metric_names
        if metric_names.count(n) > 1
    }

    _check(
        checks, "Metrics", "Metric names unique",
        "FAIL" if duplicate_metrics else "PASS",
        (
            f"Duplicate metric names: {', '.join(sorted(duplicate_metrics))}"
            if duplicate_metrics
            else "All metric names are unique."
        ),
        bool(duplicate_metrics),
    )

    invalid_metric_tables = [
        m for m in model.metrics
        if m.table not in model.tables
    ]

    _check(
        checks, "Metrics", "Metric source tables",
        "FAIL" if invalid_metric_tables else "PASS",
        (
            "One or more metrics reference an unknown table."
            if invalid_metric_tables
            else "Every metric references a known table."
        ),
        bool(invalid_metric_tables),
    )

    _check(
        checks, "Metrics", "Metric coverage",
        "PASS" if len(model.metrics) >= len(model.facts) else "FAIL",
        f"{len(model.metrics)} metric(s) generated for {len(model.facts)} fact table(s).",
        len(model.metrics) < len(model.facts),
    )

    # Prevent the known Metric View semantic error before Databricks.
    bad_measure_expressions = [
        m for m in model.metrics
        if not m.expression.strip()
    ]

    _check(
        checks, "Metrics", "Metric expressions",
        "FAIL" if bad_measure_expressions else "PASS",
        (
            "One or more metrics have an empty expression."
            if bad_measure_expressions
            else "All metrics have non-empty expressions."
        ),
        bool(bad_measure_expressions),
    )

    # ---------------------------------------------------------------
    # AI safety
    # ---------------------------------------------------------------
    ai_governed = [
        r for r in model.relationships
        if r.is_ai_suggested
    ]

    _check(
        checks, "AI", "AI suggestions remain review-only",
        "FAIL" if ai_governed else "PASS",
        (
            "An AI-suggested relationship entered the governed graph."
            if ai_governed
            else f"{len(model.ai_suggestions)} AI suggestion(s) are isolated for review."
        ),
        bool(ai_governed),
    )

    # ---------------------------------------------------------------
    # Data quality
    # ---------------------------------------------------------------
    quality_warnings = [
        (table, warning)
        for table, profile in model.tables.items()
        for warning in profile.quality_warnings
    ]

    _check(
        checks, "Data Quality", "Source data warnings",
        "WARN" if quality_warnings else "PASS",
        (
            f"{len(quality_warnings)} source quality warning(s) found."
            if quality_warnings
            else "No source data quality warnings."
        ),
    )

    # ---------------------------------------------------------------
    # Governance
    # ---------------------------------------------------------------
    pii_tables = len(model.pii_findings)

    _check(
        checks, "Governance", "PII / PHI detection",
        "WARN" if pii_tables else "PASS",
        (
            f"{pii_tables} table(s) contain PII/PHI findings. "
            "Security Center review is recommended."
            if pii_tables
            else "No PII/PHI patterns detected."
        ),
    )

    blocking = [c for c in checks if c.blocking and c.status == "FAIL"]
    failures = [c for c in checks if c.status == "FAIL"]
    warnings = [c for c in checks if c.status == "WARN"]
    passed = [c for c in checks if c.status == "PASS"]

    # Score is a quality signal, not a replacement for blocking rules.
    score = round(
        100 * len(passed) / max(len(checks), 1)
    )

    return {
        "score": score,
        "status": "FAIL" if blocking else ("WARN" if warnings else "PASS"),
        "checks": checks,
        "passed": len(passed),
        "warnings": len(warnings),
        "failures": len(failures),
        "blocking_failures": len(blocking),
        "publish_allowed": not bool(blocking),
    }


def run_qa(model: SemanticModel) -> dict:
    return validate_semantic_model(model)
