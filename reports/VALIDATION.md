# Validation record — 2026-10-20

## Completed locally

- Django system check: passed.
- Backend lint/import checks: passed after formatting.
- Latest backend suite: **62 passed, 1 skipped** in 40.97 seconds on Windows, Python 3.12, Java 17, Spark 3.5.8. This includes operation-specific model schema/privacy tests and eight independent-cloud preflight tests.
- The skipped test is complete Spark Parquet output on native Windows without Hadoop native DLLs. It runs in Linux CI; no unknown DLL was downloaded.
- Real Spark expression tests: replacement, literal dollar/backslash values, null preservation, extraction, normalization, unusual column names, multi-partition consistency and deletion by empty replacement.
- Isolated real Spark ingestion tests: quoted/multiline CSV, leading-zero IDs, explicit null marker, Excel worksheet discovery and selected-sheet ingestion.
- API/task tests: dynamic encrypted credential storage, file-list pagination, CSRF and ownership, immediate outbox submission, idempotency, retries, duplicate delivery, cancellation state and stale-worker recovery.
- Parquet page-reader tests: multiple files/row groups, signed cursor validation, owner isolation, empty/expired/not-ready results.
- Frontend TypeScript/production build: passed. Unit tests: **5 passed**, also verified in the CI run below.
- Browser inspection: Clearflow live setup state, workspace and history; separately labelled fixture-only job/result/cancel flows; 375px mobile layout. See docs/CLEARFLOW_UI_zh.md.
- Genuine Qwen3 CPU model: **6/6** fixed semantic samples passed, including a Chinese instruction, with real application validation and Java regex validation. See MODEL_EVALUATION.md. Not proof of arbitrary model accuracy or a complete model-enabled deployment.

## CI verification

The [verified run on commit 52758ed0](https://github.com/mingyanc74/patternforge/actions/runs/39366328920) completed successfully: backend **52 passed** in 46.34 seconds, frontend **5 passed** plus production build, and the complete distributed Docker stack passed. That run predates the free-model and cloud-preflight additions. New runs must be checked separately, not inferred from this historical success.

The [3-million-row, 10-column benchmark](BENCHMARK.md) also passed on its recorded commit. Its S3 and model providers were deterministic fixtures; the two Spark executors and remaining application services were real.

A separate manual genuine-model workflow is now provided. It uses real Qwen3 inference and synthetic S3, never real AWS. Its existence alone is not a pass result.

## Not yet established by local tests

- Real AWS authorization and an unconfigured reviewer-owned bucket.
- General LLM semantic accuracy beyond the small recorded sample; full genuine-model container workflow status must be checked.
- ARM64 complete-stack runtime and performance on the chosen independent free cloud host.
- Public HTTPS deployment and the required real-service demonstration video.

The CI S3/model fixtures are intentionally synthetic. They validate protocol integration and task processing, not external service authorization or model quality.

The selected deployment is independent cloud hosting with free resources only. No laptop tunnel was launched. A cloud account, available free capacity and DNS hostname are still needed before a public URL can be claimed.
