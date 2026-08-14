# INVENT v4 Final Release

## Primary changes

1. Domain-level Genie configuration.
2. All governed Metric Views are registered in the domain Genie Agent in one update.
3. Primary Fact / Default Analytics is clearly separated from publication scope.
4. Registry persists the complete Metric View list.
5. Genie page displays all governed Metric Views for the selected domain.
6. Genie status is only `connected` after the domain configuration action succeeds.
7. Existing Delta/Metric View publication remains independent from optional Genie failure.
8. Connector-based onboarding, metadata semantic modelling, QA, security, Capgemini Ask AI,
   Analytics, and existing sample domains are retained from v3.

## Migration

Existing domains should be republished once with v4 to reconcile their Genie Agent
configuration. This is especially important for domains created by v3 where Genie
contains only the last registered Metric View.

## QA

Local automated semantic regression: PASS.
Python compilation: PASS (24 files).
Live Databricks Genie API validation requires the target workspace credentials and
permissions and is intentionally not fabricated by local QA.
