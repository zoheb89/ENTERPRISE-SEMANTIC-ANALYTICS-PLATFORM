"""
AI assistance layer.

The core semantic engine does not depend on an LLM. This module adds
optional enterprise-LLM assistance for:
- fuzzy relationship suggestions
- glossary drafting
- natural-language-to-SQL Ask AI

All LLM-generated relationships remain suggestions until reviewed.
"""
from __future__ import annotations

import json
import re

from semantic_engine import RelationshipCandidate
from ai_provider import chat, extract_json, is_available


def _relationship_prompt(profiles, already_found):
    matched = {(r.from_table, r.from_column) for r in already_found}
    columns = []
    for table_name, profile in profiles.items():
        for col in profile.columns:
            if (table_name, col.name) in matched:
                continue
            columns.append({
                "table": table_name,
                "column": col.name,
                "dtype": col.dtype,
                "null_pct": col.null_pct,
                "distinct_count": col.distinct_count,
                "sample_values": [str(v) for v in col.sample_values[:5]],
            })

    return f"""
You are an enterprise data-modeling assistant.
Suggest only high-quality candidate relationships between columns in
different tables when the columns plausibly represent the same business key.

IMPORTANT:
- Do not infer a relationship merely because two columns are integer IDs.
- Prefer semantic/name evidence, value overlap, uniqueness/cardinality,
  and primary-key/foreign-key direction.
- Never use a fact table's own row identifier as a foreign key merely
  because another ID has a similar datatype.
- Return suggestions only; a human/system validation layer will decide
  whether they enter the governed model.

Candidate columns:
{json.dumps(columns, indent=2)}

Return ONLY JSON:
[
  {{
    "table_a": "...",
    "column_a": "...",
    "table_b": "...",
    "column_b": "...",
    "confidence": 0.0,
    "reason": "..."
  }}
]
"""


def suggest_fuzzy_relationships(profiles, already_found):
    if not is_available():
        return []

    try:
        result = chat(
            [
                {
                    "role": "system",
                    "content": "You are a conservative enterprise data-modeling assistant.",
                },
                {"role": "user", "content": _relationship_prompt(profiles, already_found)},
            ],
            temperature=0.0,
            max_tokens=1800,
        )
        raw = extract_json(result.text)
    except Exception:
        return []

    output = []
    for item in raw if isinstance(raw, list) else []:
        try:
            output.append(
                RelationshipCandidate(
                    from_table=str(item["table_a"]),
                    from_column=str(item["column_a"]),
                    to_table=str(item["table_b"]),
                    to_column=str(item["column_b"]),
                    confidence=min(0.95, max(0.0, float(item.get("confidence", 0.5)))),
                    reason=f"AI suggestion: {item.get('reason', 'semantic similarity')}",
                    is_ai_suggested=True,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return output


def draft_glossary_entries(profiles, domain_name):
    if not is_available():
        return []

    columns = []
    for table_name, profile in profiles.items():
        for col in profile.columns:
            columns.append(
                {
                    "table": table_name,
                    "column": col.name,
                    "dtype": col.dtype,
                    "samples": [str(v) for v in col.sample_values[:3]],
                }
            )

    prompt = f"""
Create concise business glossary definitions for the {domain_name} domain.
Only define terms that are directly supported by the supplied metadata.
Return JSON only:
[{{"term":"...", "definition":"...", "source_column":"table.column"}}]

Metadata:
{json.dumps(columns, indent=2)}
"""
    try:
        from semantic_engine import GlossaryEntry
        result = chat(
            [
                {"role": "system", "content": "You are a conservative enterprise business glossary assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1600,
        )
        rows = extract_json(result.text)
        return [
            GlossaryEntry(
                term=str(x["term"]),
                definition=str(x["definition"]),
                source_column=str(x["source_column"]),
            )
            for x in rows if all(k in x for k in ("term", "definition", "source_column"))
        ]
    except Exception:
        return []
