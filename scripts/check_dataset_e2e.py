"""Live gate + import-lifetime acceptance, synthetic source, genuine queue/model/Spark.

At the printed checkpoint, an operator expires ONLY this newly created sample
connection server-side. The HTTP client keeps its session in memory throughout.
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("reports/local/dataset-access-e2e.json"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if urlparse(base).scheme != "https":
        parser.error("Verified HTTPS required.")
    secret = json.loads(args.password_file.read_text(encoding="utf-8"))["website_access_password"]
    checks = []

    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
        print(("PASS " if passed else "FAIL ") + name, flush=True)
        if not passed:
            raise AssertionError(name)

    with httpx.Client(base_url=base, timeout=35) as client:

        def call(method, path, body=None, status=200):
            result = client.request(method, "/api" + path, json=body)
            if result.status_code != status:
                raise AssertionError(f"{path}: HTTP {result.status_code}: {result.text[:300]}")
            return result.json() if result.content else None

        boot = call("GET", "/bootstrap")
        check("Website gate required", boot["access_required"])
        check("Dataset API protected before unlock", client.get("/api/datasets").status_code == 403)
        client.headers.update({"Origin": base, "X-CSRFToken": boot["csrf_token"]})
        opened = call("POST", "/access/unlock", {"password": secret})
        client.headers["X-CSRFToken"] = opened["csrf_token"]
        boot = call("GET", "/bootstrap")
        check(
            "Gate distinct from AWS connection",
            not boot["access_required"] and call("GET", "/s3/connections")["connections"] == [],
        )
        check("Connection lifetime one hour", boot["limits"]["credential_ttl_hours"] == 1)
        check("Dataset retention independent", boot["limits"]["dataset_ttl_hours"] == 24)
        source = call("POST", "/s3/sample-connection", {}, 201)

        def wait(job):
            for _ in range(150):
                result = call("GET", "/jobs/" + job["id"])
                if result["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                    check("Persisted job succeeds", result["status"] == "SUCCESS")
                    return result
                time.sleep(2)
            raise AssertionError("Job timeout")

        inspect = wait(
            call(
                "POST",
                "/files/inspect",
                {"connection_id": source["id"], "source_key": "examples/customers.csv"},
                202,
            )
        )
        check(
            "Private imported snapshot published",
            inspect["dataset_available"] and len(inspect["metadata"]["import_sha256"]) == 64,
        )
        print("EXPIRE_TEST_CONNECTION=" + source["id"], flush=True)
        print("Waiting up to 180 seconds for operator to expire only this test connection.", flush=True)
        for _ in range(90):
            response = client.get(f"/api/s3/connections/{source['id']}/files")
            if response.status_code == 410:
                break
            response.raise_for_status()
            time.sleep(2)
        check("Expired connection blocks browsing", response.status_code == 410)
        call(
            "POST",
            "/files/inspect",
            {"connection_id": source["id"], "source_key": "examples/customers.csv"},
            410,
        )
        check(
            "Retained dataset remains listed",
            any(item["id"] == inspect["id"] for item in call("GET", "/datasets")["datasets"]),
        )

        def transform(replacement):
            return wait(
                call(
                    "POST",
                    "/jobs",
                    {
                        "connection_id": source["id"],
                        "source_key": inspect["source_key"],
                        "inspection_id": inspect["id"],
                        "operation": "regex_replace",
                        "target_columns": ["Email"],
                        "prompt": "Find email addresses",
                        "replacement": replacement,
                    },
                    202,
                )
            )

        first = transform("[REDACTED]")
        check(
            "Expired connection does not block processing",
            first["metadata"]["row_count"] == 1000 and first["metadata"]["changed_cells"] == {"Email": 800},
        )
        check("Snapshot reference persisted", first["input_dataset_id"] == inspect["id"])
        check(
            "Real distributed Spark",
            first["metadata"]["executor_count"] == 2 and first["metadata"]["partitions"] == 8,
        )
        call("DELETE", "/s3/connections/" + source["id"], status=204)
        second = transform("[MASKED]")
        check(
            "Disconnected source still processes snapshot",
            second["metadata"]["changed_cells"] == {"Email": 800},
        )
        page = call("GET", f"/jobs/{second['id']}/results?limit=100")
        check(
            "Results readable and correctly transformed",
            page["total_rows"] == 1000
            and all(row["Email"] in {None, "not-an-email", "[MASKED]"} for row in page["rows"]),
        )
        check(
            "Original imported preview unchanged",
            call("GET", "/jobs/" + inspect["id"])["metadata"]["preview"] == inspect["metadata"]["preview"],
        )
        with httpx.Client(base_url=base, timeout=20) as other:
            otherboot = other.get("/api/bootstrap").json()
            result = other.post(
                "/api/access/unlock",
                json={"password": secret},
                headers={"Origin": base, "X-CSRFToken": otherboot["csrf_token"]},
            )
            result.raise_for_status()
            check(
                "Shared entrance does not share workspaces",
                other.get("/api/datasets").json()["datasets"] == [],
            )
            check(
                "Other visitor cannot read imported data",
                other.get("/api/jobs/" + inspect["id"]).status_code == 404,
            )
        call("POST", "/access/lock", {})
        check("Lock blocks result API", client.get(f"/api/jobs/{second['id']}/results").status_code == 403)
        report = {
            "real_aws": False,
            "source_type": "sample",
            "base_url": base,
            "checks": checks,
            "inspection_id": inspect["id"],
            "transform_ids": [first["id"], second["id"]],
            "metadata": [first["metadata"], second["metadata"]],
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"PASS {len(checks)} checks; real_aws=false; report saved.", flush=True)


if __name__ == "__main__":
    main()
