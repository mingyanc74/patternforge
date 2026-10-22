# Independent cloud deployment and acceptance

This is a reproducible deployment checklist. On 2026-10-21 (Sydney), the user-approved full stack started on the Azure student-credit VM with externally trusted HTTPS. A later single-source SSH update was also approved. See [deployment evidence](AZURE_ACCEPTANCE.md). Real S3 workflows and the narrated video were subsequently completed separately; health alone is never full PDF acceptance. Consult the [final audit](../reports/FINAL_REQUIREMENTS.md) for remaining limits.

## 1. Confirm account eligibility and host configuration

- Check the active Azure for Students plan against the [student-credit plan](AZURE_STUDENT.md): size, region, capacity and costs. Account activation alone does not create a VM.
- No card or paid upgrade; use only approved student credit, without extra paid add-ons. Finite credit is not permanent free hosting. Confirm before creating resources.
- Current target: one Ubuntu x64 host, 4 vCPU/16 GiB and an appropriately sized Standard SSD. Keep at least 20 GiB free before the initial build and monitor later image/data/result growth. Full ARM deployment is not verified.
- Use your SSH public key and retain its private key locally. Restrict SSH to your source IP; expose website TCP 80/443 (optional HTTP/3 UDP 443), not database/Redis/Spark/model/Flower.
- Check cloud rules and host firewall together. Docker-published ports may bypass ordinary firewall expectations; one firewall screen is insufficient.
- Use a controlled existing/free DNS hostname with A pointing to the public IPv4 and correct AAAA if present. The HTTPS configuration requires a DNS name, not a bare-IP certificate workaround.

## 2. Prepare source and private configuration

Install Docker Engine/Compose v2, Git and Python 3.11+ using their official instructions. The model-download script requires Python 3.11+; do not assume an older system Python suffices. Clone the private repository once, authenticating securely without tokens in command URLs, chat, README or images.

In the repository:

```sh
python3 scripts/bootstrap.py
python3 scripts/free_model.py --download-only
```

Bootstrap never overwrites `.env` or prints secrets. Privately set `DOMAIN=<your-actual-dns-hostname>` in the server's `.env`, and verify:

```dotenv
DJANGO_DEBUG=0
SESSION_COOKIE_SECURE=1
SECURE_SSL_REDIRECT=1
S3_ENDPOINT_URL=
S3_ALLOW_HTTP=0
```

The production overlay also forces secure cookies, disables debug and sets exact hosts/CSRF origins. `compose.local-model.yml` supplies the internal model URL without a paid model key. Never use `compose.ci.yml` for genuine AWS acceptance; it contains fixtures.

Keep `.env`/data out of GitHub. Protect database backups and `CREDENTIAL_KEY`; losing it makes stored AWS credentials undecryptable. Do not regenerate it casually.

## 3. Preflight and startup

```sh
python3 scripts/cloud_preflight.py
docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml up -d --build --wait --wait-timeout 600
docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml ps
```

Preflight reads configuration, Docker, RAM and disk without printing secret values, modifying resources or deploying. It does not certify credit, ARM, DNS, certificates or actual AWS.

Public DNS must resolve and 80/443 must be reachable. Persist Caddy's certificate volume. Investigate DNS/ports if issuance fails; never disable certificate verification or enter AWS secrets over plaintext HTTP.

## 4. Real-service acceptance order

1. Open `https://<your-hostname>` from another computer or mobile network and verify the browser certificate, not merely server-local access.
2. Check `/api/health` for database/queue/worker/model configuration; diagnostic readiness does not replace completed tasks.
3. Run genuine-model semantics in the worker:

   ```sh
   docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml exec -T worker python - --report /data/model-evaluation.json < scripts/evaluate_model.py
   ```

4. Establish a fresh connection in the webpage using an authorized real bucket and least-privilege read-only credentials. Exclude secrets from chat, screenshots and video. A protocol fixture is not AWS.
5. CSV preview, replacement, success and at least two result pages; verify literal replacements, null/no-match behavior, rows and changed-cell counts.
6. Test Excel sheets, extraction, normalization, refresh recovery, history, connection expiry, failure messages and actual running cancellation.
7. Verify two executors/multiple effective partitions. Record actual Azure SKU, memory and timings; CI timings are not cloud-host measurements.
8. Follow [submission instructions](SUBMISSION.md), publish the real demo/URL in README and grant the actual assessor private-repository access.

## 5. Operations and recovery

Use synthetic content for initial imports, not sensitive business data. Current defaults are **one-hour S3 connections**, **24-hour imported datasets** and **24-hour results**; confirm these suit review timing. Source S3 objects remain read-only. Browser sessions isolate this assessment version, without cross-device account synchronization. Public visitors can consume compute; monitor queues and review availability.

Back up PostgreSQL, result volumes and separately protected encryption keys. Stop containers while preserving data:

```sh
docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml down
```

Do not add `-v`, which deletes persistent volumes. Stopping containers does not deallocate the VM or stop all disk/IP costs. Monitor review timing, credit and student-plan expiry; uninterrupted availability is not guaranteed forever.

Flower binds only to server loopback. Access via your own SSH forwarding, never a public monitoring port. Redact logs before sharing, including filenames/prompts. Do not capture commands that dump complete `.env`/Compose environments.
