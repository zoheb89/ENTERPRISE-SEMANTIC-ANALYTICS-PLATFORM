"""
Enterprise Semantic Analytics Platform — AI-Assisted Layer.

Purpose
-------
Provides the optional LLM-assisted layer for:
1. Fuzzy cross-table relationship suggestions.
2. Business glossary drafting.

Important architecture rule
---------------------------
The deterministic semantic engine remains authoritative for governed
relationships. LLM output is only a suggestion and is validated before it
can reach the UI.

AI relationship suggestions are:
- cross-table only
- restricted to real tables/columns in the uploaded metadata
- rejected when the model suggests the same table on both sides
- rejected when confidence is below the review threshold
- deduplicated
- never automatically merged into the governed semantic model

The implementation uses the Databricks Foundation Model API through a direct
REST request and does not require the openai Python package.
"""

from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from semantic_engine import RelationshipCandidate, GlossaryEntry
import security_fabric as security


# =============================================================================
# CONFIGURATION
# =============================================================================

FOUNDATION_MODEL_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"

# AI suggestions below this score are intentionally hidden.
#
# This is NOT a statistical probability of correctness. It is an LLM-provided
# confidence score used as a review-quality gate.
AI_RELATIONSHIP_CONFIDENCE_THRESHOLD = 0.70

# Keep only a manageable number of AI suggestions for human review.
MAX_AI_RELATIONSHIP_SUGGESTIONS = 20


# =============================================================================
# FOUNDATION MODEL CALL
# =============================================================================

