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

Latest [application validation on 177f2aa2](https://github.com/mingyanc74/patternforge/actions/runs/39382943621) **completed successfully**: Linux backend **64 passed in 54.63s**, including the native-Windows-skipped Parquet test and production HTTPS probe regression; frontend build/tests and distributed-stack integration also passed.

The [first genuine-model container integration](https://github.com/mingyanc74/patternforge/actions/runs/39382945058) failed at container readiness: the official image inherited a health probe for port 8080 while this service listens on 8089. Its logs confirmed successful model loading, not a passed semantic or task test. The probe was explicitly corrected to 8089 and the merged configuration rechecked.

The [corrected genuine-model integration run on 55f7f3f7](https://github.com/mingyanc74/patternforge/actions/runs/39383504796) was running when this entry was written. It is not labelled successful; model-container/Spark integration remains pending its actual outcome.

The merged production/local-model Compose configuration was checked with Compose v2: secure web overrides and private internal ports passed, and the database/broker environment remained preserved. No cloud containers were started by that configuration check.

## Not yet established by local tests

- Real AWS authorization and an unconfigured reviewer-owned bucket.
- General LLM semantic accuracy beyond the small recorded sample; full genuine-model container workflow status must be checked.
- ARM64 complete-stack runtime and performance on the chosen independent free cloud host.
- Public HTTPS deployment and the required real-service demonstration video.

The CI S3/model fixtures are intentionally synthetic. They validate protocol integration and task processing, not external service authorization or model quality.

The selected deployment is independent cloud hosting with free resources only. No laptop tunnel was launched. A cloud account, available free capacity and DNS hostname are still needed before a public URL can be claimed.

## Current un-deployed revision

- Expanded native genuine-model evaluation: 10/10, including ambiguity refusal, explicit custom formats in English/Chinese and additional positive/negative checks.
- Complete Windows backend regression: 74 passed, 1 skipped in 36.80s; the documented native Parquet dependency is the skip. Frontend build and 5 tests passed.
- Refused rules do not enter the verified-plan cache or execute Spark; task regression covers a non-retryable failure with no result.
- The previously pending model container run 39383504796 later completed with a failed extraction changed-cell assertion. It was not a successful end-to-end run; see MODEL_EVALUATION.md for reproduction and the fix.
- Azure for Students is now activated; no VM or public deployment was created. Read-only price lookup and quote filtering tests passed. Planning uses finite student credits without a payment method, not perpetual free hosting.
- New complete-stack CI is required for the changed revision. Do not infer a pass from local tests or older green runs.
