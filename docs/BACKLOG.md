# Natural-language S3 data processing: user stories and acceptance criteria

Version: v1.0  
Design date: 2026-10-19  
Purpose: product backlog, implementation breakdown, test design and final acceptance.

This document translates the assessment and the agreed architecture into actionable stories and test conditions. It is a **design baseline, not a record of implemented or measured functionality**. The original assessment remains the requirements source.

English edition: 2026-10-22. All original story and AC identifiers are retained. Historical proposals, including the 24-hour credential lifetime and benchmark hardware, have not been silently rewritten as current behavior. The implementation now uses one-hour S3 connections and independent 24-hour imported snapshots; see [access and retention](DATASETS_AND_ACCESS.md). Two tested buckets in one AWS account do not establish the two-account criterion below. Use the [final requirements audit](../reports/FINAL_REQUIREMENTS.md), [real-AWS report](../reports/REAL_AWS_ACCEPTANCE.md) and [submission checklist](SUBMISSION.md) for actual evidence and outstanding limitations. This translation does not mark any additional criterion as passed.

## 1. Scope, roles and labels

### 1.1 Roles

- **Data-processing user:** connect an authorized S3 bucket, select files, configure transformations, track jobs and view results.
- **Operator:** deploy the system, inspect tasks/resources and investigate failures.
- **Developer/reviewer:** run the code, inspect the architecture, execute tests and reproduce performance results.

An anonymous session may establish ownership; registration is not mandatory. Public deployment must isolate credentials, tasks and results between sessions. Full account management, organizations, billing and team collaboration are out of scope.

### 1.2 Delivery labels

| Label | Meaning |
|---|---|
| Required | Explicit assessment requirement; necessary for final delivery |
| Architecture requirement | Additional implementation constraint for reliability, security or testability, not a verbatim assessment requirement |
| Optional | Product enhancement, not required by the original assessment |

US-01 through US-27 form this design's delivery scope; US-28 is optional. Completing the main path does not remove Excel, two additional LLM transformations, performance validation or public deployment from scope.

### 1.3 Shared business conventions

1. **Operations:** `regex_replace`, `regex_extract` and `normalize`. The latter two are the selected additional LLM transformations.
2. **Input authority:** structured user selections determine the file, target columns and replacement. Natural language describes a pattern or rule. The UI displays the final configuration; the LLM cannot change these selections.
3. **Source preservation:** never overwrite the user's S3 object; write output to platform-managed storage.
4. **Matching:** replace all non-overlapping matches within a cell. Treat replacement text literally. An explicit empty string deletes matches; distinguish it from an omitted field.
5. **Nulls:** preserve nulls and nonmatching text. Version one rejects generated patterns capable of zero-length matches with an actionable error.
6. **Results:** replacement and normalization preserve row count. Extraction adds a new column and retains the source. Pagination order is stable within a result version, not necessarily identical to CSV input order.
7. **LLM boundary:** accept constrained JSON plans and execute allowlisted operations, never arbitrary generated code. Do not send private source rows to the model by default.

### 1.4 Proposed version-one quantitative thresholds

The assessment requires asynchronous processing, millions of rows and pagination, but does not prescribe these numbers. They are initial project-defined targets, to be recorded alongside the README and test environment, not quotations from the assessment.

| Item | Initial proposal |
|---|---|
| Preview | At most 100 rows |
| Result page | 100 rows by default, maximum 500 |
| Submission | HTTP 202; P95 at most 2 seconds in the benchmark environment |
| Progress | Poll every 2 seconds; stage changes visible within 5 seconds on a normal network |
| Automatic attempts | At most 3 for transient failures, including the first attempt |
| Regex length | Configurable maximum of 2,048 characters |
| Credentials | Default 24 hours, with early disconnect; refuse new jobs after expiry |
| Plan cache | Default 24 hours, isolated by user/session |
| Results | Default 24 hours, with an explicit expiry error |
| Running cancellation | Stop actual computation within 60 seconds when the cluster is reachable |
| Large-data acceptance | At least 3,000,000 CSV rows; hardware/timing targets in US-25 |

## 2. Story map

| Epic | Stories | Label |
|---|---|---|
| E1: S3 and file preparation | US-01 connect; US-02 browse; US-03 parse CSV/Excel; US-04 preview/select columns | Required |
| E2: LLM and transformations | US-05 plan; US-06 regex safety; US-07 cache; US-08 replace; US-09 extract; US-10 normalize | Required |
| E3: Asynchronous jobs | US-11 submit; US-12 progress/recovery; US-13 failure/retry; US-14 cancel | Required, with reliability additions |
| E4: Distributed processing | US-15 S3 to Spark; US-16 distributed execution; US-17 persistent results | Required / architecture requirement |
| E5: Results and UI | US-18 pagination; US-19 end-to-end interaction | Required |
| E6: Security | US-20 credential protection; US-21 session isolation | Required / architecture requirement |
| E7: Operations and delivery | US-22 startup; US-23 monitoring; US-24 tests; US-25 performance; US-26 public deployment; US-27 repository/documentation/video | Required |
| E8: Enhancement | US-28 result download | Optional |

## 3. Detailed stories and acceptance criteria

ACs use Given/When/Then semantics. Their identifiers can be used as test or issue references. Architecture criteria require tests, runtime evidence or code review; a convincing screen alone does not prove them.

