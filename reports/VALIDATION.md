# Validation record — 2026-10-19

## Completed locally

- Django system check: passed.
- Backend lint/import checks: passed after formatting.
- Backend suite: **40 passed, 1 skipped** in 37.07 seconds on Windows, Python 3.12, Java 17, Spark 3.5.8.
- The skipped test is complete Spark Parquet output on native Windows without Hadoop native DLLs. It runs in Linux CI; no unknown DLL was downloaded.
- Real Spark expression tests: replacement, literal dollar/backslash values, null preservation, extraction, normalization, unusual column names, multi-partition consistency and deletion by empty replacement.
- Isolated real Spark ingestion tests: quoted/multiline CSV, leading-zero IDs, explicit null marker, Excel worksheet discovery and selected-sheet ingestion.
- API/task tests: dynamic encrypted credential storage, file-list pagination, CSRF and ownership, immediate outbox submission, idempotency, retries, duplicate delivery, cancellation state and stale-worker recovery.
- Parquet page-reader tests: multiple files/row groups, signed cursor validation, owner isolation, empty/expired/not-ready results.
- Frontend TypeScript/production build: passed. Unit tests: **2 passed**.
- Browser inspection: workspace renders, setup state is truthful, guide is reachable and readable.

## CI verification

The repository includes Linux Spark/driver tests, a frontend job and a complete distributed Docker-stack job. See the actual GitHub Actions run and its artifacts for status; this document does not declare a pending run successful.

## Not yet established by local tests

- Real AWS authorization and an unconfigured reviewer-owned bucket.
- Real LLM semantic accuracy, provider access and cost/latency.
- Multi-million-row performance on an explicitly recorded environment.
- Public HTTPS deployment and the required real-service demonstration video.

The CI S3/model fixtures are intentionally synthetic. They validate protocol integration and task processing, not external service authorization or model quality.
