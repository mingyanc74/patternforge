# PatternForge

A private, natural-language workspace for transforming CSV and Excel data from **your own Amazon S3 bucket**.

**React · Django REST Framework · Celery · Redis · PostgreSQL · PySpark**

[中文启动说明](docs/START_HERE_zh.md) · [Architecture](docs/ARCHITECTURE.md) · [Submission checklist](docs/SUBMISSION.md) · [API contract](docs/API.md) · [Security](docs/SECURITY.md)

## What it does

- Connect with user-entered AWS Access Key, Secret Key, optional STS token, bucket and region. No predefined bucket or hard-coded production credentials.
- Browse S3 objects with prefix filtering and continuation-token pagination.
- Inspect CSV and `.xlsx` asynchronously; select an Excel worksheet and preview at most 100 rows.
- Describe a pattern in natural language, select text columns, and replace every non-overlapping match with literal text.
- Use two additional LLM-assisted transformations through the same task/Spark pipeline: **extract a field** into a new column, and **standardize text** with ordered, approved operations.
- Track persistent jobs, recover after refresh, retry transient failures, and cancel actual computation.
- Browse immutable Parquet results using signed cursors without recomputing or collecting the whole dataset.
- Monitor workers with Flower and persisted job metrics. Start the complete stack with Docker Compose.

## Honest validation status

The repository contains real provider integrations. It does not invent model output when a model key is missing.

Local tests cover API validation, encrypted credentials, session/CSRF isolation, cache behavior, retries, cancellation state, outbox recovery, pagination and real Java/Spark expressions. CSV and Excel inspection are also exercised through the actual isolated Spark driver. Native Windows Parquet output requires Hadoop native binaries; the complete output path is tested in Linux CI/Docker instead of pretending the Windows installation includes them.

The separate `compose.ci.yml` overlay uses **synthetic S3 and LLM protocol fixtures** solely for reproducible integration tests. PostgreSQL, Celery, Redis, the Spark master and two Spark workers remain real. A green fixture test is not proof of real AWS permissions, real model accuracy, or a public deployment.

**Before final assessment submission:** configure a real LLM, perform the real-AWS acceptance run, provide a working public HTTPS URL, run and attach the large-data benchmark, and embed the real demonstration video. Track these in [SUBMISSION.md](docs/SUBMISSION.md); unverified items are not claimed as complete.

## Quick start: complete stack

Prerequisites: Docker with Compose v2, an x86-64 Linux container runtime, and adequate available memory. For development, allocate at least 8 GB to Docker; use a larger instance for the multi-million-row benchmark. Docker Desktop on Windows must be running before Compose is invoked.

```bash
python scripts/bootstrap.py
```

This creates a git-ignored `.env` with independently generated application, encryption, database and monitor secrets. It never overwrites an existing file or prints the secrets. Set these server-side values in `.env`:

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-private-service-key
LLM_MODEL=a-structured-output-capable-model-you-can-access
```

Use a provider/model supporting the Chat Completions JSON-schema protocol. An explicitly configured compatible provider with JSON-object mode can set `LLM_JSON_SCHEMA=0`; server-side validation still applies. No automatic fallback to weaker modes occurs.

```bash
docker compose up --build
```

Open **http://localhost:8080**. Flower is bound to **http://localhost:5555** with credentials from the private `FLOWER_BASIC_AUTH` setting. Database, Redis, Spark and worker ports are not published.

Enter **your AWS credentials in the application**, not in repository files. The bucket needs list access and selected objects need read access. The platform never requires write permission to your input bucket. Supporting region discovery may require permission to inspect bucket location. A denied or ambiguous AWS response is surfaced safely rather than misdiagnosed.

Normal shutdown preserves database and result volumes:

```bash
docker compose down
```

Do not add `-v` unless you explicitly intend to remove local persisted data.

## VS Code / native UI development

Open the repository folder in VS Code. Provided tasks cover bootstrap, full-stack Docker, local backend, frontend build and tests.

```bash
python -m venv .venv
# Activate .venv using your platform's normal activation command.
python -m pip install -r backend/requirements-dev.txt
python scripts/bootstrap.py
python scripts/local_backend.py
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Vite proxies `/api` to `127.0.0.1:8000`. The local backend uses SQLite and local storage for UI/API development. It deliberately reports missing queue/model configuration. **A standalone frontend and development server do not replace the complete Celery/Redis/Spark stack.** Use Compose for full end-to-end processing.

Native Windows Spark tests use Java 17 and a direct Java launcher to avoid command-shell encoding corruption in Chinese paths. Linux containers remain the supported complete processing environment.