### E1: S3 and file preparation

#### US-01: Connect the user's own S3 bucket

**Story:** As a data-processing user, I want to enter my AWS credentials and bucket name so that I can process data I am authorized to access.

**Label/dependencies:** Required; protection from US-20 and US-21.

- **AC-01.1:** Given valid Access Key, Secret Key and authorized bucket, connecting returns a secret-free `connection_id` and the UI confirms success.
- **AC-01.2:** Given unconfigured buckets from two different test accounts, each connects using its own entered credentials; no fixed demo account or file is required.
- **AC-01.3:** Missing required fields produce field-specific frontend feedback and independently recognizable backend validation errors; no valid connection is created.
- **AC-01.4:** Invalid credentials, insufficient permission, missing bucket, region mismatch and network timeout produce appropriate safe codes/messages. If upstream cannot distinguish absence from denial, explain both possibilities rather than inventing a diagnosis.
- **AC-01.5:** Mask the Secret Key by default; show loading and prevent duplicate submission; allow editing and retry after failure.
- **AC-01.6:** Bound connection timeouts. Changing a bucket or reconnecting clears old selections and schema to prevent cross-connection mistakes.

#### US-02: Browse and select S3 files

**Story:** As a data-processing user, I want to browse available bucket files so that I can select the correct input.

**Label/dependencies:** Required; US-01.

- **AC-02.1:** A valid connection lists full object keys, sizes and modification times, with prefix-based directory browsing.
- **AC-02.2:** Support subsequent pages when the list exceeds one page. Use S3 pagination rather than reading the entire bucket for its first page.
- **AC-02.3:** Support `.csv` and `.xlsx` in version one; mark other extensions unsupported/unselectable. Do not promise legacy `.xls` by default; UI and README must agree.
- **AC-02.4:** Distinguish an empty bucket/prefix from expired permissions and listing failures; access failure is not an empty list.
- **AC-02.5:** Retain the full selected key and version or fingerprint. If deleted/changed before submission, require reinspection rather than silently processing another version.

#### US-03: Parse CSV and Excel asynchronously

**Story:** As a data-processing user, I want the system to identify file structure so that I can verify usability and configure a transformation.

**Label/dependencies:** Required; US-02, US-11, US-15.

- **AC-03.1:** Inspection returns a task ID immediately; downloading, parsing and schema inference run in the Celery/Spark pipeline.
- **AC-03.2:** Read valid CSV headers, quoted delimiters and embedded newlines. Default to UTF-8, commas and a header row; expose explicitly supported alternatives.
- **AC-03.3:** Discover `.xlsx` worksheets. A single usable sheet may be selected by default; multiple sheets require a user choice, followed by asynchronous schema/preview loading.
- **AC-03.4:** Default CSV values to strings so `00123` remains unchanged. Document other type policies in the preview/docs; retain non-target columns according to the parsed schema.
- **AC-03.5:** Report corrupt/encrypted files, unsupported encodings, published-limit violations and unparseable rows explicitly. Parse strictly by default; never silently discard bad rows.
- **AC-03.6:** Give explicit outcomes for empty files, header-only files and empty sheets. Reject duplicate/empty column names, or apply traceable renaming only after explicit user confirmation.
- **AC-03.7:** Both CSV and Excel paths produce PySpark DataFrames; browser-only parsing or complete pandas processing must not masquerade as Spark execution.

#### US-04: Preview data and select target columns

**Story:** As a data-processing user, I want bounded samples and column information so that I can select targets without accidental changes.

**Label/dependencies:** Required; US-03.

- **AC-04.1:** Successful inspection shows names, parsed types and at most 100 preview rows, clearly identified as a sample.
- **AC-04.2:** Allow one or more eligible text columns; frontend and backend reject transformations without targets.
- **AC-04.3:** Do not implicitly apply text replacement to numbers/dates. Any supported string cast requires explicit selection and an explained output type.
- **AC-04.4:** Correctly select/quote names containing spaces, Chinese characters, dots or backticks; never interpret a column name as an unintended expression.
- **AC-04.5:** Safely display nulls, empty strings, long text and HTML-like content. Display truncation must not change stored values.
- **AC-04.6:** Changing file, sheet or parsing options clears obsolete preview/targets and requires renewed confirmation.

### E2: LLM and transformations

#### US-05: Turn natural language into a structured plan

**Story:** As a data-processing user, I want to describe rules in natural language so that I do not have to write regex myself.

**Label/dependencies:** Required; US-06, US-07, US-11.

- **AC-05.1:** For a supported request such as "Find email addresses", the LLM returns a predefined-schema JSON plan containing the operation, pattern or allowed steps, required parameters and explanation.
- **AC-05.2:** Equivalent phrasings for fixed email, order-ID and whitespace test sets pass the same positive/negative cases; regex strings need not be identical.
- **AC-05.3:** Invoke the LLM only in Celery workers, once for a column-level rule rather than once per row.
- **AC-05.4:** Clearly reject empty, excessive, ambiguous or unsupported requests; do not replace a whole column using an unjustified broad pattern.
- **AC-05.5:** Never execute responses with invalid schema, arbitrary code or unknown operations. Permit only bounded repair attempts, then report an understandable failure.
- **AC-05.6:** Job details show the validated rule/explanation. The model cannot change the selected file, columns, replacement or result owner.

