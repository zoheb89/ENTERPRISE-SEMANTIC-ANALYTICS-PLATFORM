# DataPrepAI — AI/BI Dashboard Phase 2

## Production execution layer

Phase 2 turns the existing metadata-driven dashboard planner into a live governed dashboard.

### Flow

Published semantic model
→ canonical `mv_domain`
→ AI dashboard blueprint
→ user review
→ query canonical Metric View
→ live KPI cards
→ interactive bar/line charts
→ governed filters
→ narrative insights

### Governance rule

Dashboard values are queried from the published canonical Metric View. The dashboard does not calculate its KPIs from raw uploaded files.

Databricks Metric Views are queried using the `MEASURE()` aggregate function as required by Databricks Metric View query semantics.

### Implemented

- Live KPI execution
- Measure × dimension chart execution
- Bar and line visualizations
- Governed dimension filters
- Queryable Metric View readiness check
- Governed narrative insight
- Empty-result handling
- Databricks execution error handling
- Dashboard lifecycle status
- Unit test coverage for recommendation/narrative layer

### Databricks AI/BI publication

The app now provides the execution layer needed before publication. Publishing a native Databricks AI/BI dashboard is a separate API lifecycle step using the Databricks Lakeview dashboard APIs and requires the appropriate dashboard/data/warehouse permissions.

The Databricks documentation confirms that Metric Views are directly consumable by AI/BI dashboards and that dashboard objects can be created, managed, and published through the Lakeview APIs.
