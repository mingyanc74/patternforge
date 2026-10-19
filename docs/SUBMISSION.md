# Assessment submission checklist

This file distinguishes implemented source from externally verified deliverables. It is intentionally not a claim that all external resources already exist.

| Requirement | Evidence to attach |
|---|---|
| GitHub source | Repository URL and commit, access granted to reviewers |
| One-command stack | Clean `docker compose up --build` run, service health, CI link |
| Dynamic real S3 | A previously unconfigured AWS account/bucket, user-entered keys, file list, CSV and Excel runs |
| Genuine LLM | Configured real provider/model; varied phrasings, safe output, cache hit; no deterministic fixture |
| Async lifecycle | HTTP 202, persistent Job states, visible progress, failure/retry, actual running cancellation |
| Distributed Spark | Two active workers/executors, multiple effective partitions, row counts and correctness |
| Result pagination | More than one page, stable result version, no duplicate/missing rows |
| Extra transforms | Field extraction and standardization demonstrated from the frontend |
| Large data | At least a multi-million-row CSV, resources, source bytes, timings, correctness and limitations |
| Public deployment | Verified external HTTPS URL, functioning complete backend/worker stack |
| Demo video | Real S3 connection, async job completing and result pages, embedded in README |

## Recording script

1. Open the public application from a clean browser session.
2. Enter AWS keys with recording paused or sensitive fields masked. Show the resulting bucket connection without revealing the keys.
3. Browse a CSV from that user's bucket, inspect and select the Email column.
4. Enter “Find email addresses”, set `REDACTED`, and submit.
5. Show the immediate task ID, changing stages, responsive interface and final successful result.
6. Navigate at least two result pages. Show changed-cell counts and the validated rule.
7. Briefly demonstrate the Excel sheet selector, field extraction and normalization.
8. Optionally demonstrate cancellation and the private monitor without exposing monitor credentials.
9. Embed the resulting video in README and replace its pending public-URL field with the actual verified address.

## Benchmark record

Record dataset generator command, row/column count, actual bytes, region/network, Spark/Java/Python versions, host CPU/RAM, worker/executor resources, partition count, retries, queue time, LLM time, Spark read/transform/write time and end-to-end time. Check complete row count and expected changed-cell counts, plus deterministic row samples.

The initial backlog's 3-million-row, 10-minute and 2-second response targets are project-defined acceptance targets, not numerical promises from the original PDF. If resources differ, report the environment and actual measurements; do not replace missing measurements with estimates.

## Pending external resources

- Real AWS credentials and a test bucket: supplied privately in the application when available.
- Real LLM key/model: supplied privately through server `.env` when available.
- Docker-capable public host and hostname: not provisioned automatically; no paid account is created by these scripts.
- Actual end-to-end recording: produced after the real-service run.

Source, tests and reproducible fixture integration are useful evidence; they do not erase these remaining assessment requirements.