#### US-06: Reject invalid or dangerous regex

**Story:** As a data-processing user, I want rules checked before execution so that invalid or high-risk patterns cannot cause uncontrolled processing.

**Label/dependencies:** Required; US-05; applies to US-08 and US-09.

- **AC-06.1:** Compile/validate using semantics compatible with actual Spark execution. Python `re` validation alone is insufficient.
- **AC-06.2:** Reject invalid, over-2,048-character and zero-length-matching patterns before production transformation, with recognizable errors.
- **AC-06.3:** Publish a supported subset. Restrict nested quantifiers, backreferences and other risky constructs; reject agreed examples such as `(a+)+$`.
- **AC-06.4:** Test positive, negative and adversarial long inputs in an isolated, time/resource-bounded validator. Timeout must not hang web or ordinary Celery control tasks.
- **AC-06.5:** Bound actual Spark execution time/resources and provide a stop mechanism. Neither a blacklist nor small tests prove freedom from backtracking risk.
- **AC-06.6:** Failed validation publishes no result/success and writes no validated plan to Redis.
- **AC-06.7:** Never execute generated code, system commands, arbitrary function calls or requests to access credentials.

#### US-07: Reuse validated LLM plans

**Story:** As a platform user, I want repeated requests to reuse rules so that I wait less and avoid duplicate model calls.

**Label/dependencies:** Required; US-05, US-06.

- **AC-07.1:** The first valid request in a session calls the model; identical requests within TTL reuse the validated plan without another model call.
- **AC-07.2:** Include operation, instruction, model configuration version, prompt-template version, validator version and relevant column/format context in cache keys; changed context must not collide.
- **AC-07.3:** Normalize instructions only in semantics-preserving ways; unconditional lowercasing must not destroy case-sensitive intent.
- **AC-07.4:** Never treat expired/failed plans as successful. Use bounded deduplication/locking for concurrent identical requests, with recovery from abandoned locks.
- **AC-07.5:** Cache neither AWS credentials nor raw rows. Isolate by user/session and prevent inference of another session's private requests.
- **AC-07.6:** Expose hit/miss evidence. Document regeneration or explicit failure when cache storage is unavailable; broker disruption on the same Redis follows US-11 recovery.

#### US-08: Replace matching text in selected columns

**Story:** As a data-processing user, I want matching text replaced with my chosen literal so that I can redact or clean data.

**Label/dependencies:** Required; US-04 through US-07, US-16.

- **AC-08.1:** For the assessment's three-row email example, targeting Email with `REDACTED` makes all three emails `REDACTED` and leaves ID/Name unchanged.
- **AC-08.2:** Replace every non-overlapping match in a cell, retaining nonmatching text.
- **AC-08.3:** Apply the same validated rule to all selected columns; preserve unselected columns and row count.
- **AC-08.4:** Preserve null/nonmatching text; empty strings follow the zero-length-pattern restriction.
- **AC-08.5:** Treat `$`, backslashes, Chinese characters and quotes in replacements literally, not as capture references or executable expressions.
- **AC-08.6:** An explicitly empty replacement deletes matching text; an omitted replacement field fails validation.
- **AC-08.7:** Zero matches may succeed with "0 changed cells"; do not misreport an error or zero source rows.
- **AC-08.8:** Return total rows and changed-cell counts by column, with a documented definition; changed cells are not match occurrences.

#### US-09: Additional transformation one — extract fields

**Story:** As a data-processing user, I want to extract identifiers into a new column so that I can analyze them further.

**Label/dependencies:** Required, selected additional LLM transformation; US-04 through US-07, US-16.

- **AC-09.1:** For `Order ORD-123 shipped`, requesting extraction of the complete ORD-prefixed order identifier into `order_id` produces `ORD-123`, using an LLM-generated, validated pattern.
- **AC-09.2:** Version one extracts the first match; both no-match and null input produce null, without misleading empty-value type differences. Explain multiple-match behavior in the UI.
- **AC-09.3:** Preserve source/other columns and row count. Reject a new-column name that conflicts with existing columns.
- **AC-09.4:** Reuse replacement's asynchronous submission, cache, regex validation, Spark, progress and paginated-result pipeline.
- **AC-09.5:** Deterministically test positive, negative, multiple-match, no-match, null and Chinese-context cases. Hard-coded sample answers cannot replace model rule generation.

#### US-10: Additional transformation two — normalize text

**Story:** As a data-processing user, I want natural-language format standardization so that values become comparable.

**Label/dependencies:** Required, selected additional LLM transformation; US-04, US-05, US-07, US-16.

- **AC-10.1:** Allow trim, collapse whitespace, lowercase and uppercase, combined in an explicit order.
- **AC-10.2:** Asking to trim, collapse spaces and lowercase generates a constrained model plan; `  ALICE   SMITH  ` becomes `alice smith`.
- **AC-10.3:** Execute steps deterministically; idempotent steps remain unchanged on repetition. Preserve nulls, unselected columns and row count.
- **AC-10.4:** Explicitly reject unsupported semantic rewriting, address completion or external lookups rather than silently substituting an operation.
- **AC-10.5:** Map steps to approved Spark operations; no per-row model calls or arbitrary generated code.
- **AC-10.6:** Use the complete asynchronous pipeline, plan cache and explanation. Non-regex steps need not pass regex validation but must pass plan-schema/allowlist checks.

