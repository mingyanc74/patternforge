# Azure deployment acceptance

Recorded on 2026-10-21, Sydney time. This page preserves deployment and earlier sample-adapter history, not an up-to-date claim that AWS resources are missing.

**Subsequent evidence:** application `049cae7f` passed 88 actual-service assertions against two real AWS buckets, CSV/Excel, all three operations, a 50,000-row job and stability cases, plus 26 HTTPS/gate checks and browser interaction. See [real-AWS evidence and boundaries](../reports/REAL_AWS_ACCEPTANCE.md). The [owner-narrated demo](../README.md#demo-video-and-public-url) has since been published. A separate assessor's private-repository access remains unconfirmed; see [final audit](../reports/FINAL_REQUIREMENTS.md).

Public application: [Rulecraft](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/).

This is a real application on an independent Azure host, not a prototype or a laptop-dependent server. It consumes finite student credit, not permanently free hosting. No automatic seven-day shutdown was configured; confirm backups/resource handling after review.

## Deployment checks that passed

| Area | Evidence and limits |
|---|---|
| Host | Australia East, Standard_B4as_v2, 4 vCPU / 16 GiB, Ubuntu 24.04 x64, 64 GiB Standard SSD; both Spark workers share one host, not two physical servers |
| Secure deployment | Independently checked the SSH host public key from Azure boot logs and used strict host verification; SSH limited to one approved source `/32`; only website ports 80/443 public; model/database/queue private |
| Containers | PostgreSQL, Redis, Django, Celery worker, dispatcher, Spark master/two workers, genuine Qwen model, frontend and Caddy running; migration/deployment exit codes 0 |
| External HTTPS | External HTTP client and browser reached trusted HTTPS; `/api/health` ready with all dependency flags true |
| HTTP/session | 25 `scripts/check_cloud_http.py` checks: headers, assets, blocked internal monitoring, secure cookies, isolated sessions, anonymous CSRF, empty-credential rejection and no invented history |
| Genuine model | Checksum-verified official Qwen3-4B Q4_K_M through llama.cpp CPU; 10/10 fixed cases, 5.559–26.473 seconds each; not general-language accuracy |
| Genuine Spark | Synthetic 10,000 rows, 10,000 expected replacements, two executors/eight partitions, 10.9 seconds, Spark 3.5.8; no S3 and not full application end-to-end timing |
| Browser | Public page, empty-field validation, STS input, service help and empty history checked; fixed narrow-window overflow from zero-width flex steps |
| Local regression | 76 passed / 1 skipped; skip was native-Windows Parquet without Hadoop DLLs, not a pass; the existing path was verified in Linux CI |

Non-sensitive local raw reports remain ignored under `reports/local/azure-model-evaluation.json`, `azure-spark-acceptance.json` and `cloud-http.json`. No private keys, environment secrets, account identifiers or contact-bearing Azure screenshots are committed.

Health checks model configuration, not inference quality; the separate semantic run supplements it. Caddy supplies the public HSTS policy flagged by Django deployment checks, verified on external responses; no browser preload registration is claimed.

## Historical sample stage and then-outstanding work

### User-approved simulated-source checks, 2026-10-21

At this earlier stage the user authorized a sample adapter for functional demonstration. Code `7baa1c2` was deployed without replacing the actual S3 endpoint. Try sample bucket required no AWS keys; connection, files, jobs, results and history were labelled simulated.

`scripts/check_sample_e2e.py` passed **44 checks** through external trusted HTTPS in 201.52 seconds for the whole serial suite, not a per-job SLA. CSV replacement/extraction/normalization each processed 1,000 rows, with 800 email changes, 1,000 extracted order IDs and 1,000 normalized names respectively. Excel discovered two sheets and processed Customers with 120 rows/96 email replacements. Each transformation used two executors/eight partitions. Cache hits, full pagination, nulls, leading zeros, asynchronous errors, running cancellation and session isolation passed. A separate browser completed a 1,000-row/800-change job.

An additional 25 HTTPS/session checks passed. Local regression: 84 passed / 1 skipped; five frontend tests passed. [All three Linux CI jobs passed](https://github.com/mingyanc74/patternforge/actions/runs/39562338200). See [sample evidence](../reports/SAMPLE_ACCEPTANCE.md) and [sample guide](SAMPLE_BUCKET.md). No new cloud resources or public internal ports were added; only the user-approved single SSH source was replaced, with strict host verification preserved.

**The sample adapter is read-only synthetic input, not Amazon S3 or a public S3 protocol server.** The model/Celery/Redis/Spark/result pipeline was genuine. User approval of a sample demonstration did not waive the assessment's AWS requirement.

At that historical point there was no authorized AWS bucket, so real CSV/Excel workflows, AWS result/cache/cancel/error/timing evidence, a genuine-S3 video and assessor access were outstanding. Later real-AWS runs and the video supersede those pending statuses; reviewer access still needs confirmation.

CI fixtures, Azure Blob or local files cannot substitute for real S3. No AWS account requiring a payment method was opened automatically; an authorized owner must supply the account/bucket, with secrets entered privately over trusted HTTPS.
