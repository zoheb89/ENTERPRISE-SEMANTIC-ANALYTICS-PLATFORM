# INVENT QA Result

## Automated local regression

**Status: PASS**

The bundled demo suite was executed through the metadata-driven semantic
engine and Python compilation checks.

| Domain | Tables | Relationships | Facts | Dimensions | Metrics |
|---|---:|---:|---:|---:|---:|
| Automotive | 6 | 6 | 2 | 4 | 6 |
| Banking | 6 | 5 | 3 | 3 | 6 |
| Energy | 6 | 6 | 2 | 4 | 6 |
| Healthcare | 5 | 4 | 2 | 3 | 7 |
| HR | 6 | 6 | 2 | 4 | 7 |
| Insurance | 6 | 6 | 3 | 3 | 6 |
| Manufacturing | 6 | 6 | 3 | 3 | 11 |
| Retail | 6 | 5 | 3 | 3 | 8 |
| Telecom | 6 | 7 | 3 | 3 | 8 |
| Travel | 6 | 4 | 3 | 3 | 6 |

Additional regressions:

- Manufacturing shared-dimension topology: PASS
- Travel alternate-key relationship: PASS
- Python compilation: PASS (23 files)

## Runtime QA

The application now runs `qa_engine.run_qa()` after semantic analysis and
before every publication attempt. Blocking failures disable Publish.

The QA page is available as **QA & Validation** in the INVENT navigation.

A live Databricks smoke test is intentionally not represented as passed
without the target workspace credentials and permissions.