### E3: Asynchronous jobs

#### US-11: Receive a job ID immediately

**Story:** As a data-processing user, I want an immediate identifier so that I can continue using the interface during processing.

**Label/dependencies:** Required, with reliable-dispatch architecture additions; persistent database, Celery and Redis.

- **AC-11.1:** A valid request persists a `QUEUED` Job and returns HTTP 202, a unique `job_id` and status URL.
- **AC-11.2:** At least 100 submissions at concurrency four in US-25's environment achieve P95 at most two seconds, without waiting for model, parsing or Spark completion.
- **AC-11.3:** The API performs bounded validation, ownership checks and persistence/dispatch only; no heavy data work.
- **AC-11.4:** Missing operation, targets or required parameters, and unauthorized/expired connection references, return stable 4xx errors without runnable jobs.
- **AC-11.5:** Identical session/idempotency-key/request submissions return the same Job; the same key with different parameters returns a conflict.
- **AC-11.6:** Recover reliably between database commit and broker dispatch. Broker failure or process crash after submission must not permanently lose or strand an acknowledged 202 Job.
- **AC-11.7:** Celery messages contain only necessary IDs/references, not plaintext credentials, whole files or executable model code.

#### US-12: Track progress and recover after refresh

**Story:** As a data-processing user, I want durable status and refresh recovery so that I know whether to wait or intervene.

**Label/dependencies:** Required; US-11, US-21.

