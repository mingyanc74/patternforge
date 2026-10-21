# Security and deployment notes

- Keep `.env`, databases, result files and runtime environments out of Git. Bootstrap generates independent secrets. Never use test settings in deployment.
- AWS credentials are encrypted at rest with a separate Fernet key. Losing the key makes saved payloads unusable; store and back it up securely outside the repository.
- S3 credentials are entered over HTTPS in public deployments. Session cookies are HTTP-only and secure in the production overlay. Anonymous sessions receive CSRF validation for state changes as well as authenticated sessions.
- Nginx emits CSP, framing and cache headers at server scope so location-level cache rules do not suppress security headers. Duplicate upstream security/cache headers are hidden. The API independently denies framing. Caddy owns the public HSTS policy; Django's `security.W004` remains an explicitly reviewed edge-termination warning, not a claim that public HSTS is absent. Browser preload registration is not enabled.
- Resource lookup always includes the session owner. UUIDs alone do not authorize access. File/result cursors are signed and scoped to their owner and version.
- The optional website entrance stores only a Django password hash in private deployment configuration. Password checks are throttled; successful unlock/lock rotates session and CSRF tokens. This shared password is not a personal account; browser ownership remains independently enforced. Do not send the plaintext password in URLs, logs or Git.
- Connections default to one hour. Imported snapshots are independently retained for 24 hours under the same owner, allowing processing after connection expiry/disconnect. Snapshot jobs receive no AWS credentials. Retention cleanup defers deletion while a snapshot is referenced by active work.
- Source access is read-only. Output uses platform-managed storage. No user S3 object is overwritten, deleted or uploaded by the processing pipeline.
- Celery arguments contain IDs, not credentials. Attempt specs contain ciphertext, are mode-restricted and are deleted after execution. The decryption key is not sent to model services.
- Spark master and executor containers do not receive the application `.env`, database password, model key or encryption key. Only the isolated orchestration/driver service needs connection decryption.
- Models receive no raw data rows or AWS secrets. Column names and user instructions may themselves be sensitive; choose your provider and retention settings accordingly. The OpenAI-compatible request explicitly sets `store=false`.
- Regex validation uses a restricted subset, isolated Java checks and adversarial probes. Timeouts/text limits/process isolation remain essential because a small probe set is not a mathematical safety proof.
- Spark applications isolate credentials per Job and configure redaction. Raw driver stdout/stderr is suppressed to avoid logging input rows or configurations. Operators receive safe categories, stage, Job ID and application metadata.
- Flower is authenticated and loopback-bound. `/internal/metrics` is blocked by the public Nginx frontend; scrape it only on the private container network. Database, Redis and Spark ports are private.
- The optional S3 endpoint override is **server configuration**, not a browser-supplied arbitrary URL. HTTP endpoints are disabled unless the explicit test flag is enabled.
- The CI provider overlay is for synthetic testing only. Never attach real credentials, public routing or private user data to it.
- Apply bounded resource/queue policies and enforce the published retention policy. A separate dispatcher performs lease recovery and cleanup even while the processing worker is busy.
- Crash-leftover attempt directories are reclaimed after `TEMP_TTL_HOURS` (default 24) for terminal jobs. Active jobs, unexpired published results, unrecognized folders and redirected paths are excluded from that cleanup.
- The default result storage is a single-host shared volume, not encrypted cloud object storage. Use encrypted host storage, restricted backups and a suitable shared/object store before extending to multiple hosts.
- Run `python backend/manage.py check --deploy` with production configuration and investigate its findings before exposing the service. Review dependency updates and container vulnerabilities for the actual deployment date.

If you identify a credential leak or isolation issue, stop affected processing, restrict the deployment, rotate the relevant secrets, and report the issue privately to the repository owner. Do not post real secrets in public issues.