def _query_foundation_model(
    prompt: str,
    max_tokens: int = 900,
) -> str:
    """
    Call the configured Databricks Foundation Model endpoint.

    This function is intentionally isolated so the AI provider can later be
    replaced without changing the semantic-model UI.
    """

    import requests

    if not security.is_configured():
        raise RuntimeError(
            "Databricks AI configuration is not available."
        )

    w = security.get_workspace_client()

    host = st.secrets["DATABRICKS_HOST"].rstrip("/")

    headers = w.config.authenticate()

    url = (
        f"{host}/serving-endpoints/"
        f"{FOUNDATION_MODEL_ENDPOINT}/invocations"
    )

    body = {
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }

    response = requests.post(
        url,
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    try:
        return (
            data["choices"][0]["message"]["content"]
            .strip()
        )
    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise RuntimeError(
            "Unexpected Foundation Model response format."
        ) from exc


# =============================================================================
# JSON HELPERS
# =============================================================================

def _clean_json_response(raw: str) -> str:
    """
    Remove common Markdown code fences around an LLM JSON response.
    """

    cleaned = raw.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned.strip()


def _parse_json_array(raw: str) -> list[dict[str, Any]]:
    """
    Parse an LLM response expected to contain a JSON array.

    Returns an empty list rather than allowing malformed AI output to
    contaminate the semantic-model pipeline.
    """

    cleaned = _clean_json_response(raw)

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    if not isinstance(value, list):
        return []

    return [
        item
        for item in value
        if isinstance(item, dict)
    ]


# =============================================================================
# METADATA VALIDATION
# =============================================================================

def _build_column_metadata(
    profiles: dict,
) -> tuple[set[str], dict[str, set[str]]]:
    """
    Build authoritative table/column allow-lists from the actual uploaded
    metadata.

    The LLM is never trusted to invent a table or column.
    """

    valid_tables = set(profiles.keys())

    valid_columns: dict[str, set[str]] = {}

    for table_name, profile in profiles.items():
        valid_columns[table_name] = {
            column.name
            for column in profile.columns
        }

    return valid_tables, valid_columns


def _validate_ai_relationship(
    suggestion: dict[str, Any],
    valid_tables: set[str],
    valid_columns: dict[str, set[str]],
) -> bool:
    """
    Validate the structural correctness of an LLM relationship suggestion.
    """

    table_a = suggestion.get("table_a")
    column_a = suggestion.get("column_a")
    table_b = suggestion.get("table_b")
    column_b = suggestion.get("column_b")

    # All fields must be strings.
    if not all(
        isinstance(value, str)
        for value in (
            table_a,
            column_a,
            table_b,
            column_b,
        )
    ):
        return False

    # The relationship must be CROSS-TABLE.
    #
    # This specifically prevents:
    # Store.store_id -> Store.store_name
    # Product.product_id -> Product.product_name
    # Customer.customer_id -> Customer.customer_name
    if table_a == table_b:
        return False

    # Never accept hallucinated tables.
    if table_a not in valid_tables:
        return False

    if table_b not in valid_tables:
        return False

    # Never accept hallucinated columns.
    if column_a not in valid_columns.get(
        table_a,
        set(),
    ):
        return False

    if column_b not in valid_columns.get(
        table_b,
        set(),
    ):
        return False

    return True


# =============================================================================
# AI RELATIONSHIP SUGGESTIONS
# =============================================================================

def suggest_fuzzy_relationships(
    profiles: dict,
    already_found: list,
) -> list:
    """
    Ask the LLM to identify likely cross-table relationships that the
    deterministic name-matching engine did not identify.

    The result is strictly a suggestion layer.

    It is NOT:
        - a replacement for deterministic matching
        - a governed relationship
        - automatically published
        - a probability-calibrated prediction

    Every candidate passes structural validation and a confidence threshold
    before being returned.
    """

    if not security.is_configured():
        return []

    valid_tables, valid_columns = (
        _build_column_metadata(profiles)
    )

    # Columns already involved in deterministic relationships are excluded.
    # This prevents the LLM from second-guessing known relationships.
    already_matched = {
        (
            r.from_table,
            r.from_column,
        )
        for r in already_found
    }

    column_summary: list[dict[str, Any]] = []

    for table_name, profile in profiles.items():

        for column in profile.columns:

            if (
                table_name,
                column.name,
            ) in already_matched:
                continue

            column_summary.append(
                {
                    "table": table_name,
                    "column": column.name,
                    "dtype": column.dtype,
                    "row_count": profile.row_count,
                    "null_pct": column.null_pct,
                    "distinct_count": column.distinct_count,
                    "uniqueness_ratio": column.uniqueness_ratio,
                    "sample_values": [
                        str(value)
                        for value in column.sample_values[:5]
                    ],
                }
            )

    if len(column_summary) < 2:
        return []

    prompt = f"""
You are an enterprise semantic-modeling assistant.

Your task is to identify POSSIBLE JOIN RELATIONSHIPS between DIFFERENT
DATABASE TABLES.

The deterministic semantic engine has already checked obvious exact-name
relationships. Do not repeat those relationships.

IMPORTANT RULES:

1. A relationship MUST connect two DIFFERENT tables.
2. Never suggest a relationship between two columns in the same table.
3. Never treat an ID column and a descriptive column in the SAME table as a
   relationship.
   Example:
       Store.store_id -> Store.store_name
   is INVALID.
4. Never invent a table or column.
5. Only use tables and columns present in the supplied metadata.
6. Prefer identifier-to-identifier relationships.
7. Consider:
   - column names
   - data types
   - uniqueness
   - null percentage
   - distinct counts
   - sample values
   - likely primary-key / foreign-key semantics
8. A relationship should represent the same real-world entity across tables.
9. If there is no reasonably strong cross-table relationship, return [].
10. Do not suggest descriptive fields such as name, description, address, etc.
    as join keys unless there is very strong evidence.

The confidence value is an AI REVIEW SCORE from 0.0 to 1.0.
It is NOT a statistically calibrated probability.

Only return suggestions with confidence >= 0.70.

Available metadata:

{json.dumps(column_summary, indent=2)}

Respond with ONLY a JSON array.

Exact response shape:

[
  {{
    "table_a": "table name",
    "column_a": "column name",
    "table_b": "table name",
    "column_b": "column name",
    "confidence": 0.0,
    "reason": "one concise sentence explaining the evidence"
  }}
]

If there are no strong cross-table relationships, return:

[]
"""

    try:

        raw = _query_foundation_model(
            prompt,
            max_tokens=1200,
        )

        suggestions = _parse_json_array(raw)

    except Exception as exc:

        st.warning(
            "AI relationship suggestions unavailable "
            f"this run: {exc}"
        )

        return []

    candidates: list[
        RelationshipCandidate
    ] = []

    seen_relationships: set[
        tuple[str, str, str, str]
    ] = set()

    for suggestion in suggestions:

        # ---------------------------------------------------------------
        # Structural validation
        # ---------------------------------------------------------------

        if not _validate_ai_relationship(
            suggestion,
            valid_tables,
            valid_columns,
        ):
            continue

        table_a = suggestion["table_a"]
        column_a = suggestion["column_a"]
        table_b = suggestion["table_b"]
        column_b = suggestion["column_b"]

        # ---------------------------------------------------------------
        # Confidence validation
        # ---------------------------------------------------------------

        try:
            confidence = float(
                suggestion.get(
                    "confidence",
                    0.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        # Reject invalid numeric values.
        if not 0.0 <= confidence <= 1.0:
            continue

        # Low-quality AI guesses never reach the UI.
        if (
            confidence
            < AI_RELATIONSHIP_CONFIDENCE_THRESHOLD
        ):
            continue

        # ---------------------------------------------------------------
        # Duplicate validation
        # ---------------------------------------------------------------

        relationship_key = (
            table_a,
            column_a,
            table_b,
            column_b,
        )

        reverse_key = (
            table_b,
            column_b,
            table_a,
            column_a,
        )

        if (
            relationship_key in seen_relationships
            or reverse_key in seen_relationships
        ):
            continue

        seen_relationships.add(
            relationship_key
        )

        # ---------------------------------------------------------------
        # Reason
        # ---------------------------------------------------------------

        reason = str(
            suggestion.get(
                "reason",
                "Strong semantic similarity between "
                "identifier columns across tables.",
            )
        ).strip()

        candidates.append(
            RelationshipCandidate(
                from_table=table_a,
                from_column=column_a,
                to_table=table_b,
                to_column=column_b,
                confidence=round(
                    confidence,
                    2,
                ),
                reason=(
                    "AI suggestion: "
                    + reason
                ),
                is_ai_suggested=True,
            )
        )

    # Highest-confidence suggestions first.
    candidates.sort(
        key=lambda candidate: (
            -candidate.confidence
        )
    )

    return candidates[
        :MAX_AI_RELATIONSHIP_SUGGESTIONS
    ]


# =============================================================================
# BUSINESS GLOSSARY
# =============================================================================

def draft_glossary_entries(
    profiles: dict,
    domain_name: str,
) -> list:
    """
    Ask the LLM to draft business-friendly glossary definitions.

    Glossary entries are suggestions and require human review.
    """

    if not security.is_configured():
        return []

    columns: list[dict[str, Any]] = []

    for table_name, profile in profiles.items():

        for column in profile.columns:

            columns.append(
                {
                    "table": table_name,
                    "column": column.name,
                    "dtype": column.dtype,
                    "row_count": profile.row_count,
                    "null_pct": column.null_pct,
                    "distinct_count": column.distinct_count,
                    "uniqueness_ratio": column.uniqueness_ratio,
                }
            )

    if not columns:
        return []

    prompt = f"""
You are drafting a business glossary for the {domain_name} domain.

For every column below, write ONE concise, business-friendly definition.

Requirements:

- Describe the business meaning, not implementation details.
- Do not invent facts that cannot be inferred from the metadata.
- Keep each definition concise.
- Preserve the exact table and column names.
- Return only JSON.

Columns:

{json.dumps(columns, indent=2)}

Respond with ONLY:

[
  {{
    "table": "table name",
    "column": "column name",
    "definition": "business-friendly definition"
  }}
]
"""

    try:

        raw = _query_foundation_model(
            prompt,
            max_tokens=1800,
        )

        drafts = _parse_json_array(raw)

    except Exception as exc:

        st.warning(
            "AI glossary drafting unavailable "
            f"this run: {exc}"
        )

        return []

    valid_tables, valid_columns = (
        _build_column_metadata(profiles)
    )

    entries: list[GlossaryEntry] = []

    seen: set[
        tuple[str, str]
    ] = set()

    for draft in drafts:

        table_name = draft.get("table")
        column_name = draft.get("column")
        definition = draft.get("definition")

        if not isinstance(
            table_name,
            str,
        ):
            continue

        if not isinstance(
            column_name,
            str,
        ):
            continue

        if not isinstance(
            definition,
            str,
        ):
            continue

        if table_name not in valid_tables:
            continue

        if column_name not in valid_columns.get(
            table_name,
            set(),
        ):
            continue

        definition = definition.strip()

        if not definition:
            continue

        key = (
            table_name,
            column_name,
        )

        if key in seen:
            continue

        seen.add(key)

        entries.append(
            GlossaryEntry(
                term=column_name
                .replace("_", " ")
                .title(),
                definition=definition,
                source_column=(
                    f"{table_name}.{column_name}"
                ),
            )
        )

    return entries
