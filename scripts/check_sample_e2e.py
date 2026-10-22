"""Exercise the public app with its explicitly synthetic bucket and genuine processing stack.

Creates only session-owned test connections/jobs; no AWS credentials or AWS resources.
Report contains job IDs and safe aggregate checks, not session cookies or source rows.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--password-file", type=Path)
    parser.add_argument("--report", type=Path, default=Path("reports/local/sample-e2e.json"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if urlparse(base).scheme != "https":
        parser.error("Use the trusted public HTTPS origin. TLS verification is required.")
    checks, jobs = [], []
    started = time.monotonic()

    def verify(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        print(("PASS " if condition else "FAIL ") + name, flush=True)
        if not condition:
            raise AssertionError(name)

    with httpx.Client(base_url=base, timeout=35) as client:

        def request(method, path, body=None, expected=200):
            response = client.request(method, "/api" + path, json=body)
            if response.status_code != expected:
                raise AssertionError(f"{path}: HTTP {response.status_code}: {response.text[:500]}")
            return response.json() if response.content else None

        boot = request("GET", "/bootstrap")
        if boot.get("access_required"):
            if not args.password_file:
                parser.error("The website gate requires --password-file.")
            secret = json.loads(args.password_file.read_text(encoding="utf-8"))["website_access_password"]
            unlocked = client.post(
                "/api/access/unlock",
                json={"password": secret},
                headers={"Origin": base, "X-CSRFToken": boot["csrf_token"]},
            )
            unlocked.raise_for_status()
            boot = request("GET", "/bootstrap")
        verify("Sample source explicitly enabled", boot["sample_bucket_enabled"] is True)
        verify("Server processing ready", request("GET", "/health")["status"] == "ready")
        verify(
            "Sample connection requires CSRF",
            client.post("/api/s3/sample-connection", json={}).status_code == 403,
        )
        client.headers.update({"X-CSRFToken": boot["csrf_token"], "Origin": base})
        connection = request("POST", "/s3/sample-connection", {}, 201)
        verify(
            "Simulated source label and no keys",
            connection["source_type"] == "sample"
            and not {"access_key", "secret_key", "session_token", "ciphertext"} & connection.keys(),
        )
        verify(
            "Repeated connect reuses session connection",
            request("POST", "/s3/sample-connection", {})["id"] == connection["id"],
        )
        files = request("GET", f"/s3/connections/{connection['id']}/files")["files"]
        verify(
            "Six documented sample files", len(files) == 6 and all(item.get("description") for item in files)
        )
        with httpx.Client(base_url=base, timeout=20) as other:
            otherboot = other.get("/api/bootstrap").json()
            if otherboot.get("access_required"):
                other.post(
                    "/api/access/unlock",
                    json={"password": secret},
                    headers={"Origin": base, "X-CSRFToken": otherboot["csrf_token"]},
                ).raise_for_status()
                other.get("/api/bootstrap")
            verify(
                "Other visitor cannot read connection",
                other.get(f"/api/s3/connections/{connection['id']}/files").status_code == 404,
            )
            verify("Other visitor has empty history", other.get("/api/jobs").json()["jobs"] == [])

        def inspect(key, sheet=""):
            return request(
                "POST",
                "/files/inspect",
                {
                    "connection_id": connection["id"],
                    "source_key": key,
                    "sheet": sheet,
                    "delimiter": ",",
                    "encoding": "UTF-8",
                },
                202,
            )

        def wait(job, expected="SUCCESS"):
            deadline = time.monotonic() + 300
            previous_stage = None
            while time.monotonic() < deadline:
                current = request("GET", "/jobs/" + job["id"])
                if current["stage"] != previous_stage:
                    print(current["id"][:8] + " " + current["stage"], flush=True)
                    previous_stage = current["stage"]
                if current["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                    verify("Job reaches " + expected, current["status"] == expected)
                    jobs.append(
                        {
                            "id": current["id"],
                            "kind": current["kind"],
                            "status": current["status"],
                            "source_key": current["source_key"],
                            "source_type": current["source_type"],
                            "metadata": {
                                key: current.get("metadata", {}).get(key)
                                for key in (
                                    "row_count",
                                    "changed_cells",
                                    "cache_hit",
                                    "partitions",
                                    "executor_count",
                                    "spark_seconds",
                                )
                            },
                        }
                    )
                    return current
                time.sleep(2)
            raise AssertionError("Application job exceeded acceptance wait limit")

        for key, code in [
            ("edge-cases/empty.csv", "EMPTY_FILE"),
            ("edge-cases/unsupported.txt", "UNSUPPORTED_FILE"),
            ("../.env", "SAMPLE_NOT_FOUND"),
        ]:
            result = request(
                "POST", "/files/inspect", {"connection_id": connection["id"], "source_key": key}, 400
            )
            verify("Safe input rejection: " + code, result["error"]["code"] == code)
        duplicate = wait(inspect("edge-cases/duplicate-headers.csv"), "FAILED")
        verify("Async duplicate header error", duplicate["error"]["code"] == "DUPLICATE_COLUMNS")
        source = wait(inspect("examples/customers.csv"))
        preview = source["metadata"]["preview"]
        verify("CSV preview and leading zeroes", len(preview) == 100 and preview[0]["ID"] == "000001")
        verify(
            "CSV quotes and multiline",
            preview[2]["Name"] == "Bob, Taylor" and preview[3]["Name"] == "Two\nLines",
        )
        verify("CSV null preserved", preview[9]["Email"] is None)

        def transform(source, operation, columns, prompt, **options):
            body = {
                "connection_id": connection["id"],
                "inspection_id": source["id"],
                "source_key": source["source_key"],
                "sheet": source["metadata"].get("sheet", ""),
                "delimiter": ",",
                "encoding": "UTF-8",
                "operation": operation,
                "target_columns": columns,
                "prompt": prompt,
                **options,
            }
            submitted = request("POST", "/jobs", body, 202)
            verify(
                "Async submit returns queued Job ID",
                submitted["status"] == "QUEUED" and bool(submitted["id"]),
            )
            return wait(submitted)

        replaced = transform(
            source, "regex_replace", ["Email"], "Find email addresses", replacement="[REDACTED]"
        )
        verify(
            "Replace 1,000 rows / 800 changed cells",
            replaced["metadata"]["row_count"] == 1000
            and replaced["metadata"]["changed_cells"] == {"Email": 800},
        )
        verify(
            "Distributed processing / eight partitions",
            replaced["metadata"]["executor_count"] == 2 and replaced["metadata"]["partitions"] == 8,
        )
        all_rows, cursor = [], ""
        while True:
            page = request("GET", f"/jobs/{replaced['id']}/results?limit=100&cursor={cursor}")
            all_rows.extend(page["rows"])
            if not page["next_cursor"]:
                break
            cursor = page["next_cursor"]
        verify("All paginated rows unique", len(all_rows) == len({row["ID"] for row in all_rows}) == 1000)
        by_id = {row["ID"]: row for row in all_rows}
        verify(
            "Actual replacement / unmatched text / null",
            by_id["000002"]["Email"] == "[REDACTED]"
            and by_id["000001"]["Email"] == "not-an-email"
            and by_id["000010"]["Email"] is None,
        )
        extracted = transform(
            source,
            "regex_extract",
            ["Notes"],
            "Extract order IDs beginning with ORD- followed by digits",
            new_column="OrderID",
        )
        page = request("GET", f"/jobs/{extracted['id']}/results?limit=100")
        verify(
            "Actual extraction values",
            all(row["OrderID"] == "ORD-" + str(100000 + int(row["ID"])) for row in page["rows"]),
        )
        normalized = transform(
            source,
            "normalize",
            ["Name"],
            "Trim spaces, collapse repeated whitespace, then convert to lowercase",
        )
        page = request("GET", f"/jobs/{normalized['id']}/results?limit=100")
        expected_names = {1: "alice smith", 2: "\u9648 \u5c0f\u96e8", 3: "bob, taylor", 0: "two lines"}
        verify(
            "Actual normalization / Chinese / newlines",
            all(row["Name"] == expected_names[int(row["ID"]) % 4] for row in page["rows"]),
        )
        cached = transform(
            source, "regex_replace", ["Email"], "Find email addresses", replacement="[REDACTED]"
        )
        verify("Repeated plan uses cache", cached["metadata"]["cache_hit"] is True)

        workbook = wait(inspect("examples/workbook.xlsx"))
        verify(
            "Excel requires explicit worksheet",
            workbook["metadata"]["requires_sheet"] is True
            and workbook["metadata"]["sheets"] == ["Customers", "Orders"],
        )
        excel = wait(inspect("examples/workbook.xlsx", "Customers"))
        verify("Excel preview retains leading zeroes", excel["metadata"]["preview"][0]["ID"] == "000001")
        excel_job = transform(
            excel, "regex_replace", ["Email"], "Find email addresses", replacement="[REDACTED]"
        )
        verify(
            "Excel actual transform: 120 rows / 96 emails",
            excel_job["metadata"]["row_count"] == 120
            and excel_job["metadata"]["changed_cells"] == {"Email": 96},
        )

        large = inspect("examples/large-customers.csv")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            current = request("GET", "/jobs/" + large["id"])
            if current["status"] == "RUNNING":
                break
            if current["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                raise AssertionError("Large inspection finished before running cancellation test")
            time.sleep(0.5)
        verify("Cancel starts with a running task", current["status"] == "RUNNING")
        request("POST", "/jobs/" + large["id"] + "/cancel", {})
        cancelled = wait(large, "CANCELLED")
        verify("Cancelled job has no results", cancelled["result_available"] is False)
        history = request("GET", "/jobs?kind=transform")
        verify(
            "History persists and labels sample provenance",
            history["total"] == 5 and all(job["source_type"] == "sample" for job in history["jobs"]),
        )
        verify(
            "Source unchanged after transforms",
            request("GET", "/jobs/" + source["id"])["metadata"]["preview"] == preview,
        )
        report = {
            "base_url": base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "source_type": "sample",
            "real_aws": False,
            "genuine_model_configured": boot["llm_configured"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "checks": checks,
            "jobs": jobs,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"passed": len(checks), "report": str(args.report), "real_aws": False}), flush=True)


if __name__ == "__main__":
    main()
