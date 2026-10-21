# API contract

All endpoints are relative to `/api`. Call `GET /bootstrap` first; retain its session cookie and send the returned `csrf_token` as `X-CSRFToken` on state-changing requests. Ownership comes from the verified server session, never a supplied `owner` field.

| Method | Path | Success |
|---|---|---|
| GET | `/bootstrap` | 200: CSRF token, model configuration flag, limits |
| GET | `/health` | 200: dependency flags; `ready` or `setup_required` |
| GET | `/s3/connections` | 200: active session connections, no credentials |
| POST | `/s3/connections` | 201: connection id, bucket, region, expiry |
| POST | `/s3/sample-connection` | 201 (or 200 reused): session-owned simulated bucket, no credentials; empty JSON body; requires SAMPLE_BUCKET_ENABLED=1 |
| DELETE | `/s3/connections/{id}` | 204: disconnected; existing running tasks converge |
| GET | `/s3/connections/{id}/files?prefix=...&cursor=...` | 200: up to 100 objects and `next_cursor` |
| POST | `/files/inspect` | 202: inspection Job and status URL |
| GET | `/jobs` | 200: up to 50 recent session jobs |
| POST | `/jobs` | 202: transformation Job and status URL |
| GET | `/jobs/{id}` | 200: persistent status, config, plan and safe metadata |
| POST | `/jobs/{id}/cancel` | 200: current cancellation/terminal state |
| GET | `/jobs/{id}/results?limit=100&cursor=...` | 200: bounded result page |

Connection request:

Connections and jobs include `source_type=amazon_s3|sample`. Bootstrap includes `sample_bucket_enabled`.
The optional sample route never accepts a bucket, credentials, endpoint or path. It uses synthetic,
immutable files, not Amazon S3. Existing real S3 requests and credentials are unchanged.

```json
{"access_key":"user-supplied","secret_key":"user-supplied","session_token":"optional","bucket":"your-bucket","region":"us-east-1"}
```

Inspection request:

```json
{"connection_id":"uuid","source_key":"folder/customers.csv","delimiter":",","encoding":"UTF-8","sheet":""}
```

Transform request:

```json
{
  "connection_id":"uuid",
  "source_key":"folder/customers.csv",
  "inspection_id":"successful-inspection-uuid",
  "delimiter":",",
  "encoding":"UTF-8",
  "sheet":"",
  "operation":"regex_replace",
  "prompt":"Find all email addresses",
  "target_columns":["Email"],
  "replacement":"REDACTED"
}
```

For extraction set `operation=regex_extract`, exactly one target column and `new_column`. For normalization set `operation=normalize` and describe supported steps. File, worksheet and parsing options must agree with the successful inspection. Schema validation and permissions run independently of the frontend.

Submit an `Idempotency-Key` header (max 128 characters). The same session/key/payload returns the same Job; reuse with different parameters returns 409. A missing replacement is invalid; `"replacement":""` is explicitly allowed.

Successful status responses include `id`, `kind`, `status`, `stage`, `progress`, `progress_kind=stage_estimate`, `attempt`, `cancel_requested`, timestamps, `result_available`, `config`, `plan`, `metadata`, `error`. The preview metadata contains at most 100 rows within a byte budget. Transformation metadata includes exact row count and changed-cell counts; these are not match-occurrence counts.

Page response: `rows`, `columns`, `total_rows`, `offset`, `returned_rows`, `next_cursor`, `version`. A cursor must be treated as opaque. The page may contain fewer rows than requested when its byte limit is reached. Order is stable for that result version.

Error envelope:

```json
{"error":{"code":"SOURCE_CHANGED","message":"The source file changed. Inspect it again before processing."}}
```

Validation may include a `details` object. Typical codes: `S3_CREDENTIALS_INVALID`, `S3_ACCESS_DENIED`, `S3_NOT_FOUND`, `CONNECTION_EXPIRED`, `UNSUPPORTED_FILE`, `EMPTY_FILE`, `COLUMN_NOT_FOUND`, `COLUMN_CONFLICT`, `UNSAFE_REGEX`, `INVALID_JAVA_REGEX`, `LLM_NOT_CONFIGURED`, `JOB_LIMIT`, `IDEMPOTENCY_CONFLICT`, `RESULT_NOT_READY`, `RESULT_EXPIRED`, `INVALID_CURSOR`. Internal stack traces, secret input and raw upstream error bodies are never API error details.
