# Capgemini DataPrepAI — Release Manifest

## Product
Capgemini DataPrepAI — Enterprise Data Preparation, Semantic Analytics & AI Platform

## Included
- Shared server-side Streamlit login via `[DATAPREPAI_AUTH]`
- Capgemini DataPrepAI branding and custom product mark
- Raw data profiling and deterministic preparation
- Data Preparation UI with findings, preview and apply controls
- Existing semantic discovery / relationship / metric / glossary pipeline
- Review-only AI relationship suggestions
- Existing QA and governed publication workflow
- Existing Analytics / Ask AI / Genie workflow
- AI/BI Dashboard recommendation page
- Deployment and secrets documentation
- Targeted preparation-engine test

## Validation
- Python compileall: PASS
- `pytest -q qa/test_dataprepai_enhancements.py`: PASS (1 test)

## Important deployment note
The shared login credential is NOT committed to source. Configure it in Streamlit Secrets:

```toml
[DATAPREPAI_AUTH]
email = "cinvent@capgemini.com"
password = "REPLACE_WITH_NEW_SECRET"
role = "Admin"
name = "DataPrepAI Shared User"
```

The password previously supplied in chat should be rotated before production use.

## Current capability boundary
Raw-data preparation is deterministic and reviewable. It does not claim to infer arbitrary business-specific corrections. AI/BI currently provides metadata-driven KPI/visualization recommendations; full Databricks AI/BI dashboard publishing remains an execution integration step.