## User workflow

1. Connect your S3 bucket, using an STS session token when applicable.
2. Select a CSV or Excel file. For Excel, select the required worksheet.
3. Inspect it, confirm the preview, and choose target columns.
4. Select **Find & replace**, **Extract a field**, or **Clean & standardize** and enter an instruction.
5. Submit. The API returns HTTP 202 and a persistent Job ID immediately; heavy work stays in Celery/Spark.
6. Follow stages, return through Activity or the task URL, or cancel the job.
7. Read the completed result in pages. The original S3 object is never overwritten.

Replacement is literal: `$1` is inserted as `$1`, not interpreted as a capture group. Empty replacement deletes matches. Null stays null. No matches is a successful job with zero changed cells, not an empty result set. Extraction uses the first match and returns null when no value is found.

## Format and operation boundaries

| Area | Behavior |
|---|---|
| CSV | Header required; UTF-8, UTF-16, ISO-8859-1; comma, semicolon, tab or pipe; quoted commas and multiline fields supported |
| Types | Values are ingested as strings to preserve IDs and leading zeroes; Excel dates become ISO text |
| Null | CSV `\N` is the documented null marker; quoted empty text is distinct where the parser supports it |
| Excel | `.xlsx`, worksheets selectable, streaming conversion to a staged CSV followed by a Spark DataFrame; `.xls`, encrypted workbooks and formula evaluation are unsupported |
| Headers | 1–200 nonempty, case-insensitively unique names; max 255 characters |
| Default limits | CSV 2 GB; Excel 100 MB; cells 65,536 characters; preview row 128 KiB of serialized characters; tunable via configuration |
| Normalization | Ordered trim, collapse whitespace, lowercase, uppercase; arbitrary semantic rewriting is rejected |
| Regex | Conservative Java/Python-compatible subset; no lookaround, backreferences, nested repetition, repeated alternatives, unbounded wildcard repeats or zero-length matches |
| Pagination | Default 100, max 500 rows; JSON page bounded to approximately 2 MiB, so wide rows can yield fewer rows with a valid next cursor |
| Retention | Credentials and results default to 24 hours; explicit disconnect prevents new jobs |

LLM plans are schema-validated; no generated Python, SQL, shell commands or arbitrary functions are evaluated. Only the prompt, chosen operation and necessary column names are sent to the model. Raw data rows and AWS credentials are never included in model requests.

## Architecture

```mermaid
flowchart LR
  UI[React] --> API[Django API]
  API --> DB[(PostgreSQL jobs / encrypted credentials / outbox)]
  Dispatcher[Outbox dispatcher] --> DB
  Dispatcher --> Redis[(Redis broker / task backend / plan cache)]
  Redis --> Worker[Celery orchestration worker]
  Worker --> LLM[Configured LLM service]
  Worker --> Driver[Isolated Spark driver per job]
  Driver --> S3[User's S3 bucket]
  Driver --> Cluster[Spark master + two workers]
  Cluster --> Store[(Shared persistent Parquet storage)]
  API --> Store
  UI -->|signed cursor pages| API
  Flower[Private Flower monitor] --> Redis
```

- The HTTP process never parses a full file, generates a regex or performs replacement.
- PostgreSQL is authoritative for job status; Redis Celery results are not the only durable job record.
- The transactional outbox prevents accepted HTTP 202 jobs from being lost between database commit and broker publication. A dispatcher outside the task queue also resumes publication after Redis returns.
- Each job has a lease and attempt-specific workspace. Duplicate deliveries cannot overwrite terminal states. Only a complete manifest becomes visible.
- Each Spark application has an isolated credential context. Plaintext AWS keys are not passed in command-line arguments or Celery messages.
- The worker polls cancellation while its child runs. An independent driver lease guard also stops work after parent loss, cancellation, lease replacement or a hard deadline.
- Parquet is split into bounded files and indexed by row-group metadata. The API reads the relevant batches through PyArrow rather than starting Spark for every page.
- The provided deployment uses a named shared volume, appropriate for a single-host multi-container assessment. A multi-host deployment must replace it with a shared filesystem or object-store-aware result service; mounting unrelated local directories on different hosts is not supported.

### Partitioning and scale

CSV parsing enables multiline support, which may make a single source object unsplittable during parsing. After ingestion the DataFrame is explicitly repartitioned (`SPARK_PARTITIONS`, default 8), and replacements/extraction/normalization use Spark expressions across those partitions. This is an intentional correctness/performance trade-off; bulk production workloads should prefer partitioned CSV/Parquet inputs or a separate single-line CSV mode.

