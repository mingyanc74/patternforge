# Public sample-bucket acceptance

Date: 2026-10-21. Tested application code: `7baa1c2`.

URL: https://clearflow-patternforge.australiaeast.cloudapp.azure.com/

Source: **synthetic read-only sample adapter, NOT Amazon S3**. Real Qwen model, Django/PostgreSQL, Celery/Redis, Spark master plus two workers, and immutable Parquet pagination remain in use. Both executors share the same Azure VM; this is not a multi-host cluster claim.

## Actual external run

`scripts/check_sample_e2e.py --base-url <public URL>`: **44 checks passed**, 201.52 seconds for the entire sequence. Aggregate report is in ignored `reports/local/sample-e2e.json`; no cookies, AWS keys or source rows are in the report.

| Transform | Rows | Verified changes | Spark executors / partitions | Spark seconds |
|---|---:|---|---|---:|
| CSV email replacement | 1,000 | Email: 800 cells | 2 / 8 | 11.54 |
| CSV order ID extraction | 1,000 | OrderID: 1,000 cells; exact values checked | 2 / 8 | 11.35 |
| CSV normalization | 1,000 | Name: 1,000 cells; Chinese/newlines checked | 2 / 8 | 11.32 |
| Repeated replacement | 1,000 | Email: 800 cells; cached plan confirmed | 2 / 8 | 11.11 |
| Excel Customers replacement | 120 | Email: 96 cells | 2 / 8 | 10.96 |

Times are the driver-reported Spark phase, not total user-facing latency or an SLA. Initial uncached CSV transformations had `cache_hit=false`; repeated replacement had `true`.

Also verified: explicit sample provenance, no credentials, CSRF enforcement, connection reuse, six documented objects, prefix listing, cross-session isolation, missing/empty/unsupported source errors, asynchronous duplicate-header failure, 100-row preview, leading zeros, CSV quoting/multiline cells, null preservation, ten result pages containing 1,000 unique IDs, two Excel worksheets and explicit selection, cancellation of a RUNNING large-file inspection with no result, persistent history and unchanged source preview.

An independent browser session clicked the live sample connection, filtered examples, inspected customers.csv, configured Email replacement, reviewed/submitted, and viewed an actual completed 1,000-row / 800-cell result. This is a real persisted job, not preloaded history.

## Other checks

- `scripts/check_cloud_http.py`: 25 public HTTPS/session checks passed after deployment.
- Windows backend regression: 84 passed, 1 skipped (native Hadoop Parquet DLL unavailable); exit code 0.
- Frontend: 5 tests passed and TypeScript/Vite production build passed.
- [Linux CI on tested code](https://github.com/mingyanc74/patternforge/actions/runs/39562338200): frontend, unit-and-spark, distributed-stack all successful. The separate CI stack still uses synthetic S3 and deterministic model fixtures, not the genuine cloud model.

## Remaining limits

The sample catalog includes 50,000 rows for optional larger tests; this run cancels its inspection and does not claim completed large-file throughput. Historical million-row CI benchmarks are separate evidence. The public sample adapter does not test AWS identity, S3 permissions, STS expiry or external S3 network access. The real AWS API path remains available, but real AWS acceptance and the final demonstration video remain pending. Teacher approval of a reduced requirement has not been established. Azure student credit is finite; no new paid resources or subscriptions were created for this feature.
