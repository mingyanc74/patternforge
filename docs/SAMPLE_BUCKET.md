# Simulated S3 development bucket

**Retained development/demo guide, not final AWS acceptance.** On 2026-10-21 the user reconfirmed genuine AWS as mandatory; subsequent [real-AWS acceptance](REAL_AWS_ACCEPTANCE.md) used two actual buckets, CSV/Excel and 50,000 rows. This page's historical simulated checks are not included in the 88 real-service checks.

Application: [Rulecraft](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/).

At the earlier sample stage, 44 functional checks and 25 HTTPS/session checks passed on the deployment, plus an actual browser submission/result. See [historical evidence](../reports/SAMPLE_ACCEPTANCE.md). The owner's approval to test a sample without an AWS account was not an assessor waiver of the PDF's S3 requirement.

## Browser workflow

Unlock the website if its gate is enabled, then choose Try sample bucket or Use sample bucket in Connections. No AWS keys are required. The simulated connection belongs only to this browser session, defaults to one hour and can be reconnected. Imported datasets have separate 24-hour retention and remain usable after connection expiry. Do not use sensitive personal data.

`clearflow-sample-bucket` with `sample://` is an application-local read-only adapter, not Amazon S3 or a public S3 protocol server. It exposes no storage port, makes no AWS writes and uses no fake AWS keys.

| File | Contents/expectation |
|---|---|
| `examples/customers.csv` | 1,000 rows; leading-zero IDs; Email has 800 addresses, 100 nonmatching values and 100 nulls; Name includes Chinese text, whitespace, commas and newlines |
| `examples/workbook.xlsx` | Customers: 120 rows; Orders: 80; choose the worksheet before preview |
| `examples/large-customers.csv` | 50,000 rows for pagination/longer tasks, not million-row performance evidence |
| `edge-cases/empty.csv` | Intentionally empty; precheck returns `EMPTY_FILE` |
| `edge-cases/duplicate-headers.csv` | Intentionally duplicate names; asynchronous inspection fails with an explanation |
| `edge-cases/unsupported.txt` | Unsupported format; unselectable in the UI |

Start with customers.csv using UTF-8/comma defaults:

1. Replacement: Email, `Find email addresses`, replacement `[REDACTED]`; 1,000 rows, Email `changed_cells=800`.
2. Extraction: Notes, `Extract order IDs beginning with ORD- followed by digits`, new column `OrderID`; 1,000 rows with ORD-prefixed identifiers.
3. Normalization: Name, `Trim spaces, collapse repeated whitespace, then convert to lowercase`; inspect whitespace, English case, Chinese text and newline behavior.
4. Results, refresh recovery, history/reuse, cancellation and errors use the real API, without seeded successful jobs or fabricated progress.

Qwen inference, Celery/Redis, database, distributed Spark and Parquet pagination are actual services. Only the data source is simulated. Allowlisted files are generated into temporary task storage and read by the same Spark pipeline; leases, timeouts, cancellation and cleanup still apply.

## Administration/API

Enable with `SAMPLE_BUCKET_ENABLED=1` in private `.env`; default is disabled. Rebuild/restart relevant containers after changes. No extra cloud service/subscription/payment method is needed, but jobs still consume the existing Azure credit.

`GET /api/bootstrap` returns `sample_bucket_enabled`. With session cookie/CSRF token, send `{}` to `POST /api/s3/sample-connection` for `source_type=sample`. Repeated requests reuse this session's valid sample connection. Existing files/inspect/jobs/results APIs are reused; responses and UI continue labelling the simulated source.

`POST /api/s3/connections` always requires genuine credentials. Sample mode does not rewrite `S3_ENDPOINT_URL` or affect real connections. It accepts no external sample URLs, arbitrary local paths or variable bucket parameters.

## Evidence boundary

This mode can test application behavior, not AWS permission/network/STS expiry or S3A semantics. Real S3 was tested separately through the original connection endpoint. Any video of this mode must say Simulated S3, not real Amazon S3 acceptance.