- **AC-12.1:** Support at least `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, plus this design's `CANCELLED`; persist state, stage, progress and key timestamps.
- **AC-12.2:** Show queueing, plan generation, validation, reading, transformation and writing stages. Label stage-based progress as estimated, not a precise row percentage.
- **AC-12.3:** Poll every two seconds by default, show changes within five seconds on a normal network and stop continuous polling at terminal states.
- **AC-12.4:** Reopening the job URL in the same valid session recovers current status; browser memory is not its sole store.
- **AC-12.5:** Show bounded-backoff reconnection after temporary network failure; one failed poll does not mean failed computation.
- **AC-12.6:** Show 100%/`SUCCESS` only after result-manifest/metadata commit. Display retry attempts rather than masking restarted stages with smooth animation.
- **AC-12.7:** Show creation/start/finish times and safe errors. Persist terminal states and result references across Django restart.

#### US-13: Handle failure, retry and duplicate execution

**Story:** As a data-processing user, I want transient recovery and clear permanent errors so that I need not resubmit blindly.

**Label/dependencies:** Required; US-11, US-12, US-17.

- **AC-13.1:** Retry defined transient errors, such as timeout/rate limits, with bounded exponential backoff/jitter and at most three attempts; show the current attempt.
- **AC-13.2:** Do not pointlessly retry deterministic invalid-credential, permission, corrupt-file or invalid-rule failures.
- **AC-13.3:** Exhausted retries become `FAILED` with stable codes, redacted information and actionable advice, not full tracebacks/secrets.
- **AC-13.4:** Worker termination, duplicate messages and redelivery publish at most one visible successful version per Job; stale attempts cannot overwrite newer terminal states.
- **AC-13.5:** Detect abandoned work through heartbeats/leases or equivalent; recover or fail tasks past configured thresholds rather than leaving permanent `RUNNING` records.
- **AC-13.6:** Hide failed attempts' partial shards from pagination and reclaim temporary resources using a configurable policy.
- **AC-13.7:** Corrected input creates a new Job while retaining the failed record. Re-entering expired credentials must not silently switch files/accounts.

#### US-14: Cancel queued or running jobs

**Story:** As a data-processing user, I want to stop unnecessary processing so that resources are released.

**Label/dependencies:** Required; US-11 through US-13, US-16.

- **AC-14.1:** A cancelled queued Job never starts processing and reaches `CANCELLED`.
- **AC-14.2:** Immediately persist a running cancellation request and show "Cancelling"; do not report `CANCELLED` before computation stops.
- **AC-14.3:** With a reachable cluster, stop the associated Spark computation/driver and pending work within 60 seconds; changing a database flag alone is insufficient.
- **AC-14.4:** Cancellation control runs independently of the long-task worker; its API does not wait for natural completion.
- **AC-14.5:** Repeated cancellation is idempotent. Already successful/failed jobs retain their terminal state and completed results.
- **AC-14.6:** Atomically arbitrate cancellation against success; only one terminal state wins, and cancellation publishes no result.
- **AC-14.7:** Unreachable workers/clusters show honest pending confirmation and trigger recovery. Cancelled attempts must not automatically restart.

### E4: Distributed processing

#### US-15: Import S3 objects into Spark DataFrames

**Story:** As a platform user, I want files in a distributed engine so that subsequent operations can handle large data.

**Label/dependencies:** Required; US-01 through US-03, US-20.

- **AC-15.1:** Both CSV and supported Excel paths read the selected S3 object into a PySpark DataFrame using the user's authorization context.
- **AC-15.2:** Bind a version when available; otherwise fingerprint the object. Detected source changes fail explicitly rather than silently accepting unreproducible input.
- **AC-15.3:** Propagate read failures, expired permission, missing sheets and malformed rows to their Job with recognizable stages/codes.
- **AC-15.4:** Never preload the complete large CSV into Django, the browser or one pandas DataFrame; preview must not return the entire dataset to the web process.
- **AC-15.5:** Isolate authorization context per Spark job; concurrent jobs using different credentials must not overwrite shared global settings and cross accounts.
- **AC-15.6:** Import Excel asynchronously with documented memory/file/format bounds. Million-row CSV evidence does not establish equivalent Excel scale.

#### US-16: Execute across multiple partitions

**Story:** As a platform user, I want parallel Spark transformations so that processing remains feasible as data grows.

**Label/dependencies:** Required; US-15, US-05 through US-10.

- **AC-16.1:** Use approved DataFrame/distributed expressions for all three operations, not full Python row loops in the driver.
- **AC-16.2:** Do not use full `collect()`/`toPandas()` in the main transformation. Explicitly bound preview and result-page reads.
- **AC-16.3:** The million-row benchmark actually uses at least two workers and multiple effective partitions. Record executor/partition evidence rather than merely configuring idle workers.
- **AC-16.4:** Single- and multi-partition execution on fixed data agree on values, counts, nulls and statistics; page samples alone cannot establish full correctness.
- **AC-16.5:** Explain format, partition size, parallelism, skew and Excel trade-offs in the README; do not force one hard-coded partition count on every file.
- **AC-16.6:** Correlate Spark application/job groups with platform Jobs for progress, diagnosis and real cancellation; one failure must not disrupt other sessions' work.

#### US-17: Persist results and publish manifests reliably

**Story:** As a data-processing user, I want stable completed results so that they remain readable after a web restart.

**Label/dependencies:** Architecture requirement; US-16.

- **AC-17.1:** Store complete output in persistent platform-managed object/shared storage, primarily Parquet. Store references, schema, counts and manifests in the database, not millions of rows.
- **AC-17.2:** Write each attempt to its own temporary path. Atomically publish one manifest/success only after all required shards are written and checked.
- **AC-17.3:** Interrupted writes, worker crashes and duplicate execution expose no partial output, and failed attempts cannot overwrite successful output.
- **AC-17.4:** Manifests record stable shard order, bounded page-location information, version and expiry. Bound physical shards so a page does not scan all output.
- **AC-17.5:** Redis is control/cache storage, not the sole full-result store. Results remain readable after a web-container restart.
- **AC-17.6:** Expiry returns an explicit error; idempotent cleanup reclaims only the corresponding files and preserves other jobs.

### E5: Results and interface

#### US-18: Browse paginated results

**Story:** As a data-processing user, I want to view results page by page so that large data does not freeze my browser.

**Label/dependencies:** Required; US-17, US-21.

- **AC-18.1:** Successful-result APIs default to 100 rows, maximum 500, with schema, total count, result version and next cursor.
- **AC-18.2:** Traversing a fixed result visits every row exactly once. Paging/repeated reads cannot duplicate or omit rows because of Spark nondeterminism.
- **AC-18.3:** Bind cursors to Job/version. Invalid, modified, cross-job or expired cursors produce safe 4xx errors, without storage paths/secrets.
- **AC-18.4:** Read bounded manifest-selected shards/row groups; never restart Spark, recompute all data or load all results for each page. An object URL alone is not a pagination service.
- **AC-18.5:** Distinguish pending, failed, cancelled, expired and unauthorized results; never disguise them as successful empty arrays.
- **AC-18.6:** Zero-row results show schema/empty state; zero matches with source rows still show all original rows.
- **AC-18.7:** Keep the UI responsive during page loads. Completed-page API P95 is at most two seconds in the benchmark environment, with payload bounded by the requested page size.

#### US-19: Provide a clear end-to-end workflow

**Story:** As a data-processing user, I want a coherent connection-to-results workflow so that I need no technical operator.

**Label/dependencies:** Required; US-01 through US-18.

- **AC-19.1:** React provides connection, file/sheet selection, preview, configuration, tracking and results, with real data determining availability.
- **AC-19.2:** Connection, parsing, model and processing failures have understandable messages/next actions, not just "Something went wrong".
- **AC-19.3:** Distinct loading, queued, retrying, cancelling, success, failure, empty-file and zero-match states do not freeze inputs/navigation/status queries.
- **AC-19.4:** Review file, sheet, operation, targets and replacement/new-column configuration before submission; subsequent form edits cannot silently mutate the submitted Job.
- **AC-19.5:** All three operations are visible/selectable; extraction/normalization cannot be backend-only features without a demonstrable UI.
- **AC-19.6:** Complete end-to-end tests in the agreed desktop browser, with labels, keyboard operation and readable errors. A separate mobile app is not required.

### E6: Security

#### US-20: Protect AWS credentials and sensitive inputs

**Story:** As a data-processing user, I want credentials used only for authorized data access so that I can safely connect my bucket.

**Label/dependencies:** Required, with credential-lifecycle architecture additions; system-wide.

- **AC-20.1:** Use HTTPS publicly. Never place credentials in URLs, local storage, shareable page addresses or ordinary API responses.
- **AC-20.2:** Encrypt credentials retained across asynchronous processes, with independently managed encryption keys. Base64/database permissions are not encryption.
- **AC-20.3:** Trace unique test secrets through web/proxy/Celery/Spark/Flower/error/monitoring systems and verify absence from plaintext logs, task arguments and responses, including Spark configuration/UI.
- **AC-20.4:** Send only necessary instructions, operation and minimal schema to the model; no AWS credentials or source samples by default, and no model access to credentials.
- **AC-20.5:** Proposed credential default is 24 hours; disconnect/expiry rejects new jobs. Running tasks converge within explicit bounds, and cleanup must not arbitrarily remove needed inputs mid-task.
- **AC-20.6:** Require no write permission on source buckets and preserve original content/metadata. Authorize platform result writes separately.
- **AC-20.7:** Keep valid secrets out of repositories, images, sample configuration, recordings and demo data. Do not log private prompts/rows unredacted or use them as ordinary metric labels.

#### US-21: Isolate user/session resources

**Story:** As a data-processing user, I want my resources visible only to me so that public deployment protects my data.

**Label/dependencies:** Architecture requirement; all resource APIs.

- **AC-21.1:** Bind every connection, inspection, transformation and result to a server-validated owner; hiding IDs in the frontend is insufficient.
- **AC-21.2:** Session B cannot list files, read schema/status/results, cancel or download session A's resources by guessing or obtaining IDs.
- **AC-21.3:** Apply a consistent 403/404 policy without leaking another session's bucket, prompt, columns or task details.
- **AC-21.4:** Use unpredictable anonymous IDs and secure cookies, CSRF protection for cookie-authenticated mutations and constrained public CORS authorization.
- **AC-21.5:** Expiry/cleanup never damages another session. Flower, admin and Spark management are not anonymous public services.

### E7: Operations and delivery

#### US-22: Start the full environment with one command

**Story:** As a developer/reviewer, I want quick documented startup so that I can reproduce the whole workflow.

**Label/dependencies:** Required; React, Django, PostgreSQL, Redis, Celery, Spark, result storage and monitoring.

- **AC-22.1:** On a fresh environment meeting documented prerequisites, copy/configure the example environment and start the stack with `docker compose up --build`.
- **AC-22.2:** Provide executable/documented migrations, health checks and readiness handling; first startup must not require manual repairs inside multiple containers.
- **AC-22.3:** Include actual Celery workers, Redis broker/result configuration, a Spark master and at least two workers; synchronous/fake task execution is no substitute.
- **AC-22.4:** Persist database/results. Ordinary restarts preserve successful jobs; Redis loss does not erase database-backed terminal history.
- **AC-22.5:** Supply secret-free `.env.example`, resource requirements and clear missing-configuration errors; missing model configuration must not silently select a fake model.
- **AC-22.6:** Separate API, services, orchestration, Spark transformations and data access; test key transformations without starting HTTP.

#### US-23: Monitor tasks and Spark execution

**Story:** As an operator, I want task/resource visibility so that I can diagnose failures, backlogs and bottlenecks.

**Label/dependencies:** Required; US-11 through US-17.

- **AC-23.1:** Access-controlled Flower or equivalent shows live workers, execution and failures.
- **AC-23.2:** Observe queue length/wait, execution time, success/failure/cancellation counts, retries and model-cache hits.
- **AC-23.3:** Correlate each Job with API requests, Celery task IDs and Spark applications/job groups; demonstrate tracing an injected failure.
- **AC-23.4:** Use structured stage logs/timings without credentials, raw rows or complete private prompts. Avoid unbounded labels such as Job IDs.
- **AC-23.5:** Distinguish web liveness from dependency readiness; worker loss and unreachable Spark have visible diagnostic signals.
- **AC-23.6:** Document monitoring access, permissions, metrics and basic diagnosis for stuck queues, credential errors and Spark failure.

#### US-24: Automate business and failure tests

**Story:** As a developer/reviewer, I want automated business/task checks so that changes do not break essential behavior.

**Label/dependencies:** Required; all preceding required stories.

- **AC-24.1:** Deterministically test all three Spark operations, nulls, multiple/no matches, unusual names, literal replacements and partition equivalence.
- **AC-24.2:** Celery/integration tests cover queued/success/failure, transient retries, duplicate delivery, interruption, cancellation and terminal races; eager mode alone does not establish asynchronous execution.
- **AC-24.3:** Test paginated S3 listing, denial, changed/deleted objects, valid CSV/Excel and bad files; public acceptance separately uses genuine buckets with dynamically entered credentials.
- **AC-24.4:** Use controlled model responses for schema/safety/cache unit tests; retain separate genuine-model integration/demo evidence without requiring online inference for every unit test.
- **AC-24.5:** API/end-to-end tests cover 202 responses, isolation, secret redaction, the complete pipeline and pagination without duplicates/omissions.
- **AC-24.6:** Provide repeatable CI/README commands and actual results, clearly distinguishing unit, integration and performance scope/prerequisites.

#### US-25: Demonstrate million-row capability and responsiveness

**Story:** As a reviewer, I want a reproducible large-data run so that I can assess the scale requirement.

**Label/dependencies:** Required; US-16 through US-18, US-23.

- **AC-25.1:** Reproducibly generate at least 3,000,000 CSV rows and ten columns, including emails, order text, names, nulls, no-match and multi-match cases; record actual bytes.
- **AC-25.2:** Record CPU/RAM, worker count, cores/memory per worker, partitions, input region/network, software versions and configuration.
- **AC-25.3:** Proposed benchmark hardware totals 8 vCPU/32 GB, with two workers at two cores/6 GB each and headroom for driver/services. Target at most ten minutes for Spark reading/transformation/writing, excluding queue/model time; report full end-to-end time separately.
- **AC-25.4:** Verify no configured-memory failure and no API unresponsiveness caused by full in-memory datasets. Meet submission/page P95 targets and record samples/methods.
- **AC-25.5:** Publish exact generator expectations and verifiable counts/checks. Validate all-row counts, key-column statistics and deterministic samples, not merely the first page's appearance.
- **AC-25.6:** Report at least one complete run's actual time, resources, effective partitions, outcome and limits. Separate million-row CSV evidence from Excel tests. Unmet timing is a failure or explicit requirement change, never a silently deleted target.

#### US-26: Let reviewers complete a genuine public workflow

**Story:** As a reviewer, I want a public URL and my own S3 input so that I can independently validate the delivery.

**Label/dependencies:** Required; complete core pipeline and security.

- **AC-26.1:** Provide working external HTTPS for React and required APIs, without the developer's laptop, VPN or internal ports.
- **AC-26.2:** Valid unconfigured credentials/bucket support connecting, selection, inspection, natural-language replacement, asynchronous completion and paginated real results.
- **AC-26.3:** Demonstrate Excel/extraction/normalization from the frontend with actual public-environment model, Celery, Redis and Spark, not canned outputs.
- **AC-26.4:** Web scaling/restart preserves successful records; database, Redis, Spark and monitoring remain private.
- **AC-26.5:** Disclose demo capacity, task deadlines, credential/result retention and S3 permissions in UI/README; capacity bounds cannot replace independent million-row validation.
- **AC-26.6:** Provide reasonable concurrency/queue limits and understandable overload errors. One long job must not block others' status/cancellation controls.

#### US-27: Deliver understandable, reproducible code and demonstration

**Story:** As a developer/reviewer, I want complete source, design documentation and a demo so that I can evaluate/reproduce the system.

**Label/dependencies:** Required; the actual delivered implementation.

- **AC-27.1:** Provide an accessible GitHub repository with complete frontend/backend/task/Spark code, containers, tests and necessary scripts, without valid secrets.
- **AC-27.2:** Document installation, execution, configuration, permissions, public URL, use, testing and troubleshooting with reproducible instructions.
- **AC-27.3:** Include an architecture diagram/rationale explaining API/task/data boundaries, Celery versus Spark, Redis's three uses, pagination, partitioning, security and recovery trade-offs.
- **AC-27.4:** Document formats, Excel bounds, regex semantics/subset, two additional operations, null/no-match semantics, expiry/cancellation and all known limitations.
- **AC-27.5:** Embed an accessible short video showing user-entered S3 authorization, file selection, asynchronous submission/completion, progress and pagination. Omit/redact active Access/Secret Keys.
- **AC-27.6:** Supply actual test/performance evidence consistent with public behavior. Explicitly list incomplete work; do not present optional/unimplemented functionality as delivered.

### E8: Optional enhancement

#### US-28: Download complete results

**Story:** As a data-processing user, I want a full download so that I can continue working in other tools.

**Label/dependencies:** Optional; the assessment requires pagination, not explicitly full downloads. US-17, US-21.

- **AC-28.1:** Successful output can request CSV/Parquet export; large exports run asynchronously, not within one API request.
- **AC-28.2:** Export counts/values match the current result version, with documented quoting, special-character, newline and null rules.
- **AC-28.3:** Use short-lived access-controlled links; other sessions cannot enumerate IDs/paths to download files.
- **AC-28.4:** No successful download links for cancelled, failed, incomplete or expired results.
- **AC-28.5:** Explicitly control/document spreadsheet-formula risks in CSV exports; do not silently alter original Parquet values as a safety measure.

## 4. Job state machine and API conventions

### 4.1 Job states

```text
QUEUED  -> RUNNING -> SUCCESS
                  -> FAILED
                  -> CANCELLED
