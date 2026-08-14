# INVENT — Enterprise Semantic Analytics Platform

INVENT is a metadata-driven platform that turns tabular enterprise data into
a governed semantic model, publishes it to Databricks Unity Catalog, and
exposes the same governed metrics through Analytics, an approved enterprise
LLM, and Databricks Genie.

## Product promise

INVENT is **domain-agnostic**.

There is no application logic such as:

```python
if domain == "Healthcare":
    ...
elif domain == "Finance":
    ...
```

Domains are discovered from the data and persisted as metadata.

Supported demo domains are loaded from `demo_datasets/` and include:

- Automotive
- Banking
- Energy
- Healthcare
- Human Resources
- Insurance
- Manufacturing
- Retail
- Telecom
- Travel

The same pipeline also accepts new, user-supplied domains.

## End-to-end architecture

```text
ANY TABULAR SOURCE
       |
       v
Data Onboarding
       |
       v
Metadata / Data Quality / PII-PHI
       |
       v
Semantic Intelligence
       |
       +--> deterministic PK/FK inference
       +--> cardinality and shared-dimension analysis
       +--> fact / dimension classification
       +--> measures / metrics
       +--> glossary
       +--> AI suggestions (review-only)
       |
       v
Governed Business Model
       |
       v
Databricks Unity Catalog
       |
       +--> Delta tables
       +--> Metric View(s)
       +--> persistent metadata registry
       |
       +----------------------+-------------------+
       |                      |                   |
       v                      v                   v
    Analytics            Ask AI              Genie Agent
                         Capgemini             Databricks
```

## What is governed

INVENT treats the semantic model as the contract between data and AI.

- Deterministic relationships are validated from metadata, uniqueness,
  containment, primary-key evidence, and shared-key topology.
- AI relationship suggestions are **review-only** and are never silently
  promoted into the governed graph.
- Master/reference tables can contain numeric reference attributes such as
  `standard_cost` without being incorrectly classified as facts.
- Multiple fact tables are supported in one domain.
- Shared/conformed dimensions prevent false many-to-many relationships.
- Reverse duplicate relationship suggestions are canonicalized.
- Fact-to-fact relationships are not converted into dimension joins.
- Metric View queries use Databricks `MEASURE()` semantics.

## Databricks

Databricks is the governed execution/data platform:

- Unity Catalog
- Delta tables
- SQL Warehouse
- Metric Views
- Genie Agents

INVENT is the semantic automation/orchestration layer.

### Required Streamlit secrets

```toml
DATABRICKS_HOST = "https://<workspace>.cloud.databricks.com"
DATABRICKS_TOKEN = "<workspace-pat>"
DATABRICKS_WAREHOUSE_ID = "<sql-warehouse-id>"
DATABRICKS_CATALOG = "invent_semantic_platform"
```

The one-time `databricks_bootstrap.py` utility verifies the workspace,
warehouse and catalog.

For production, use an enterprise workload identity/OAuth configuration
rather than a personal PAT when the target environment supports it.

## Genie — domain-aware and automatic

Current Databricks Genie terminology is **Genie Agent**; the REST API still
uses `/api/2.0/genie/spaces`. Databricks documents the `space_id` path
parameter as a UUID.

INVENT supports three configuration modes:

### 1. Existing Genie Agent per domain — preferred

```toml
[GENIE_SPACES]
Retail = "<retail-agent-id>"
Healthcare = "<healthcare-agent-id>"
Finance = "<finance-agent-id>"
Manufacturing = "<manufacturing-agent-id>"
```

### 2. Legacy/shared Agent

```toml
GENIE_SPACE_ID = "<existing-agent-id>"
```

This is retained for backward compatibility.

### 3. Automatic domain Agent creation

```toml
GENIE_AUTO_CREATE = true
```

If no domain mapping exists, INVENT can create a Genie Agent for the
published domain using the configured SQL Warehouse.

When a domain is published INVENT:

1. creates/updates the domain schema
2. writes all uploaded tables as Delta
3. creates one Metric View per detected fact table
4. resolves the domain's Genie Agent
5. adds the Metric View(s) to the Agent
6. adds domain-specific sample questions
7. adds INVENT governance instructions
8. persists the Agent ID in the metadata registry

Genie management failures do **not** roll back a successful semantic
publication. The UI reports the Genie problem explicitly instead of
pretending the Agent was connected.

If an old `GENIE_SPACE_ID` is malformed or points to a deleted Agent, INVENT
now attempts automatic recovery: it looks for an existing Agent titled
`INVENT — <domain>`, otherwise it creates a replacement when
`GENIE_AUTO_CREATE=true`. This prevents a stale ID from breaking the semantic
publish flow.

