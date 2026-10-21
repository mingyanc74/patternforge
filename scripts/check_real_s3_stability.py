"""Second-stage genuine S3 tests. Never provision or modify AWS resources.

Retry uses an explicitly labelled, single-job fault-injection checkpoint; its
successful retry must read real AWS bytes and execute the genuine Spark worker.
"""

import argparse
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--other-bucket", required=True)
    parser.add_argument("--retry-checkpoint", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("reports/local/real-aws-stability.json"))
    args = parser.parse_args()
    private = json.loads(args.credentials_file.read_text(encoding="utf-8"))
    password = json.loads(args.password_file.read_text(encoding="utf-8"))["website_access_password"]
    base = private["website"].rstrip("/")
    assert base == "https://clearflow-patternforge.australiaeast.cloudapp.azure.com"
    assert args.other_bucket == "patternforge-control-20261021-a7f4c2"
    large = json.loads((args.fixtures / "large_test_data.manifest.json").read_text(encoding="utf-8"))
    fixtures = json.loads((args.fixtures / "expected-results.json").read_text(encoding="utf-8"))
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "real_aws": True,
        "checks": [], "jobs": [], "processing_http_latencies_seconds": [],
        "buckets": [private["bucket"], args.other_bucket], "aws_objects": [],
        "all_executed_checks_passed": False,
        "retry_method": "Not executed unless explicit single-job fault-injection checkpoint is completed.",
    }
    started = time.monotonic()

    def save():
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def check(name, passed):
        report["checks"].append({"name": name, "passed": bool(passed)})
        print(("PASS " if passed else "FAIL ") + name, flush=True)
        save()
        if not passed:
            raise AssertionError(name)

    try:
        s3 = boto3.client("s3", region_name=private["region"], aws_access_key_id=private["access_key"], aws_secret_access_key=private["secret_key"])
        for key, expected_hash in [("test_data.csv", fixtures["files"][0]["sha256"]), (large["name"], large["sha256"])]:
            response = s3.get_object(Bucket=args.other_bucket, Key=key)
            with response["Body"] as body:
                raw = body.read()
            digest = hashlib.sha256(raw).hexdigest()
            check("Second bucket genuine AWS object matches local file: " + key, digest == expected_hash)
            report["aws_objects"].append({"bucket": args.other_bucket, "key": key, "bytes": len(raw), "sha256": digest, "etag": response["ETag"], "aws_request_id": response["ResponseMetadata"]["RequestId"]})

        with httpx.Client(base_url=base, timeout=35) as client:
            boot = client.get("/api/bootstrap").json()
            client.headers.update({"Origin": base, "X-CSRFToken": boot["csrf_token"]})
            unlocked = client.post("/api/access/unlock", json={"password": password})
            unlocked.raise_for_status()
            client.headers["X-CSRFToken"] = unlocked.json()["csrf_token"]

            def request(method, path, body=None, status=200):
                response = client.request(method, "/api" + path, json=body)
                if response.status_code != status:
                    code = response.json().get("error", {}).get("code", "HTTP_ERROR")
                    raise AssertionError(f"{path}: HTTP {response.status_code}, code={code}")
                return response.json() if response.content else None

            def connect(bucket):
                value = {key: private.get(key, "") for key in ("access_key", "secret_key", "session_token", "region")}
                value["bucket"] = bucket
                return request("POST", "/s3/connections", value, 201)

            first, second = connect(private["bucket"]), connect(args.other_bucket)
            report["connection_ids"] = [first["id"], second["id"]]
            check("Same application accepts two different real AWS buckets", first["bucket"] != second["bucket"] and first["source_type"] == second["source_type"] == "amazon_s3")
            files = request("GET", f"/s3/connections/{second['id']}/files")["files"]
            check("Second bucket lists copied CSV and larger CSV", {"test_data.csv", large["name"]} <= {item["key"] for item in files})

            def wait(job, terminal="SUCCESS"):
                began, states = time.monotonic(), []
                while time.monotonic() - began < 420:
                    value = request("GET", "/jobs/" + job["id"])
                    state = {key: value[key] for key in ("status", "stage", "progress", "attempt")}
                    if not states or states[-1] != state:
                        states.append(state)
                        print(value["id"][:8] + " " + value["stage"], flush=True)
                    if value["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                        report["jobs"].append({
                            "id": value["id"], "kind": value["kind"], "source_key": value["source_key"], "bucket": value["bucket"],
                            "source_type": value["source_type"], "status": value["status"], "expected_status": terminal,
                            "attempt": value["attempt"], "states": states, "observed_wait_seconds": round(time.monotonic() - began, 3),
                            "created_at": value["created_at"], "started_at": value["started_at"], "finished_at": value["finished_at"],
                            "metadata": {key: value.get("metadata", {}).get(key) for key in ("row_count", "changed_cells", "cache_hit", "partitions", "executor_count", "spark_seconds", "import_sha256")},
                            "error": value.get("error"),
                        })
                        check("Task reaches expected " + terminal, value["status"] == terminal)
                        return value
                    before = time.monotonic()
                    request("GET", "/jobs?kind=transform&limit=1")
                    request("GET", "/health")
                    report["processing_http_latencies_seconds"].append(round(time.monotonic() - before, 4))
                    time.sleep(1)
                raise AssertionError("Task wait exceeded stability limit")

            def inspect(connection, key, sheet="", terminal="SUCCESS"):
                job = request("POST", "/files/inspect", {"connection_id": connection["id"], "source_key": key, "sheet": sheet, "delimiter": ",", "encoding": "UTF-8"}, 202)
                return wait(job, terminal)

            def submit(source, connection):
                return request("POST", "/jobs", {
                    "connection_id": connection["id"], "inspection_id": source["id"], "source_key": source["source_key"],
                    "sheet": "", "delimiter": ",", "encoding": "UTF-8", "operation": "regex_replace",
                    "target_columns": ["Email"], "prompt": "Find email addresses", "replacement": "[REDACTED]",
                }, 202)

            other_source = inspect(second, "test_data.csv")
            other_result = wait(submit(other_source, second))
            check("Different bucket real import and transform succeed", other_source["metadata"]["import_sha256"] == fixtures["files"][0]["sha256"] and other_result["metadata"]["changed_cells"] == {"Email": 800})
            source = inspect(second, large["name"])
            check("Large snapshot matches genuine S3 bytes", source["metadata"]["import_sha256"] == large["sha256"])
            result = wait(submit(source, second))
            check("Actual larger workload: 50000 rows / 40000 changed cells", result["metadata"]["row_count"] == 50000 and result["metadata"]["changed_cells"] == {"Email": 40000})
            check("Larger workload distributed over two executors / eight partitions", result["metadata"]["executor_count"] == 2 and result["metadata"]["partitions"] == 8)
            identifiers, total, pages, cursor, redacted = set(), 0, 0, "", 0
            while True:
                page = request("GET", f"/jobs/{result['id']}/results?limit=500&cursor={cursor}")
                identifiers.update(row["ID"] for row in page["rows"])
                redacted += sum(row["Email"] == "[REDACTED]" for row in page["rows"])
                total += len(page["rows"])
                pages += 1
                if not page["next_cursor"]:
                    break
                cursor = page["next_cursor"]
            check("All 50000 larger result rows paged without duplicates", len(identifiers) == total == 50000 and pages == 100 and redacted == 40000)
            check("Website remains responsive during background processing", bool(report["processing_http_latencies_seconds"]) and max(report["processing_http_latencies_seconds"]) < 5)

            cancelled = submit(source, second)
            for _ in range(120):
                state = request("GET", "/jobs/" + cancelled["id"])
                if state["status"] == "RUNNING":
                    break
                if state["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                    raise AssertionError("Cancellation task finished before RUNNING could be observed")
                time.sleep(0.25)
            check("Cancel is requested on an actually running task", state["status"] == "RUNNING")
            request("POST", "/jobs/" + cancelled["id"] + "/cancel", {})
            stopped = wait(cancelled, "CANCELLED")
            check("Cancelled task publishes no partial result", stopped["result_available"] is False)
            bad = inspect(first, "test_data.xlsx", "NoSuchWorksheetForAcceptance", "FAILED")
            check("Genuine AWS file with invalid sheet fails safely", bad["error"]["code"] == "SHEET_NOT_FOUND" and bad["dataset_available"] is False)

            if args.retry_checkpoint:
                retry_id = str(uuid.uuid4())
                print("INJECT_RETRY_CONNECTION=" + first["id"], flush=True)
                print("INJECT_RETRY_JOB=" + retry_id, flush=True)
                print("Waiting 180 seconds for isolated one-attempt fault injection; no successful AWS response may be mocked.", flush=True)
                for _ in range(180):
                    response = client.get("/api/jobs/" + retry_id)
                    if response.status_code == 200:
                        break
                    if response.status_code != 404:
                        response.raise_for_status()
                    time.sleep(1)
                check("Isolated retry test job created", response.status_code == 200)
                retry = wait({"id": retry_id})
                check("Controlled transient failure retried then real S3 succeeds", retry["attempt"] == 2 and retry["metadata"]["import_sha256"] == fixtures["files"][0]["sha256"])
                report["retry_method"] = "First attempt injected S3_TEMPORARY_ERROR in one isolated operator process. Real outbox/Celery retry downloaded genuine AWS bytes and completed Spark. Not a naturally observed AWS outage."
            check("Worker and dependencies ready after failure/cancel/retry", request("GET", "/health")["status"] == "ready")
            report["all_executed_checks_passed"] = True
    except Exception as error:
        report["run_error"] = {"type": type(error).__name__, "message": str(error) if isinstance(error, AssertionError) else "External operation failed; inspect privately without disclosing credentials."}
        raise SystemExit("Stability acceptance stopped; inspect safe report. Credentials were not printed.") from None
    finally:
        save()
        print(json.dumps({"report": str(args.report), "checks": len(report["checks"]), "executed_checks_passed": report["all_executed_checks_passed"]}), flush=True)


if __name__ == "__main__":
    main()