QUEUED  ----------> CANCELLED
QUEUED  ----------> FAILED   (unschedulable after recovery is exhausted)
```

- During retry, retain `RUNNING` with `stage=RETRYING`, `attempt` and `next_retry_at`.
- Represent requested cancellation with `cancel_requested_at`/`stage=CANCELLING`; enter `CANCELLED` only after stopping.
- Terminal states cannot overwrite each other. A user retry after correcting parameters creates a new Job with immutable original inputs.
- Reserve `progress=100` for committed success; failed/cancelled jobs retain their last stage/progress.
- Include `job_id`, ownership and timestamps; associate credentials only through controlled references.

### 4.2 Proposed APIs and story mapping

These are design proposals; the [API contract](API.md) documents implemented endpoints.

| Method/path | Responsibility | Stories |
|---|---|---|
| `POST /api/s3/connections` | Validate/create connection | US-01, 20, 21 |
| `DELETE /api/s3/connections/{id}` | Disconnect/refuse new work | US-20 |
| `GET /api/s3/connections/{id}/files` | S3 object listing/cursor | US-02 |
| `POST /api/files/inspect` | Asynchronous file/sheet inspection | US-03, 04 |
| `POST /api/jobs` | Create transformation; return 202 | US-05 through 11 |
| `GET /api/jobs/{id}` | Status, stage, statistics, safe errors | US-12, 13 |
| `POST /api/jobs/{id}/cancel` | Request cancellation/stop computation | US-14 |
| `GET /api/jobs/{id}/results?cursor=...&limit=...` | Read one fixed-version result page | US-18 |
| `POST /api/jobs/{id}/exports` | Optional asynchronous export | US-28 |
| `GET /api/exports/{id}` | Optional export status/download URL | US-28 |

Suggested status fields: `status`, `stage`, `progress`, `progress_kind`, `attempt`, `cancel_requested`, `created_at`, `started_at`, `finished_at`, `result_available` and safe `error`. Inspections also need queryable asynchronous status, not a separate blocking-only interface.

## 5. Acceptance examples and end-to-end scenarios

### 5.1 Fixed replacement examples

Here `null` means a genuine null; "empty string" means a zero-character string.

| ID | Input Email/text | Replacement | Expected |
|---|---|---|---|
| 1 | `john.doe@example.com` | `REDACTED` | `REDACTED` |
| 2 | `Contact a@example.com or b@example.org` | `REDACTED` | `Contact REDACTED or REDACTED` |
| 3 | `not-an-email` | `REDACTED` | `not-an-email` |
| 4 | null | `REDACTED` | null |
| 5 | empty string | `REDACTED` | empty string |
| 6 | `a@example.com` | literal `$1` | literal `$1` |
| 7 | `Contact a@example.com` | empty string | `Contact ` |

Also include an unselected column containing the same email and assert no change. Model semantic tests compare outputs/positive/negative cases, not exact regex strings.

### 5.2 Final end-to-end scenarios

| Scenario | Path and evidence |
|---|---|
| Dynamic authorization | New session; enter own credentials; list bucket; choose CSV; preview/select columns; submit replacement; 202; real state changes; success; pages |
| Excel | Multi-sheet `.xlsx`; select sheet; preview; same asynchronous/Spark pipeline; correct output |
| Model cache | Repeat an identical valid configuration in the same session; second hit; no additional inference |
| Additional operations | Frontend extraction and normalization; genuine model plans; Spark; exact expected values |
| Errors/security | Invalid credentials, bad files, dangerous regex and cross-session reads/cancels refused without secret leaks |
| Asynchronous reliability | Worker interruption, duplicate delivery and transient broker failure recover/fail deterministically, without lost jobs or duplicate published results |
| Actual cancellation | Cancel a long Spark job; computation stops; `CANCELLED`; no automatic restart |
| Millions of rows | Three million rows; multiple workers/partitions; measured resources/timing; full correctness; bounded pages |
| Public delivery | Genuine workflow over an external URL; accessible README, source, tests, performance report and safe video |

## 6. Assessment traceability

| Original requirement | Stories |
|---|---|
| 1. Data Ingestion: own credentials, any authorized bucket, CSV/Excel, credential protection | US-01 through 04, 15, 20 |
| 2. Django: API/task/data separation, persistent Jobs, immediate IDs and results queries | US-11 through 13, 17, 18, 22 |
| 3. Celery & Redis: heavy asynchronous work, cache, progress, failure/retry/cancel | US-05, 07, 11 through 14, 23 |
| 4. PySpark: distributed transformations, millions of rows, pagination, partition rationale | US-08 through 10, 15 through 18, 25, 27 |
| 5. React: connection, files/columns, natural language, replacement, progress/errors/pages | US-01 through 04, 08 through 14, 18, 19 |
| 6. LLM: multiple phrasings, valid/safe regex, Redis cache, two additional operations | US-05 through 10 |
| Development guidelines: architecture, errors, Compose, monitoring, task/Spark tests | US-06, 11 through 17, 22 through 25, 27 |
| Deliverables: GitHub, README, public deployment, embedded demo | US-26, 27 |
| Architecture additions: atomic publication, isolation, lifecycle, idempotency | US-11, 13, 14, 17, 20, 21 |

## 7. Suggested implementation order and definition of done

### 7.1 Order

1. **Infrastructure/security:** US-20, 21, 22 and US-11 through 14 task foundations, with real asynchronous execution, durable states and isolation.
2. **CSV path:** CSV portions of US-01 through 04 and US-15 through 19, initially with fixed development-only rules; those rules are not the final LLM implementation.
3. **Genuine LLM path:** US-05 through 08, including cache, safety and natural-language replacement.
4. **Full functionality:** Excel in US-03, US-09/10, failures, cancellation and lifecycle cases.
5. **Operations/delivery:** US-23 through 27, with tests added throughout. Performance/public deployment are delivery gates; US-28 is optional if time allows.

### 7.2 Definition of done per story

- Every AC has reviewable evidence appropriate to its nature: behavior tests, architecture review or runtime observations, not unrelated test counts.
- User-facing stories are demonstrable with integrated frontend/backend; technical stories have corresponding integration evidence.
- Normal, failure and necessary boundary cases work without manual database repairs.
- Backend enforcement implements security/ownership, not frontend warnings alone.
- Documentation, configuration and actual behavior agree; key checks pass without known core-flow blockers.
- This design requires US-01 through US-27 to pass before claiming full completion; a happy path alone does not satisfy the full assessment.

## 8. Source

The user-provided two-page `Web_Application_for_Regex_Pattern_Matching_and_Replacement.pdf`.

Specific formats, chosen additional operations, session isolation, storage, default limits, timing targets and API details are project design decisions; they do not reduce the assessment's prescribed stack or deliverables.