The current Databricks Update Space API requires a complete
`serialized_space` replacement; INVENT retrieves the existing serialized
configuration, merges the new Metric View and governance metadata, and
updates it while preserving the existing Agent configuration.

## Genie consumption

The `Analyze → Genie Agent` page supports:

- domain-aware Agent selection
- opening the native Databricks Genie Agent
- programmatic Agent Mode chat from inside INVENT
- follow-up questions in the same Genie conversation
- optional visualization generation

Agent Mode APIs must be enabled by the Databricks workspace administrator.

## Ask AI

Ask AI is separate from Genie.

Default enterprise configuration:

```toml
AI_PROVIDER = "capgemini"

CAPGEMINI_LLM_BASE_URL = "https://api.generative.engine.capgemini.com/v2/11m/invoke"
CAPGEMINI_LLM_API_KEY = "<approved-api-key>"
CAPGEMINI_LLM_MODEL = "openai.gpt-5.1"

# Default for the current Capgemini gateway integration.
CAPGEMINI_AUTH_HEADER = "x-api-key"
```

The application does not expose the API key to the browser.

Ask AI receives the selected domain's governed metadata, generates a
read-only analytical query, validates it, and executes it against the
published Metric View.

## Metric View contract

A published domain may contain multiple facts, therefore INVENT creates
one Metric View per fact:

```text
invent_semantic_platform
  |
  +-- domain_retail
  |     +-- mv_orders
  |     +-- mv_order_items
  |
  +-- domain_manufacturing
  |     +-- mv_production_runs
  |     +-- mv_maintenance
  |     +-- mv_defects
  |
  +-- domain_healthcare
        +-- mv_encounters
        +-- ...
```

The selected primary fact is registered as the default Analytics source.

All published Metric Views remain governed Unity Catalog objects.

## Data onboarding

Supported file formats:

- CSV
- XLSX
- XLS
- JSON
- Parquet

The ingestion boundary is implemented in `data_engine.py`, so future
database/API/cloud/streaming connectors can be added without rewriting the
semantic engine.

## Security model

- Databricks credentials remain server-side in Streamlit Secrets.
- PII/PHI detection is performed during semantic analysis.
- PII/PHI masking recommendations are shown in Security Center.
- Semantic publishing does not silently grant broad access.
- Optional `READER_PRINCIPAL_ID` can receive schema read permissions.
- AI relationship suggestions require human review.
- Genie Agent failures do not cause the data/semantic publish to be
  falsely reported as failed.

## Demo

Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then:

```text
Data Onboarding
    -> Try a sample domain
    -> Select Manufacturing
    -> Analyze
    -> Semantic Intelligence
    -> Business Model
    -> Publish
    -> Analytics
    -> Ask AI
    -> Genie Agent
```

The sample selector reads directly from `demo_datasets/`; it does not contain
domain-specific semantic logic.

## QA

`qa/run_qa.py` performs local regression checks across every bundled demo
domain, including:

- semantic engine execution
- fact/dimension classification
- relationship detection
- many-to-many false-positive prevention
- Manufacturing shared-dimension topology
- Travel alternate-key regression
- Metric generation
- Python compilation
- Parquet and XML ingestion boundary
- Internal single-document routing

A live Databricks smoke test requires the deployment's real Streamlit
Secrets and is therefore not executed in this source-only build.

## Production deployment

Before enterprise production:

1. Replace PAT authentication with the approved workload identity/OAuth
   method for the target environment.
2. Use a Pro/Serverless SQL Warehouse suitable for Genie.
3. Enable Unity Catalog and partner-powered AI features required by Genie.
4. Grant the publishing identity the required Genie Agent permissions.
5. Enable Agent Mode APIs if the embedded INVENT Genie chat is used.
6. Configure the approved enterprise LLM gateway.
7. Configure domain-specific Genie Agent mappings or enable automatic Agent
   creation.
8. Protect Streamlit access with the organization's approved identity layer.
9. Run the local QA suite and a deployment smoke test against the target
   Databricks workspace.

## Source layout

```text
INVENT/
├── app.py
├── semantic_engine.py
├── ai_engine.py
├── ai_provider.py
├── data_engine.py
├── publish_engine.py
├── security_fabric.py
├── registry.py
├── analytics_engine.py
├── databricks_bootstrap.py
├── assets/
├── pages/
│   ├── 0_Home.py
│   ├── 1_Data_Onboarding.py
│   ├── 2_AI_Analysis.py
│   ├── 3_Semantic_Intelligence.py
│   ├── 4_Business_Model.py
│   ├── 5_Analytics.py
│   ├── 6_Ask_AI.py
│   ├── 7_Security_Center.py
│   └── 8_Genie.py
├── demo_datasets/
└── qa/
```
