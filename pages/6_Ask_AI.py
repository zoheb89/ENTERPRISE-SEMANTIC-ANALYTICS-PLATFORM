import re
import time

import pandas as pd
import streamlit as st

from theme import inject_base_css, render_sidebar_brand, page_header
import security_fabric as security
from registry import list_domains
from ai_provider import chat, is_available, provider_name
from publish_engine import get_sql_connection


inject_base_css()
render_sidebar_brand()

page_header(
    "Ask AI",
    "Natural-language analytics grounded in the published semantic model",
)

if not security.is_configured():
    st.warning("Databricks is not configured for this deployment.")
    st.stop()

domains = list_domains()

if not domains:
    st.info("No published domains yet — publish a semantic model first.")
    if st.button("← Go to Data Onboarding"):
        st.switch_page("pages/1_Data_Onboarding.py")
    st.stop()

domain_names = [d.domain_name for d in domains]
active_name = st.selectbox(
    "Ask about",
    domain_names,
    key="ask_ai_domain_selector",
)
entry = next(d for d in domains if d.domain_name == active_name)

st.caption(
    f"AI provider: **{provider_name()}** · "
    f"Semantic source: `{entry.metric_view}`"
)

if not is_available():
    st.info(
        "Ask AI needs an approved enterprise LLM endpoint. "
        "Configure the Capgemini OpenAI-compatible endpoint in Streamlit "
        "Secrets. Analytics and semantic publishing do not require an LLM."
    )
    st.stop()


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.$]+", value or ""):
        raise ValueError("Unsafe identifier in semantic metadata.")
    return value


def _build_context():
    measures = ", ".join(entry.measures) or "No measures declared"
    dimensions = ", ".join(entry.dimensions) or "No dimensions declared"

    return f"""
DOMAIN: {entry.domain_name}
GOVERNED METRIC VIEW: {_identifier(entry.metric_view)}
FACT TABLE: {_identifier(entry.fact_table)}
MEASURES: {measures}
DIMENSIONS: {dimensions}

The Metric View is the ONLY permitted analytical source.
Do not invent tables, columns, joins, measures, or business definitions.
"""


def _generate_sql(question: str) -> tuple[str, str]:
    metric_view = _identifier(entry.metric_view)

    system = f"""
You are the SQL planner for an enterprise semantic analytics platform.

{_build_context()}

Generate exactly one read-only Databricks SQL query for the user's question.

Rules:
1. Use ONLY the governed Metric View: {metric_view}
2. Never query information_schema, system tables, raw source tables, or other domains.
3. Never use INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, CREATE, COPY, GRANT,
   REVOKE, CALL, SET, USE, or multiple statements.
4. Use declared measures through MEASURE(<measure_name>) when appropriate.
5. Use only dimensions declared by the semantic model.
6. If the question cannot be answered from the model, say so instead of inventing metadata.
7. Return JSON only:
{{
  "sql": "SELECT ...",
  "explanation": "short explanation"
}}
"""

    result = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        max_tokens=1200,
    )

    import json
    payload = result.text.strip()
    payload = re.sub(r"^```(?:json)?", "", payload, flags=re.I).strip()
    payload = re.sub(r"```$", "", payload).strip()
    obj = json.loads(payload)

    return str(obj["sql"]).strip(), str(obj.get("explanation", "")).strip()


def _validate_sql(sql: str):
    compact = re.sub(r"\s+", " ", sql.strip())
    upper = compact.upper()

    if not (upper.startswith("SELECT ") or upper.startswith("WITH ")):
        raise ValueError("The AI generated a non-read-only query.")

    if ";" in compact.rstrip(";"):
        raise ValueError("Multiple SQL statements are not allowed.")

    forbidden = [
        " INSERT ", " UPDATE ", " DELETE ", " MERGE ", " DROP ",
        " ALTER ", " CREATE ", " COPY ", " GRANT ", " REVOKE ",
        " CALL ", " SET ", " USE ", " TRUNCATE ",
    ]
    padded = f" {upper} "
    if any(token in padded for token in forbidden):
        raise ValueError("The generated SQL contains a forbidden operation.")

    if entry.metric_view.lower() not in sql.lower():
        raise ValueError(
            "The generated SQL did not use the governed Metric View."
        )

    if len(sql) > 12000:
        raise ValueError("Generated SQL is unexpectedly large.")


def _execute(sql: str) -> pd.DataFrame:
    with get_sql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [c[0] for c in cur.description or []]
    return pd.DataFrame(rows, columns=columns)


def _explain(question: str, sql: str, result: pd.DataFrame) -> str:
    preview = result.head(20).to_dict(orient="records")

    response = chat(
        [
            {
                "role": "system",
                "content": """
You are an enterprise analytics assistant.
Explain the SQL result in concise business language.
Do not invent facts that are not present in the result.
Mention the semantic source and, if useful, the key calculation.
""",
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"SQL: {sql}\n"
                    f"Result preview: {preview}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=900,
    )
    return response.text


if "ask_ai_messages" not in st.session_state:
    st.session_state.ask_ai_messages = {}

messages = st.session_state.ask_ai_messages.setdefault(active_name, [])

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source"):
            st.caption(msg["source"])
        if msg.get("sql"):
            with st.expander("Show generated SQL"):
                st.code(msg["sql"], language="sql")
        if msg.get("data") is not None:
            st.dataframe(msg["data"], use_container_width=True)

if not messages:
    examples = [
        f"What are the main {entry.measures[0] if entry.measures else 'metrics'}?",
        f"Show the top {entry.dimensions[0] if entry.dimensions else 'categories'} by {entry.measures[0] if entry.measures else 'value'}.",
        "Give me the key business insight from this domain.",
    ]
    st.info("Try one of these:\n\n" + "\n".join(f"- {x}" for x in examples))

question = st.chat_input(f"Ask anything about {active_name}…")

if question:
    messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("Understanding the semantic model and querying Databricks…"):
            try:
                sql, planning_note = _generate_sql(question)
                _validate_sql(sql)
                data = _execute(sql)
                answer = _explain(question, sql, data)

                st.markdown(answer)
                if planning_note:
                    st.caption(planning_note)
                st.caption(f"Source: `{entry.metric_view}`")

                if not data.empty:
                    st.dataframe(data, use_container_width=True)

                with st.expander("Show generated SQL"):
                    st.code(sql, language="sql")

                messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "source": f"Source: {entry.metric_view}",
                        "sql": sql,
                        "data": data,
                    }
                )

            except Exception as exc:
                error = (
                    "I could not safely answer that question from the "
                    f"governed semantic model: {exc}"
                )
                st.error(error)
                messages.append(
                    {
                        "role": "assistant",
                        "content": error,
                    }
                )
