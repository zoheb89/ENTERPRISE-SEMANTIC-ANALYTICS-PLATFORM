INVENT LOCAL QA RESULT
========================

Date: 2026-08-14

Bundled demo domains tested:
- Automotive
- Banking
- Energy
- Healthcare
- HR
- Insurance
- Manufacturing
- Retail
- Telecom
- Travel

Results:
- Semantic engine execution: PASS
- Fact/dimension classification: PASS
- Relationship detection: PASS
- Many-to-many false-positive regression: PASS
- Manufacturing shared-dimension regression: PASS
- Manufacturing fact/dimension regression: PASS
- Travel alternate-unique-key regression: PASS
- Metric generation: PASS
- Python compilation: PASS

Manufacturing expected:
FACT: production_runs, maintenance, defects
DIMENSION: products, machines, plants
M:N candidates: 0

Important:
A live Databricks/Genie smoke test requires the deployment's actual
Streamlit Secrets and workspace permissions. Those credentials were not
available in the source-only build environment and were not fabricated.