Input caching uses `DISK_ONLY` to avoid retaining a large dataset in driver memory. Statistics and output remain distributed. At most 100 bounded preview rows are collected. A result file holds at most 1,000 records; the API indexes its row groups and batches page reads. Output ordering is stable within a manifest version, not guaranteed to preserve original input order.

Two Spark workers each advertise one core and 2 GB by default; executor memory is 1 GB and the application is capped at two cores. Increase resources and partitions together for the benchmark; do not interpret a higher partition count alone as more physical compute. The README and actual report must state the tested settings.

## Tests and continuous integration

```bash
python -m pip install -r backend/requirements-dev.txt -r backend/requirements-spark.txt
python -m ruff check backend scripts
python -m pytest -q
cd frontend
npm ci
npm run build
npm test
```

Java 17 is needed for Java validation and Spark tests. Use `pytest -m "not spark"` for the remaining backend tests. The Java validator test still requires Java. Test credentials and response fixtures are deliberately invalid for real services.

CI contains three independent jobs: backend/real Spark tests, frontend checks, and a **real distributed Docker stack** tested through HTTP against the explicitly synthetic provider fixtures:

```bash
python scripts/bootstrap.py
docker compose -f docker-compose.yml -f compose.ci.yml up -d --build --wait
python scripts/smoke_e2e.py --rows 1000
```

The smoke test covers dynamic bucket setup, CSV, multi-sheet Excel, all three transformations, multiple partitions, result pages, session isolation and a cancellation request. Provider fixtures do not prove model semantics or AWS authentication correctness; those have a separate real-service checklist.

For a large test, manually run the **Verify application** workflow with `benchmark_rows=3000000` or use:

```bash
python scripts/smoke_e2e.py --rows 3000000 --report reports/local/three-million-rows.json
```

This exercises actual S3-protocol input and three distributed transformations with deterministic provider fixtures. Its generated dataset currently has four columns; use the ten-column generator for the separately specified assessment baseline. Record environment resources, rows, actual bytes, partitions, timings, correctness and limitations. Do not label fixture timing as a real-AWS/real-LLM measurement.

Generate ten-column files for the real acceptance run:

```bash
python scripts/generate_dataset.py --rows 3000000 --output data/fixtures/customers.csv
python scripts/generate_dataset.py --rows 100 --output data/fixtures/customers.xlsx
```

Upload only to a bucket you intentionally choose, then process it through the normal UI. The generator does not upload automatically or require access to any existing private file.

## Production deployment

Use a Docker-capable Linux host with sufficient memory, a hostname pointed to it, and inbound ports 80/443. Set `DOMAIN` in the server's private `.env`, configure a real model, and run:

```bash
docker compose -f docker-compose.yml -f compose.production.yml up -d --build
```

Caddy terminates HTTPS; secure cookies, trusted origins and HTTPS redirects are enabled for the web API. Only the gateway is public; monitor access remains loopback-only. Back up PostgreSQL and the result volume; protect the encryption key independently. See [SECURITY.md](docs/SECURITY.md) before making a deployment public.

## Demo video and public URL

**Public URL:** not provisioned in this repository.  
**Demo video:** not recorded yet. Use the exact recording checklist in [SUBMISSION.md](docs/SUBMISSION.md), then replace these lines with the verified URL and an embedded video link/player. A UI-only recording does not meet the required real S3 plus completed asynchronous job demonstration.

## Troubleshooting

| Symptom | Next step |
|---|---|
| Service setup required | Check Docker is running; inspect `docker compose ps`; configure the real model |
| Job stays queued | Check dispatcher, Redis, Celery worker and queued outbox metrics; restarting only the browser cannot fix a stopped worker |
| AWS connection fails | Check key, session token, region, bucket name, list/read permissions and key expiry |
| Source changed | Reinspect the object; jobs are bound to its recorded fingerprint |
| Unsupported / unsafe regex | Use a more specific description within the documented subset; do not disable validation |
| Excel requires a sheet | Select a worksheet and inspect it before submitting a transformation |
| Result expired | Submit a new job; expiry does not modify the original S3 file |
| Native Windows Parquet fails | Use the supplied Linux Docker environment; do not download unknown Hadoop DLLs just to suppress the failure |

## Primary technical references

- [Spark 3.5.8 documentation](https://spark.apache.org/docs/3.5.8/)
- [Celery with Django and transaction boundaries](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [OpenAI structured output protocol](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
