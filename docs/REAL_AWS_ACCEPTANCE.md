# Real Amazon AWS S3 acceptance guide

On 2026-10-21 (Sydney), the public Azure application passed **88 actual-service checks: 65 end-to-end plus 23 stability checks**, separately from 26 HTTPS/password/session checks. Browser testing also entered actual AWS credentials, connected, selected CSV/Excel, imported, submitted and viewed results.

Application: [Rulecraft / PatternForge](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/), backend acceptance revision `049cae7f`.

On 2026-10-22 the UI became Rulecraft, combining the original light styling with the refresh. The [UI regression](../reports/UI_REFRESH.md) records another successful 1,000-row/800-replacement task using a retained snapshot about nine hours after its original one-hour connection naturally expired. This is not STS expiry or 24-hour observation; the original accelerated-expiry record is unchanged.

Full timings, job IDs, SHA-256, raw JSON, failures and limits are in the [real-AWS evidence report](../reports/REAL_AWS_ACCEPTANCE.md). The [pre-test baseline](REAL_AWS_PREPARATION.md) is historical, not current progress. Simulated S3/Moto/CI model fixtures remain development evidence, excluded from these real-service totals; no independent simulated public acceptance was repeated for final acceptance.

## Try it yourself

1. Open the application and enter the website password provided privately. It is neither an AWS key nor personal account registration.
2. In Connections, enter the authorized Access Key, Secret, bucket and region from your private connection record. The tested IAM key does not require a Session Token.
3. Main bucket: `patternforge-test-20261021-a7f4c2`, region `ap-southeast-2`, with actual `test_data.csv` and `test_data.xlsx` objects. Excel worksheet: `TestData`.
4. Select a file and Preview selected file; wait for successful background import before choosing columns/instructions.
5. Connections default to one hour. Reconnect for new listings/imports; retained Imported datasets remain independently usable within their own 24-hour window.

| Operation | Configuration | Verified expectation |
|---|---|---|
| Find & replace | Email; `Find email addresses`; replacement `[REDACTED]` | 1,000 rows; 800 changed cells |
| Extract a field | Notes; `Extract the complete order identifier, including ORD- and the following digits`; new column OrderID | 900 order IDs; 100 nulls |
| Clean & standardize | Name and Status; `Trim leading and trailing spaces, collapse repeated whitespace, then convert to lowercase` | 1,000 changed cells in each column |
| Multi-column replacement | Email and BackupEmail; same email instruction | 800 and 700 changed cells respectively |

All three operations on both formats were compared row by row, not represented by preset success screens. The first actual plans for the three operation types had `cache_hit=false`; repeated valid plans subsequently demonstrated Redis hits.

## Phase one: performed

- External HTTPS, password gate, sessions and CSRF passed.
- The AWS console showed Free plan, $100 credit, 183 days remaining and expiry 2027-04-21 at the check; no paid upgrade was performed. This is a dated account observation, not a permanent allowance promise.
- Two genuine private S3 buckets: ACLs disabled, all Block Public Access enabled and SSE-S3. The records are fictional, but the files/storage are real.
- Dedicated `patternforge-s3-test` IAM identity without console password, one key pair, limited to List/GetBucketLocation/GetObject/GetObjectVersion for the two buckets. No upload/delete/other-resource permission.
- Actual AWS bytes matched local files and independent imported snapshots by SHA-256. Both formats used genuine Celery/Spark import with separate snapshot expiry.
- Replacement, extraction, normalization, states/progress, full pagination, session isolation and unchanged source objects passed.
- Actual requests safely rejected invalid keys/missing buckets. The browser initially displayed denial for the existing unauthorized second bucket. After separate user approval extended read-only access, the same key connected/imported it successfully.
- Accelerating only a newly created test connection's `expires_at` caused new listing/import to return 410; retained CSV and Excel each completed another transformation without changing dataset expiry.

**The original expiry check was accelerated application expiry**, not waiting an hour or natural STS expiry. The later natural-connection-expiry regression is separate. Neither establishes continuous observation for a complete day.

## Phase two: performed

- Second bucket: `patternforge-control-20261021-a7f4c2`, same region/key, with a copied CSV and `large_test_data.csv`. Connection, listing, import and transformation succeeded.
- Actual large object: **50,000 rows / 4,765,075 bytes**, with 40,000 expected email replacements. Two executors/eight partitions; Spark 13.305 seconds; transformation creation-to-completion 19.431 seconds. Spark time excludes queue/import/model; this large job used a cached plan.
- Read all 100 pages of 500 rows: 50,000 unique IDs, no duplication/omission. During processing, the maximum measured total for a consecutive health/history request pair was 0.125 seconds, not a multi-user load SLA.
- Cancellation after actual `RUNNING` reached `CANCELLED` without publishing partial output. A wrong Excel sheet failed asynchronously with `SHEET_NOT_FOUND` and no usable snapshot.
- Isolated transient-fault test: one operation process injected `S3_TEMPORARY_ERROR` on attempt one; real outbox/dispatcher/Celery retried, downloaded from actual AWS on attempt two, completed Spark and matched the snapshot checksum. No successful response was fabricated and no service was disabled. This was not a naturally occurring AWS outage.
- Dependencies remained ready after failures, cancellation and retry.

## Limits and remaining work

Real-AWS scale in this run stops at 50,000 rows. The existing 3,000,000-row CI benchmark used explicitly synthetic service fixtures and must not be relabelled real-AWS large-data acceptance. Both Spark executors share one Azure machine, not multiple physical hosts.

The [owner-narrated real-AWS video](../README.md#demo-video-and-public-url) has since been published; a separate assessor's private-repository access remains unconfirmed. The [final requirements audit](../reports/FINAL_REQUIREMENTS.md) documents these boundaries rather than declaring unconditional completion.

The AWS key remains valid until disabled; an application's one-hour connection expiry does not disable it. Disable it promptly after review. S3 storage/requests/cross-cloud transfer and the Azure host consume finite allowances. No permanent-free guarantee is made. Keys/passwords stay in restricted local files and authorized server storage, not public Git, screenshots, chat or reports.
