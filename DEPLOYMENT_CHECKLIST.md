# INVENT Deployment Checklist

## 1. Streamlit Secrets

```toml
DATABRICKS_HOST = "https://<workspace>.cloud.databricks.com"
DATABRICKS_TOKEN = "<PAT>"
DATABRICKS_WAREHOUSE_ID = "<pro-or-serverless-warehouse-id>"
DATABRICKS_CATALOG = "invent_semantic_platform"

GENIE_AUTO_CREATE = true

AI_PROVIDER = "capgemini"
CAPGEMINI_LLM_BASE_URL = "https://api.generative.engine.capgemini.com/v2/11m/invoke"
CAPGEMINI_LLM_API_KEY = "<approved-key>"
CAPGEMINI_LLM_MODEL = "openai.gpt-5.1"
CAPGEMINI_AUTH_HEADER = "x-api-key"
```

## 2. Existing Genie Agent mapping

Preferred:

```toml
[GENIE_SPACES]
Retail = "<32-char-lowercase-hex-agent-id>"
Healthcare = "<32-char-lowercase-hex-agent-id>"
Finance = "<32-char-lowercase-hex-agent-id>"
Manufacturing = "<32-char-lowercase-hex-agent-id>"
```

Current Databricks Genie Agent IDs are 32-character lowercase hexadecimal
values.

If the old value looks like:

```text
2s8WeLl8017r1UTIr7gxC9mCS3jDYE6O3H0Z55xl
```

do not use it as the current Agent ID. It is not a current 32-character
lowercase hexadecimal Agent ID.

## 3. Genie permissions

The publishing identity must have permission to edit the existing Genie
Agent when INVENT updates it. The Genie Agent also needs access to the
published Metric View and its underlying Unity Catalog data.

## 4. Genie Agent Mode API

For the embedded `Analyze -> Genie Agent` chat, enable Databricks Agent Mode
APIs in the workspace previews if required by the target workspace.

## 5. Publish test

Use:

Data Onboarding
  -> Try a sample domain
  -> Manufacturing
  -> Analyze
  -> Semantic Intelligence
  -> Business Model
  -> Publish

Expected:

```text
Delta tables published
Governed Metric View(s) published
Genie Agent connected
```

The old message:

```text
Existing Genie Space ID recorded.
Automatic Genie management is disabled...
```

should no longer appear in the final build.

## 6. Verify in Databricks

For the selected domain verify:

```text
invent_semantic_platform
  -> domain_<domain>
      -> Delta tables
      -> mv_<fact>
```

Then open the domain's Genie Agent and verify the Metric View appears in
its configured data sources.

## 7. Ask Genie

Try:

- What are the key KPIs for this domain?
- Show the main KPI by the primary business dimension.
- What changed most significantly?
- Show the top performers.

## 8. Ask AI

Verify:

```text
AI provider: capgemini
```

and that the generated SQL uses the governed Metric View and `MEASURE()`
for Metric View measures.

## 9. Access control

For enterprise production, put the Streamlit application behind the
organization's approved identity-aware access layer. Do not put a
Databricks PAT, Capgemini API key, or other secret in browser-side code.
