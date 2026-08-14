# INVENT v3 Production-Ready QA Result

## Local automated validation

**PASS**

- 10 bundled demo domains passed semantic regression.
- Manufacturing topology regression passed.
- Travel alternate-key regression passed.
- Python compilation passed for all application Python files.
- Connector engine compiles and SQLite connector smoke test passed.

## Genie hardening

- Genie ID validation accepts current 32-character hexadecimal Agent IDs and UUID-form IDs.
- IDs are normalized before API calls.
- Publish no longer reports Genie as connected when only a subset of Metric View registrations succeeded.
- Registry stores `genie_status`.
- Delta/Metric View publication remains independent from optional Genie provisioning failures.

## Live validation boundary

The local suite does not claim that a real Databricks Genie Agent was created or
updated because that requires the target workspace, SQL Warehouse, PAT/identity,
Genie permissions, and feature availability.

After deployment, perform one real smoke test:
1. Publish a new domain.
2. Confirm Delta tables and Metric View.
3. Confirm Genie status is `connected`.
4. Open the domain Genie Agent.
5. Ask a question against the published Metric View.
