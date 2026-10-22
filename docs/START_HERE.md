# Run on the desktop and in VS Code

Try the deployed [Rulecraft application](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/) without development tools. Rulecraft is PatternForge's current UI name, formerly Clearflow; the existing hostname, API and data are unchanged. It uses actual services, not an interactive prototype. Processing your own files requires an authorized Amazon S3 bucket and read-only credentials. See [real-AWS acceptance](REAL_AWS_ACCEPTANCE.md).

## Recommended: full stack

1. Open the desktop `patternforge` folder in VS Code.
2. Run `python scripts/bootstrap.py` in its terminal. This creates private `.env` only if absent and never overwrites existing configuration.
3. Configure your authorized `LLM_API_KEY`/`LLM_MODEL` privately, or follow the README's [local-model option](../README.md#quick-start-complete-stack). Never commit secrets.
4. Start Docker Desktop and run `docker compose up --build` for the configured-provider stack. The local-model option uses the additional Compose file documented in the README.
5. Open `http://localhost:8080`.
6. Enter your own AWS credentials, bucket and region in the application. Temporary credentials also require a Session Token.

Workflow: connect S3, choose a file/worksheet, inspect the preview, select targets, describe a rule, run, track progress and browse result pages.

## Without local Docker

The real React frontend and Django API can run separately for interface, validation and connection checks. Complete background computation still requires Redis and Spark workers; a web server alone is not the full system.

Initial setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

Terminal one:

```powershell
.\.venv\Scripts\python.exe scripts/local_backend.py
```

Terminal two:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Missing model configuration is reported explicitly, never replaced by fake success.

## VS Code tasks

Use **Terminal > Run Task**:

- `PatternForge: full stack (Docker)` — complete backend and frontend.
- `PatternForge: backend (local)` — local Django API.
- `PatternForge: frontend` — frontend development server.
- `PatternForge: backend tests` — backend checks.
- `PatternForge: frontend check` — TypeScript and production build.

Select `PatternForge: Django` under Run and Debug for backend debugging. The default interpreter is the project's `.venv`.

## Testing without AWS/model resources

The regular CI uses explicitly labelled S3/model fixtures with actual Celery, Redis, PostgreSQL and two-worker Spark services. This establishes development integration, not genuine AWS authorization, genuine model inference or public deployment. Separate real-service evidence is linked from the README; do not relabel fixture tests.

## Before submission

Use the [submission checklist](SUBMISSION.md) and [final requirements audit](../reports/FINAL_REQUIREMENTS.md). Real-AWS tests, HTTPS and an owner-narrated demonstration have since been recorded; assessor repository access and the real-AWS million-row measurement remain separately disclosed limitations.

Keep live keys out of chat, Git, logs and recordings. `.env` and `.venv` are ignored by Git.
