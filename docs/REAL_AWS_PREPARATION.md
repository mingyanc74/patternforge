# Real Amazon S3 preparation — historical baseline

**Saved before the actual AWS tests on 2026-10-21, not current progress.** Every "not run", "pending" and "no resources" statement below describes that earlier point. Subsequent [real-AWS acceptance](REAL_AWS_ACCEPTANCE.md) and [raw evidence/limits](../reports/REAL_AWS_ACCEPTANCE.md) supersede it. Retaining this baseline distinguishes plans from operations actually performed later.

Final acceptance requires genuine Amazon S3. Simulated S3/Moto/CI model fixtures are development evidence only; no additional simulated public acceptance phase is required or counted.

## Checks at the baseline, 2026-10-21 Sydney

- Website: [public deployment](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/).
- Revision `049cae7f` included the PostgreSQL nullable-related-row locking compatibility fix. The previous revision could not start tasks; that failure is not omitted.
- [Fixed-revision CI](https://github.com/mingyanc74/patternforge/actions/runs/39580701915): all three jobs passed. Distributed CI still used development fixtures, not AWS.
- 26 external HTTPS/gate/CSRF/session checks passed without submitting transformations or connecting AWS.
- A read-only database check found zero genuine-S3 connection records and zero successful genuine-S3 imports. No credentials were read/output.
- New connections defaulted to one hour; independent snapshots to 24 hours. Configuration was checked, not genuine-AWS expiry behavior.
- S3 endpoint override was empty; genuine input was not redirected to a fixture.
- Twelve resident services ran. Startup/model configuration did not prove an actual-data pipeline.
- In-app browser access was blocked by the client during this baseline. No security restriction was bypassed. External HTTPS passed; browser file selection/submission remained pending.
- The owner confirmed an actual AWS account and would log in personally; plan, credit, bucket, region and authorization were not yet verified.

## Prepared files, not yet uploaded at this point

Paired files were saved to the task's `outputs/aws-real-acceptance/` directory, without real personal records. Excel worksheet: `TestData`; first row contains field names, without title rows/formulas. CSV: UTF-8, comma-separated, `\N` for null, supporting quoted commas/newlines. All 1,000 decoded rows matched between formats.

| File | Bytes | SHA-256 |
|---|---:|---|
| test_data.csv | 130,760 | 1982f7bed81768f67e6c222fd07f178202cdf17aafb6b3cf79fe8ade98867fca |
| test_data.xlsx | 37,719 | 8414f6168ddcb232c514f4e224a8133058dc2111ccdeb54dc1eea957eba672e2 |

These checks proved local preparation only, not upload/import.

| Operation | Columns/instruction | Independent expectation |
|---|---|---|
| Replacement | Email; `Find email addresses`; `[REDACTED]` | 1,000 rows; Email changed_cells=800; invalid addresses/null unchanged |
| Extraction | Notes; `Extract the complete order identifier, including ORD- and the following digits`; new OrderID | 900 non-null, 100 null; ID=000001 gives ORD-100001 |
| Normalization | Name/Status; `Trim leading and trailing spaces, collapse repeated whitespace, then convert to lowercase` | 1,000 changes per column; sample Name `alice chen example` |
| Multi-column replacement | Email/BackupEmail; email replacement | 800/700 changed cells respectively |
| Pagination | Default 100 rows/page | Ten pages without duplicate/missing IDs; input ordering not promised |

## Account and cost boundaries

1. The owner logs into the actual AWS console to verify plan, remaining allowance and expiry. AWS Educate coursework alone is not an account authorized for this application.
2. Prefer an explicitly authorized existing test bucket. Before confirming allowances, do not create buckets, upload or upgrade to Paid plan.
3. If approved, use General purpose, S3 Standard, ACLs disabled, all Block Public Access enabled and default SSE-S3. Select/confirm an actually available region, then keep it fixed.
4. Do not enable static hosting, replication, acceleration, extra logging, custom KMS, NAT or new EC2. Server-side reads need neither public objects nor browser S3 CORS.
5. Website credentials are read-only for specified test buckets. Upload with the owner's separately authorized identity; separate upload and application permissions.
6. Prefer suitable temporary credentials, including Session Token. Creating a dedicated IAM key requires confirmation of identity, least privilege and storage. Never use root keys or expose secrets in chat/Git/screenshots/reports.
7. Storage, requests and Azure-bound transfer may incur usage. Budget alerts are not automatic cost stops; actual account allowances govern, not a promise of permanent zero-cost S3.

References retained from planning: [AWS free-plan FAQ](https://aws.amazon.com/free/free-tier-faqs/), [S3 getting started/cost notes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html), [S3 access control](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-management.html).

Use [the identity-policy template](../deploy/aws-test-readonly-policy.template.json) only after replacing placeholders and obtaining approval. It is not a public bucket policy, and grants no upload/delete/other-bucket access.

## Phase-one execution plan at the baseline

| Item | Then-current status | Required evidence |
|---|---|---|
| Public HTTPS/gate/sessions | API checks passed; manual browser acceptance pending | Secret-free timestamps, response codes, screenshots |
| AWS account/allowance/read-only authorization | Owner reported account; unverified | Plan/allowance conclusion and permission scope, no keys |
| Upload both files to genuine S3 | Not run | Actual region, keys, bytes, ETag/VersionId/checksums |
| Enter real credentials in the webpage | Not run | source_type=amazon_s3, safe connection identifier, actual AWS response |
| Listing and CSV/Excel selection | Not run | Both visible, sheet selection and safe errors |
| Spark import/snapshot | Not run | Successful inspection, SHA-256 and retention expiry |
| Three transformations | Not run | Genuine plans, counts, changed cells and extraction null distribution |
| LLM/Celery/Redis/Spark asynchronous path | Services running; actual data not tested | Persisted states, queue flow, inference, Spark application/executors |
| Status/progress/pagination | Not run against actual data | State sequence, totals, complete IDs and unchanged source |
| Snapshot after connection expiry | Not run | New import 410, retained transform SUCCESS, unchanged dataset expiry |
| Invalid credentials/denial/missing bucket | Not run | Actual request, safe errors, no new snapshot or secret leak |

Prefer natural test-connection expiry. If only that newly created connection's application `expires_at` is advanced for speed, label it **accelerated expiry**, not an hour's observation or natural STS expiry. A 24-hour configured window is not continuous 24-hour observation.

S3 HeadBucket may return indistinguishable 403/404 responses for different causes. Do not require the application to infer information AWS withholds; give actionable safe guidance and refuse import.

## Phase two, planned after phase one

All items below were pending **at this baseline**. Reuse genuine successful imports, never preset success output.

- Run all three operations on both formats; verify Chinese text, leading zeros, nulls, multiline values and unchanged source objects.
- Compare multi-column results/statistics separately by column.
- After allowance/cost approval, upload a larger dataset, initially targeting 100,000 rows, then adjust scope to available resources. Targets are not achievements: record actual rows, bytes, total/stage times. The subsequent actual run used 50,000 rows, as recorded separately.
- During a longer task measure health/history/page responses. A returned job ID alone does not establish nonblocking behavior.
- Cancel only newly created test jobs. Limit failure/retry injection to the test flow; do not shut down production Redis/model services.
- Repeat a valid configuration to verify Redis `cache_hit`; inspect key isolation/availability rather than treating fast inference as a cache hit.
- Connect/import another explicitly authorized real bucket. Without it, leave this criterion uncompleted; generic code alone is not runtime evidence.
- Record PASS/FAIL/NOT RUN, dates, revision, job IDs, scale, timings, expectations and observations. Retain failures and repaired reruns; never invent successful values.
