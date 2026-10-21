"""External HTTPS/session checks. Never accepts AWS credentials or prints cookie values."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--report", type=Path, default=Path("reports/local/cloud-http.json"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if urlparse(base).scheme != "https":
        parser.error("Use the real HTTPS origin; certificate verification is never disabled.")
    checks = []

    def verify(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    with httpx.Client(base_url=base, timeout=20, follow_redirects=False) as client:
        page = client.get("/")
        verify("HTTPS application page", page.status_code == 200 and "Clearflow" in page.text)
        for path in ["/", "/api/health", "/internal/metrics", "/assets/absent-acceptance-check.js"]:
            response = page if path == "/" else client.get(path)
            verify("Framing denied: " + path, response.headers.get("x-frame-options") == "DENY")
            verify(
                "CSP retained: " + path,
                "frame-ancestors 'none'" in response.headers.get("content-security-policy", ""),
            )
            verify(
                "HSTS retained: " + path, "max-age=" in response.headers.get("strict-transport-security", "")
            )
            if path == "/internal/metrics":
                verify("Internal monitoring blocked", response.status_code == 403)
            if path.startswith("/assets/"):
                verify("Missing asset is not SPA HTML", response.status_code == 404)
        asset = re.search(r'src="(/assets/[^\"]+\.js)"', page.text)
        verify("Built JavaScript referenced", asset is not None)
        response = client.get(asset.group(1))
        verify(
            "Built JavaScript served with immutable cache",
            response.status_code == 200 and "immutable" in response.headers.get("cache-control", ""),
        )
        health = client.get("/api/health")
        verify("Processing health ready", health.json()["status"] == "ready")
        bootstrap = client.get("/api/bootstrap")
        verify("API is never publicly cached", "no-store" in bootstrap.headers.get("cache-control", ""))
        cookies = list(client.cookies.jar)
        session = next(cookie for cookie in cookies if cookie.name == "sessionid")
        verify("Secure HTTP-only session cookie", session.secure and session.has_nonstandard_attr("HttpOnly"))
        response = client.post("/api/s3/connections", json={})
        verify("Anonymous state change requires CSRF", response.status_code == 403)
        response = client.post(
            "/api/s3/connections",
            json={},
            headers={"X-CSRFToken": bootstrap.json()["csrf_token"], "Origin": base},
        )
        verify("Missing AWS credentials rejected before connection", response.status_code == 400)
        verify(
            "New session has no preloaded S3 connection",
            client.get("/api/s3/connections").json()["connections"] == [],
        )
        verify("New session has no fabricated jobs", client.get("/api/jobs").json()["jobs"] == [])
        with httpx.Client(base_url=base, timeout=20) as other:
            other.get("/api/bootstrap")
            verify(
                "Guest sessions use distinct cookies",
                other.cookies.get("sessionid") != client.cookies.get("sessionid"),
            )
    report = {
        "base_url": base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "real_aws": False,
        "completed_application_job": False,
        "checks": checks,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} external HTTPS/session checks. No AWS or completed-job claim.")


if __name__ == "__main__":
    main()
