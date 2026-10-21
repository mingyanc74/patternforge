# Rulecraft UI refresh — 2026-10-22

The user requested a more polished interface, then asked to combine the first refresh with the original Clearflow UI. Application UI commit: `608f62bf`. Backend remains the previously accepted `049cae7f`; API contracts, credentials, storage, jobs and data volumes were not replaced.

## Delivered

- User-facing name **Rulecraft**; repository and existing HTTPS hostname unchanged.
- Original light/blue workbench and clear five-stage workflow, combined with self-hosted Manrope typography, softer navigation, consistent fields/buttons, refined tables and selected-column treatment.
- Refreshed gate, connection guide, dataset cards, job history, configuration, progress, results and dialogs. Sample-source warnings remain explicit; no fake job/metric data added to production.
- Source preview column headers now select targets using the same handler as the existing checkbox/radio list. Browser verification confirmed synchronized selection, multi-column replacement and single-column extraction.
- Source preview height reduced on narrow layouts so controls are easier to reach. Local iframe QA at actual 375px and 753px viewport widths showed no whole-page horizontal overflow for the gate and result views; tables retain internal scrolling. These fixtures were visual/development checks, **not** AWS acceptance.
- Local production build and all five existing frontend tests passed. The font and its SIL OFL are served from the application origin.

## Deployment and live verification

Only the frontend source was uploaded to the existing Azure VM. A recoverable frontend source archive was created before replacement. The frontend container rebuilt successfully; Nginx configuration passed. No backend container restart, migration, AWS policy expansion, data-volume replacement or website-password change was part of this UI deployment. A separate, explicitly user-approved SSH source /32 replacement restored management access; it did not expose SSH to the Internet generally.

The first deployment command was rejected before execution because permission review timed out. One permitted retry executed successfully with `rulecraft_ui_update_exit=0`. Do not label the first attempt a successful deployment.

`scripts/check_cloud_http.py` passed **28/28** external checks against the new live website, including the Rulecraft page, favicon, self-hosted font, trusted HTTPS/security headers, password gate, CSRF, session isolation and processing health. This check does not submit AWS jobs.

All three [CI jobs for UI commit 608f62bf](https://github.com/mingyanc74/patternforge/actions/runs/39675266725) completed successfully: frontend, backend/Java/Spark tests and the development-only distributed fixture stack. The latter is not real-AWS evidence. All 12 production services remained running after the frontend-only replacement.

The actual browser separately opened a previously imported **real Amazon S3 CSV snapshot**, clicked Email in the new column header, reviewed the real prompt/replacement and submitted job `b1ce7228-7164-4ad8-9fbb-7bbb52369b44`. It reached SUCCESS with **1,000 rows / 800 Email changes / two Spark executors / eight partitions**, Spark time **11.139 seconds**. The plan was a Redis cache hit; this UI regression is not a new uncached model-quality evaluation. See [read-only task metadata](UI_REAL_JOB.json).

The actual result UI's Next action displayed rows **101–200 / Page 2**. Lock workspace returned to the new password screen; the existing private password unlocked it again. No new password was created or published.

### Additional natural-expiry observation

This browser's real connection was created at `2026-10-21T11:16:22.916850Z` and expired at `2026-10-21T12:16:22.916548Z`, an original lifetime of approximately 3,600 seconds. The new UI task was submitted at `2026-10-21T21:06:58.985622Z` (2026-10-22 Sydney), almost nine hours **after** that connection expired. It is not the earlier accelerated-expiry test connection. Its retained input SHA-256 still equals the uploaded AWS CSV, and the dataset remains valid until `2026-10-22T11:17:25.163461Z`.

This adds an actual post-natural-expiry snapshot processing observation to the prior accelerated test. It does not mean an STS token expired, that the same source was newly fetched from AWS after expiry, or that continuous 24-hour observation is complete. This regression intentionally uses the retained snapshot rather than an expired connection to import new data.

Local proof images are in sibling `outputs/rulecraft-ui/`; they are not added to the public assets or Git source. The final result page is real, not the development fixture.

## Development dependency notice

The build reported three existing dependency audit findings: one moderate and two critical, all in the Vitest development/test dependency tree (`vitest`, `@vitest/mocker`, `tinypool`). A separate `npm audit --omit=dev` reported **zero** known production dependency findings at this check. The deployed final Nginx image contains built frontend resources, not the Node/Vitest test server. This is not a claim that all development tooling is risk-free; do not expose the Vitest server or run untrusted test code.

The proposed audit remediation crosses a major test-tool version. It was not forced into this styling change with `npm audit fix --force`; schedule a separate compatible tooling update and rerun tests. References: [Vitest advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9), [Tinypool worker-options advisory](https://github.com/advisories/GHSA-5gmw-xhrv-c9v3), [Tinypool run-options advisory](https://github.com/advisories/GHSA-85c8-ppgw-ccpr).
