# Enterprise Semantic Analytics Platform

A single Streamlit application that turns source data into a governed,
metadata-driven semantic model and analytics experience.

## Product flow

ANY SOURCE
→ ingestion
→ metadata/data quality
→ relationship discovery
→ fact/dimension classification
→ measures/KPIs/glossary
→ governed semantic model
→ Databricks Delta tables + Metric View
→ metadata registry
→ domain-agnostic Analytics
→ optional enterprise LLM Ask AI
→ optional Databricks Genie integration

## Important architecture boundary

The product does NOT try to replace Databricks.

Databricks is the governed execution/data platform:
- Delta tables
- SQL Warehouse
- Unity Catalog
- Metric Views
- Lakehouse processing
- optional Genie

The Streamlit application is the semantic automation/orchestration layer.

## Authentication for the Free Edition POC

Use a workspace PAT:

DATABRICKS_HOST
DATABRICKS_TOKEN
DATABRICKS_WAREHOUSE_ID
DATABRICKS_CATALOG

Do not use:
DATABRICKS_CLIENT_ID
DATABRICKS_CLIENT_SECRET

Do not configure GENIE_SPACE_ID for the current Free Edition publish flow.

## Ask AI

Ask AI is provider-neutral.

Preferred enterprise path:
Capgemini-approved OpenAI-compatible endpoint.

Secrets:
AI_PROVIDER=capgemini
CAPGEMINI_LLM_BASE_URL=...
CAPGEMINI_LLM_API_KEY=...
CAPGEMINI_LLM_MODEL=...

The LLM never gets unrestricted database access. It receives the selected
domain's governed semantic metadata, generates one read-only query against
the published Metric View, and the application validates the query before
execution.

If no approved LLM is configured, the semantic platform and Analytics still
work. Ask AI is explicitly disabled rather than pretending an LLM exists.

## Genie

Genie is an optional Databricks-native AI experience.

For the Free Edition POC, do not make Genie management a prerequisite for
publishing. A Genie Agent can be configured separately in Databricks when
available. The platform's Metric Views remain the governed semantic contract.

## Current supported source uploads

CSV, Excel, JSON, Parquet.

The Data Engine is intentionally connector-based so database/API/cloud
storage/streaming adapters can be added without changing the semantic,
analytics or registry layers.

## Run

pip install -r requirements.txt
streamlit run app.py

## Streamlit Community Cloud

Point the application to app.py, use Python 3.11, and add the secrets from
.streamlit/secrets.toml.example.

## Enterprise hardening roadmap

For production beyond the Invent demo:
- object-storage/Volume + COPY INTO or Auto Loader for large files
- Lakeflow pipeline generation for Bronze/Silver/Gold
- connector adapters for databases/APIs/message buses
- enterprise identity/OAuth instead of a personal PAT
- approved enterprise LLM gateway
- formal SQL parser/AST validation
- model/version audit trail
- human approval workflow for PII/PHI and semantic certification
- automated tests and CI/CD
