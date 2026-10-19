"""Read repository CI status or explicitly dispatch a benchmark; reuse authorized Git credentials safely."""

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default="mingyanc74")
    parser.add_argument("--repo", default="patternforge")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--log-job", type=int)
    parser.add_argument("--dispatch-benchmark", type=int)
    args = parser.parse_args()
    credential = subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol=https\nhost=github.com\nusername={args.owner}\n\n",
        text=True,
        capture_output=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"},
        check=True,
    )
    token = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)["password"]
    base = f"https://api.github.com/repos/{args.owner}/{args.repo}"
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PatternForge-verification",
    }

    def api(path, data=None):
        req = urllib.request.Request(
            base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as result:
                body = result.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"GitHub API returned HTTP {exc.code}; credentials were not printed.") from None

    if args.dispatch_benchmark:
        api(
            "/actions/workflows/ci.yml/dispatches",
            {"ref": "main", "inputs": {"benchmark_rows": str(args.dispatch_benchmark)}},
        )
        print("Dispatched distributed benchmark.")
    elif args.log_job:

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        req = urllib.request.Request(base + f"/actions/jobs/{args.log_job}/logs", headers=headers)
        try:
            result = urllib.request.build_opener(NoRedirect).open(req, timeout=30)
            body = result.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code != 302:
                raise SystemExit(f"Log API returned HTTP {exc.code}.") from None
            # Never forward the GitHub authorization header to a redirected log-storage host.
            with urllib.request.urlopen(exc.headers["Location"], timeout=30) as result:
                body = result.read().decode("utf-8", errors="replace")
        target = Path("reports/local") / f"ci-job-{args.log_job}.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print("\n".join(body.splitlines()[-100:]))
    elif args.run_id:
        result = api(f"/actions/runs/{args.run_id}/jobs")
        print(
            json.dumps(
                [
                    {
                        "id": job["id"],
                        "name": job["name"],
                        "status": job["status"],
                        "conclusion": job["conclusion"],
                        "steps": [
                            {"name": step["name"], "status": step["status"], "conclusion": step["conclusion"]}
                            for step in job.get("steps", [])
                        ],
                    }
                    for job in result["jobs"]
                ],
                indent=2,
            )
        )
    else:
        result = api("/actions/runs?per_page=5")
        print(
            json.dumps(
                [
                    {
                        "id": run["id"],
                        "event": run["event"],
                        "status": run["status"],
                        "conclusion": run["conclusion"],
                        "url": run["html_url"],
                        "sha": run["head_sha"][:8],
                    }
                    for run in result["workflow_runs"]
                ],
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
