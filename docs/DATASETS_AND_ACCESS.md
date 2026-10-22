# Website access, browser workspaces and S3 connections

Website access, workspace ownership and AWS authorization are separate mechanisms, not one account login.

| Mechanism | Purpose | Lifetime |
|---|---|---|
| Website password | Enter the demo; not personal registration or AWS login | Administrator-configured hash; changing it invalidates previous gate authorization; Lock workspace relocks this browser |
| Browser session | Isolate this browser's connections, imported datasets and jobs | Server-side session with secure HttpOnly cookies; sharing the gate password does not share workspace data |
| S3 connection | Use entered AWS credentials to check permissions, list and import objects | New connections default to one hour; AWS temporary credentials may expire earlier |
| Imported dataset | Retained read-only source-object snapshot for Spark | Default 24 hours, independent of the connection; expiry is shown in the UI |
| Result | A job's paginated Parquet output | Default 24 hours, independent of source and connection |

## Normal workflow

1. Unlock with the website password. This grants no AWS authorization.
2. Enter your AWS Access Key, Secret, bucket and region in Connections; add a Session Token for temporary credentials.
3. The backend actually checks S3 permissions and lists objects. Preview selected file submits an asynchronous CSV/Excel import.
4. Celery downloads the specified version or ETag-bound bytes, enforces size/source-consistency checks and calculates SHA-256. Spark reads the shared-volume snapshot and produces schema/preview. Incomplete or failed imports are not available datasets.
5. Reopen successful imports from Imported datasets. Within their retention window, new transformations do not need the original connection or another AWS download, even after disconnect, connection expiry or credential cleanup.
6. Reconnect to browse/import new objects. An imported dataset is a point-in-time snapshot, not an automatic mirror of later S3 changes.

For multi-sheet Excel, select and successfully preview a sheet before processing it. Older previews created before snapshot support cannot become retained datasets retroactively; reimport them. Existing job history/results are not deleted by this change.

## Implementation and security boundaries

- A successful inspection ID is also its dataset ID. Independent `dataset_path`/expiry fields and `transform.input_dataset` references retain ownership. APIs expose neither local paths nor raw AWS credentials.
- Downloads, parsing, inference and transformations run in the background; APIs return job IDs immediately.
- The genuine S3 endpoint requires credentials. The separate optional sample adapter remains explicitly labelled `sample`, for development/demonstration only.
- Directory isolation, session ownership, CSRF, password checks, leases and cancellation still apply. Cleanup defers removal of expired input referenced by active jobs.
- Source objects remain unchanged. Datasets/results are not retained forever; connection expiry and dataset expiry have distinct messages.
- Downloading once to a shared volume costs disk and import transfer, but decouples credential lifetime from repeatable processing. Multiple Spark executors read/partition that snapshot; this is not browser-local computation.

## Configuration and API

`CREDENTIAL_TTL_HOURS=1`, `DATASET_TTL_HOURS=24`. Changed defaults apply to new connections, not retroactively to existing expiry timestamps.

`DEMO_ACCESS_PASSWORD_HASH_B64` is Base64 of a Django PBKDF2 hash, not Base64 of the password. No plaintext password belongs in Git or server configuration. An empty setting disables the gate. Redis-backed throttling permits five unlock attempts per minute per source; shared network exits can share that limit.

While locked, `GET /api/bootstrap` returns only `access_required` and a CSRF token. `POST /api/access/unlock` accepts a password and rotates session/CSRF tokens on success. `POST /api/access/lock` relocks without deleting or confusing the current workspace. `GET /api/datasets` lists this browser's retained available imports. Inspection/transformation responses include `dataset_available`, `dataset_expires_at` and `input_dataset_id`.

The public health endpoint exposes only brief dependency status; internal monitoring remains private. Static frontend assets are downloadable, but the backend enforces the gate for workspace APIs rather than merely hiding buttons.

## Evidence boundaries

Development fixtures verify processing after application connection expiry and after removal of the fixture's source object. These are not real-AWS evidence.

Separate real-AWS acceptance on 2026-10-21 verified `test_data.csv`/`test_data.xlsx` in genuine private buckets, with AWS/local/snapshot SHA-256 equality. Accelerating only a newly created test connection's `expires_at` made new listing/import return 410 while both retained formats completed further Spark transformations without changing their retention deadlines. A second real bucket and 50,000-row object also passed. See [real-AWS acceptance](REAL_AWS_ACCEPTANCE.md).

The later [UI regression](../reports/UI_REFRESH.md) additionally processed a retained CSV after its original one-hour connection naturally expired. Neither test establishes natural STS expiry or continuous observation for 24 hours. Earlier conversational filenames `contacts.csv`/`contacts.xlsx` were not verified in this project and are not claimed as successful imports.
