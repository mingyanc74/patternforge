# Architecture decisions

## Boundaries

`core/views.py` implements a small HTTP/session boundary. Serializers reject invalid input before job creation. `core/services` handles external providers, rule plans and page reads. `core/tasks.py` owns durable task transitions and process supervision. `spark_engine` owns parsing and Spark expressions; it has no dependency on HTTP handlers.

## Durable asynchronous submission

A single database transaction creates the Job and Outbox row. The API returns HTTP 202 after commit without a broker round-trip. A standalone dispatcher publishes pending references and retries after broker failure. Duplicate deliveries contend on the Job row and may only claim a queued Job. Recovery invalidates stale leases before requeueing.

Celery uses Redis database 0 as broker, database 1 as task backend, database 2 as plan cache. These logical databases are not independent failure domains. PostgreSQL holds authoritative job status. Redis AOF plus the database outbox provides queue recovery; a flush is not treated as deletion of application history.

## State transitions

`QUEUED -> RUNNING -> SUCCESS | FAILED | CANCELLED`. A queued Job can also fail or cancel before execution. Transient errors move the persisted Job back to `QUEUED` with `stage=RETRYING` and a future outbox publication time. The UI displays the attempt, so the retry is not hidden. This is the implementation's explicit refinement of the initial backlog's retry-state proposal.

Terminal publication is protected by a database row lock and current lease. Cancellation is a request first, a terminal status after the supervisor stops its process. The driver independently observes its lease and deadline. Worker-loss recovery is lease-based; the old attempt cannot publish a later result.

## Credential isolation

Each connection stores a Fernet-encrypted JSON credential payload. Encryption keys come from private environment configuration. Queue messages contain Job IDs only. Each Spark application receives an attempt specification with encrypted credentials; it decrypts inside its isolated driver. Spark redaction is configured before credentials are introduced. Driver output is suppressed and failures expose safe error categories, not raw data-bearing Spark stack traces.

Credentials cannot be used to start a new Job after expiry/disconnect. Active jobs prevent credential deletion until they converge; runtime limits prevent indefinite retention. A maintenance pass clears expired/disconnected inactive payloads.

## LLM and regex boundaries

The provider returns a strict JSON plan; server validation is authoritative even with provider schema enforcement. Normalization maps to an enum of approved Spark operations. Regex rules pass a conservative parser subset, bounded Python regex probes and a killable Java regex process. Validation cannot prove every expression is linear time; hard job deadlines, text limits and separate applications remain necessary.

Cache keys contain a hash of session owner, operation, exact trimmed instruction, columns, model/base URL and schema/validator versions. Case-sensitive instruction content is not lowercased. Only a validated plan is cached. A short Redis lock prevents duplicate generation. Failures are never cached as valid plans.

## CSV and Excel

CSV headers are checked independently, before Spark can silently rename duplicates. The reader uses an explicit all-string Schema, strict malformed-record handling and multiline support. Multiline input can serialize source parsing; an explicit repartition distributes the transformation stage.

Excel is streamed using openpyxl into an attempt-local CSV, then read into a Spark DataFrame. This avoids loading a workbook as a pandas table and avoids an extra Spark Excel connector compatibility boundary. It does not make Excel intrinsically partitionable. Compressed size, expanded archive size, row count and cell sizes are bounded. Formula evaluation is not performed; cached workbook values may be absent.

## Results and paging

Workers write Parquet into a unique attempt directory. Each file has at most 1,000 rows. PyArrow metadata builds a stable ordered list of row groups with cumulative offsets. The database publishes the complete manifest path atomically with `SUCCESS`; partial attempts stay invisible.

The page endpoint validates a signed cursor scoped to owner, Job and manifest version. It seeks relevant files/row groups and reads small batches. A JSON byte budget limits very wide pages. The next cursor uses the number actually returned. No per-page Spark startup, global `collect`, million-row JSON payload or Redis result dump is needed.

The supplied named volume is shared by all containers on one host. Moving executors to separate hosts requires shared storage and an adapted page reader; the default volume is deliberately not presented as multi-host object-store deployment.

## Limits and outstanding production work

The system is scoped to this assessment, not an unbounded multi-tenant SaaS. Anonymous sessions provide resource ownership. A production service should add authenticated accounts if persistence across browsers is required, organization-specific quota policies, managed backups and centrally retained metrics. No registration or billing subsystem is required by the PDF.

Large result download is an optional backlog item and is not implemented as a synchronous whole-dataset HTTP response.
