# Original PDF final requirements audit

Checked 2026-10-22 against both pages of **Technical Assessment — Distributed NL-to-Regex Data Processing Platform**. This is an evidence matrix, not a guarantee of the assessor's grading. The PDF is the assessment source, not a source of authority to disclose credentials or provision paid resources.

## Evidence classes

- **Real-service:** [88 AWS checks](REAL_AWS_ACCEPTANCE.md), real AWS bytes and hashes, actual local Qwen3 inference, public Azure deployment, Celery/Redis/PostgreSQL and isolated distributed Spark.
- **Development:** [automated tests](VALIDATION.md), deterministic S3/LLM protocol fixtures, and [three-million-row benchmark](BENCHMARK.md). These remain valuable, but are not genuine AWS acceptance conclusions.
- **New final recording:** [README demo](../README.md#demo-video-and-public-url), three newly submitted real-AWS tasks and [safe database metadata](DEMO_REAL_JOBS.json). The silent video is ready for the owner's voiceover.

## Requirement-by-requirement

| PDF requirement | Result | Evidence / boundary |
|---|---|---|
| Django + React, clear API/task/data separation | Implemented and exercised | README architecture, `backend/core/views.py`, `tasks.py`, `services/`, React frontend |
| User enters own Access/Secret, bucket, region; list/select files | Real-service passed | Real AWS report; video 00:11–00:38 (key entry paused); no predefined bucket dependency |
| CSV and Excel into PySpark DataFrame | Real-service passed | Both actual AWS objects, SHA-256 matches, immutable imports; video CSV and Excel |
| Other authorized buckets, not fixed samples | Real-service passed | Second explicitly authorized private control bucket, same least-privilege key; no write permission needed |
| Credentials encrypted, not logged/plaintext/API returned | Implemented; bounded checks passed | Fernet server storage, no key in task args/model prompt, API/security tests, final local Git scan. Operator's private input file is outside repository, ACL-restricted. No claim of exhaustive penetration testing |
| Clear invalid credential / unreadable bucket errors | Real-service passed within tested cases | Actual invalid-key/nonexistent-bucket/existing unauthorized-bucket checks in real report; generic access errors avoid leaking AWS detail |
| Durable QUEUED/RUNNING/SUCCESS/FAILED, progress | Passed | PostgreSQL jobs, outbox + lease design, actual browser progress; stage-based estimate |
| Immediate job ID, status polling/results API | Passed | HTTP 202 acceptance and API contract, actual recorded tasks |
| Heavy parsing/model/transforms in Celery | Passed | Real Celery process orchestrates isolated Spark child, not HTTP process |
| Redis broker + result backend + prompt cache | Passed | Separate Redis databases, real repeated prompt cache checks; all three new video tasks were cache misses |
| Failure, retry, cancellation | Passed with controlled-test boundary | Real running task cancelled; invalid worksheet failed; one isolated injected first-attempt transient fault recovered. Not a naturally observed AWS outage |
| Spark partition transforms, not Python per-row processing | Passed | Spark expressions, two executors, eight partitions in actual jobs; single Azure host, not multi-host infrastructure |
| Millions of rows, correct/performance | **Split evidence / real-AWS million-row run not performed** | Actual distributed 3,000,000-row benchmark uses S3+LLM fixtures. Actual AWS 50,000-row test has full checked results. Do not combine these into a real-AWS million-row claim |
| Paged results, no all-row response | Passed | Signed cursors, bounded PyArrow reads, all-page correctness checks; video switches page 1→2 |
| README partition/parallelism rationale | Complete | Multiline CSV parse trade-off, explicit repartitioning, two cores/eight partitions and shared-volume limits documented |
| React target columns, instruction, replacement, progress/errors | Passed | Actual browser CSV replacement, Excel extraction and two-column standardization; existing UI tests retained |
| LLM varied phrasings + regex safety + cache | Bounded real tests passed | Genuine Qwen3 cases plus uncached final video jobs; structured/schema + regex validation; accuracy beyond tested cases not guaranteed |
| Two additional model-assisted async/Spark transformations | Real-service passed | Extraction and normalization in both prior real-AWS format matrix; newly recorded Excel tasks |
| One-command Docker Compose full stack | Verified development/container evidence; live stack deployed | Source Compose + real CI startup. Genuine model overlay requires initial pinned model download; full ARM acceptance remains pending |
| Observability / metrics / worker monitoring | Implemented | Persistent metrics, private Flower, health endpoint; monitoring intentionally not exposed publicly |
| Task and Spark tests | Retained, CI passed | 82 backend / 5 frontend at recorded CI, real Java/Spark tests; Windows native Parquet limitation documented |
| Complete GitHub source | Pushed; private | Owner `mingyanc74` has access; **actual teacher's separate account still unconfirmed** |
| README setup/run/architecture/trade-offs | Updated | README + architecture/API/security/deployment guides + dated evidence |
| Public complete app, reviewer own S3 | Live verified | [Azure HTTPS app](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/), [28 final HTTP/gate checks](FINAL_HTTP.json). Shared access password supplied privately; finite student credits |
| Short video real S3 + completed async task, embedded README | Silent demonstration recorded | 1280×720 H.264, 05:18; actual CSV/Excel and three completed jobs. Keys/password entered off-screen and pause disclosed. Owner voiceover optional, provided separate script |

## Retention and security follow-ups

The app's one-hour S3 connection/24-hour snapshot design is a project feature. Earlier expiry was accelerated for one test connection. A separate new UI task succeeded after its original connection's natural one-hour expiry. No continuous full 24-hour observation or AWS STS-expiration run is claimed.

[Final secret audit](FINAL_SECRET_AUDIT.json) checks exact known AWS key/secret and website password locally, all reachable Git blobs after fetching remote refs, and bounded token/private-key patterns. It prints locations only, not values. Re-run after final media/docs changes. This is not proof against all possible credentials or all threats.

The prior UI dependency audit reported no production dependency advisory at that time, but known development-only Vitest/tinypool advisories remain in the recorded toolchain. Nginx serves built assets without a Vitest server. They must not be described as fixed by this delivery/documentation work; see [UI refresh report](UI_REFRESH.md).

No additional cloud resource, permission expansion, paid upgrade or large S3 upload was performed for final recording. The existing read-only key and original two test objects were reused. Recording does not reset their server snapshots' TTLs or make hosting permanently free.
