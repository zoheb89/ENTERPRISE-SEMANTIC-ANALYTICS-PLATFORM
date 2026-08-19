# Data Preparation Enhancement — DataPrepAI

## What changed

The raw-data quality profiler now detects and classifies:

- Exact duplicate records
- Duplicate records exposed by safe normalization
- Leading/trailing whitespace
- Blank strings and null-heavy columns
- Inconsistent text casing
- Currency-formatted numeric values
- Non-numeric values in numeric candidates
- Invalid date/time values
- Invalid year values
- Inconsistent boolean representations
- Potential PII/PHI columns

## Safe preparation

Only deterministic actions are automatically eligible:

- trim whitespace
- convert blank strings to null
- normalize supported boolean representations
- standardize parseable dates
- standardize parseable numeric/currency text
- remove exact duplicates after deterministic normalization

The engine does NOT:

- invent replacement business values
- silently delete non-duplicate business records
- automatically mask PII/PHI
- automatically repair referential-integrity problems
- silently publish AI-suggested semantic relationships

## Enterprise review model

Security findings are routed to Security Center for human review.

Referential-integrity issues such as invalid foreign keys are intentionally left for Semantic Intelligence / QA rather than being "fixed" by Data Preparation.

## Validation

The deliberately dirty automotive test pack now produces a substantially richer profile (22 findings in the supplied six-table test set), including:
- 14 warnings
- 8 informational findings
- 18 auto-safe findings
- 4 review-required findings

Automated test result:
- `2 passed`
