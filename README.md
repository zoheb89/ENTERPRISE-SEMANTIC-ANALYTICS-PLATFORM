# C INVENT — Final Production Product

C INVENT is a Streamlit production application for governed semantic analytics on Databricks Free Edition.

## Final publish contract

For every domain publish:

1. All detected fact tables are written as real Delta tables.
2. All detected dimension tables are written as real Delta tables.
3. Exactly **one canonical Unity Catalog Metric View** is created: `catalog.schema.mv_domain`.
4. The canonical Metric View exposes measures from **every detected fact**, not only the selected primary fact.
5. Legacy per-fact `mv_<fact>` Metric Views created by older INVENT builds are removed from that domain schema; Delta tables are never removed by this cleanup.
6. One deterministic domain Genie Agent is reused/recovered instead of creating duplicates.
7. Genie receives the single canonical Metric View as its governed source.
8. A Genie UpdateSpace HTTP 409 is retried without a stale etag so an edited Agent can be updated safely.

## Travel acceptance case

The checked-in travel sample is detected as:

- Facts: `booking_services.csv`, `bookings.csv`, `payments.csv`
- Dimensions: `customers.csv`, `airports.csv`, `flights.csv`
- Relationships: booking_services → bookings; payments → bookings; bookings → customers; bookings → flights

The final publisher turns those three facts into one `mv_domain` Metric View with fact-specific measures and conformed dimensions. This avoids the v5 defect where the UI reported three facts but the Metric View YAML was generated only from the selected primary fact.

## Real Databricks discovery

`discovery_engine.py` uses the Unity Catalog Tables REST API and SQL Information Schema. Metric Views are discovered from Databricks metadata rather than from the C INVENT registry. The Databricks Tables API exposes `METRIC_VIEW` as an object type.

## Authentication

For Databricks Free Edition, use a workspace PAT:

```text
DATABRICKS_HOST
DATABRICKS_TOKEN
DATABRICKS_WAREHOUSE_ID
DATABRICKS_CATALOG
GENIE_AUTO_CREATE = true
```

Do **not** put a stale `GENIE_SPACE_ID` back into Secrets. With `GENIE_AUTO_CREATE=true`, C INVENT finds an existing `INVENT — <domain>` Agent first and creates one only when necessary.

## File formats

CSV, XLSX, XLS, JSON, Parquet and XML are enabled. Parquet uses `pyarrow`; XML uses pandas' ElementTree parser.

## UI

The product uses the C INVENT visual system with a single stable navigation surface:

Home → Data Onboarding → AI Analysis → Semantic Intelligence → Business Model → QA → Analytics → Ask AI → Genie Agent, plus Govern → Databricks Discovery / Security / Connectors / Audit.

F5/browser refresh is detected and routes to Home; normal Streamlit reruns caused by button presses retain the current page. A fresh application session also starts at Home.
