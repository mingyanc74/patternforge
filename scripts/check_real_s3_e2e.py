"""Genuine AWS acceptance: existing authorized objects only, no resource provisioning.

Credentials are read from a local private file, never CLI literals or report fields.
An optional operator checkpoint expires ONLY this run's new application connection.
"""

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import boto3
import httpx
from botocore.exceptions import ClientError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--expire-checkpoint", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("reports/local/real-aws-e2e.json"))
    args = parser.parse_args()
    credentials = json.loads(args.credentials_file.read_text(encoding="utf-8"))
    password = json.loads(args.password_file.read_text(encoding="utf-8"))["website_access_password"]
    base = credentials["website"].rstrip("/")
    if base != "https://clearflow-patternforge.australiaeast.cloudapp.azure.com":
        parser.error("Only the authorized HTTPS application origin is permitted.")
    expected = json.loads((args.fixtures / "expected-results.json").read_text(encoding="utf-8"))
    with (args.fixtures / "test_data.csv").open(encoding="utf-8", newline="") as handle:
        originals = {
            row["ID"]: {key: None if value == "\\N" else value for key, value in row.items()}
            for row in csv.DictReader(handle)
        }
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "real_aws": False,
        "all_executed_checks_passed": False,
        "stage_1_complete": False,
        "bucket": credentials["bucket"],
        "region": credentials["region"],
        "checks": [],
        "aws_objects": [],
        "jobs": [],
        "web_latency_seconds_during_processing": [],
        "limitations": [
            "API acceptance is separate from browser evidence.",
            "No large-dataset, second authorized bucket or injected retry-fault test in this run.",
            "ListAllMyBuckets denial proves limited SDK permission, not a website connection denial to another existing bucket.",
        ],
    }
    started = time.monotonic()

    def save():
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def check(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        print(("PASS " if condition else "FAIL ") + name, flush=True)
        save()
        if not condition:
            raise AssertionError(name)

    try:
        s3 = boto3.client(
            "s3", region_name=credentials["region"],
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            aws_session_token=credentials.get("session_token") or None,
        )
        host = urlparse(s3.meta.endpoint_url).hostname or ""
        check("SDK targets genuine Amazon AWS endpoint", host.endswith(".amazonaws.com"))
        for fixture in expected["files"]:
            result = s3.get_object(Bucket=credentials["bucket"], Key=fixture["name"])
            with result["Body"] as body:
                content = body.read()
            digest = hashlib.sha256(content).hexdigest()
            check(f"AWS bytes match local fixture: {fixture['name']}", digest == fixture["sha256"])
            report["aws_objects"].append({
                "key": fixture["name"], "bytes": len(content), "sha256": digest,
                "etag": result.get("ETag"), "version_id": result.get("VersionId"),
                "aws_request_id": result["ResponseMetadata"]["RequestId"],
            })
        report["real_aws"] = True
        try:
            s3.list_buckets()
            denied = False
        except ClientError as error:
            denied = error.response["Error"]["Code"] in {"AccessDenied", "403"}
        check("Read-only identity cannot enumerate all account buckets (SDK)", denied)

        with httpx.Client(base_url=base, timeout=35) as client:
            def request(method, path, body=None, status=200):
                response = client.request(method, "/api" + path, json=body)
                if response.status_code != status:
                    code = response.json().get("error", {}).get("code", "HTTP_ERROR")
                    raise AssertionError(f"{path}: HTTP {response.status_code}, code={code}")
                return response.json() if response.content else None

            def unlock(visitor):
                boot = visitor.get("/api/bootstrap").json()
                visitor.headers.update({"Origin": base, "X-CSRFToken": boot["csrf_token"]})
                if boot.get("access_required"):
                    opened = visitor.post("/api/access/unlock", json={"password": password})
                    opened.raise_for_status()
                    visitor.headers["X-CSRFToken"] = opened.json()["csrf_token"]
                return visitor.get("/api/bootstrap").json()

            check("Website gate blocks dataset API", client.get("/api/datasets").status_code == 403)
            boot = unlock(client)
            check("Connection/dataset lifetimes 1/24 hours", boot["limits"]["credential_ttl_hours"] == 1 and boot["limits"]["dataset_ttl_hours"] == 24)
            check("Database, queue, worker, Spark and model configured", request("GET", "/health")["status"] == "ready")
            connection_body = {key: credentials.get(key, "") for key in ("access_key", "secret_key", "session_token", "bucket", "region")}
            connection = request("POST", "/s3/connections", connection_body, 201)
            report["connection_id"] = connection["id"]
            check("Application connection is amazon_s3, never sample", connection["source_type"] == "amazon_s3")
            files = request("GET", f"/s3/connections/{connection['id']}/files")["files"]
            check("Both real AWS files are listed and selectable", {"test_data.csv", "test_data.xlsx"} <= {item["key"] for item in files if item["supported"]})
            for name, changes in [
                ("Incorrect real-signature credentials", {"secret_key": ("A" if connection_body["secret_key"][0] != "A" else "B") + connection_body["secret_key"][1:]}),
                ("Nonexistent bucket", {"bucket": credentials["bucket"] + "-missing"}),
            ]:
                error = request("POST", "/s3/connections", {**connection_body, **changes}, 400)
                check(name + " safely rejected by real AWS", error["error"]["code"] in {"S3_CREDENTIALS_INVALID", "S3_ACCESS_DENIED", "S3_NOT_FOUND", "S3_REQUEST_FAILED"})

            def wait(submitted, terminal="SUCCESS"):
                states, deadline = [], time.monotonic() + 360
                while time.monotonic() < deadline:
                    current = request("GET", "/jobs/" + submitted["id"])
                    state = {key: current[key] for key in ("status", "stage", "progress", "attempt")}
                    if not states or states[-1] != state:
                        states.append(state)
                        print(current["id"][:8] + " " + current["stage"], flush=True)
                    if current["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                        report["jobs"].append({
                            "id": current["id"], "kind": current["kind"], "operation": current.get("operation"),
                            "source_key": current["source_key"], "source_type": current["source_type"],
                            "status": current["status"], "states": states,
                            "created_at": current["created_at"], "started_at": current["started_at"], "finished_at": current["finished_at"],
                            "dataset_expires_at": current.get("dataset_expires_at"), "input_dataset_id": current.get("input_dataset_id"),
                            "plan": current.get("plan"), "error": current.get("error"),
                            "metadata": {key: current.get("metadata", {}).get(key) for key in ("row_count", "changed_cells", "cache_hit", "partitions", "executor_count", "spark_seconds", "import_sha256")},
                        })
                        check("Persisted task reaches " + terminal, current["status"] == terminal)
                        return current
                    before = time.monotonic()
                    health = request("GET", "/health")
                    report["web_latency_seconds_during_processing"].append(round(time.monotonic() - before, 4))
                    check_ready = health["status"] == "ready"
                    if not check_ready:
                        print("NOTICE dependency readiness changed during task", flush=True)
                    time.sleep(2)
                raise AssertionError("Acceptance task wait timed out")

            def inspect(key, sheet=""):
                return wait(request("POST", "/files/inspect", {"connection_id": connection["id"], "source_key": key, "delimiter": ",", "encoding": "UTF-8", "sheet": sheet}, 202))

            def transform(source, operation, columns, prompt, **options):
                submitted = request("POST", "/jobs", {
                    "connection_id": connection["id"], "inspection_id": source["id"], "source_key": source["source_key"],
                    "sheet": source["metadata"].get("sheet", ""), "delimiter": ",", "encoding": "UTF-8",
                    "operation": operation, "target_columns": columns, "prompt": prompt, **options,
                }, 202)
                check("HTTP submission immediately returns queued task", submitted["status"] == "QUEUED")
                return wait(submitted)

            def rows(job):
                values, cursor, pages = [], "", 0
                while True:
                    page = request("GET", f"/jobs/{job['id']}/results?limit=100&cursor={cursor}")
                    values.extend(page["rows"])
                    pages += 1
                    if not page["next_cursor"]:
                        break
                    cursor = page["next_cursor"]
                check("Ten complete pages / 1000 unique IDs", pages == 10 and len(values) == len({row["ID"] for row in values}) == 1000)
                return values

            imported = []
            for key in ("test_data.csv", "test_data.xlsx"):
                source = inspect(key, "TestData" if key.endswith(".xlsx") else "")
                imported.append(source)
                digest = next(item["sha256"] for item in expected["files"] if item["name"] == key)
                check("Independent snapshot equals AWS object bytes: " + key, source["dataset_available"] and source["metadata"]["import_sha256"] == digest)
                replaced = transform(source, "regex_replace", ["Email"], expected["prompts"]["replacement"], replacement="[REDACTED]")
                check("Real replace counts / two Spark executors / eight partitions", replaced["metadata"]["row_count"] == 1000 and replaced["metadata"]["changed_cells"] == {"Email": 800} and replaced["metadata"]["executor_count"] == 2 and replaced["metadata"]["partitions"] == 8)
                check("Every replacement matches independent source", all(row["Email"] == ("[REDACTED]" if originals[row["ID"]]["Email"] and "@" in originals[row["ID"]]["Email"] else originals[row["ID"]]["Email"]) for row in rows(replaced)))
                extracted = transform(source, "regex_extract", ["Notes"], expected["prompts"]["extraction"], new_column="OrderID")
                values = rows(extracted)
                check("Every extracted identifier / null is correct", all(row["OrderID"] == (match.group(0) if (match := re.search(r"ORD-[0-9]+", originals[row["ID"]]["Notes"])) else None) for row in values))
                check("Extraction 900 non-null / 100 null", sum(row["OrderID"] is not None for row in values) == 900)
                normalized = transform(source, "normalize", ["Name", "Status"], expected["prompts"]["normalization"])
                check("Multi-column normalization changes 1000 cells each", normalized["metadata"]["changed_cells"] == {"Name": 1000, "Status": 1000})
                check("Every normalized value matches independent calculation", all(row[column] == re.sub(r"\s+", " ", originals[row["ID"]][column].strip()).lower() for row in rows(normalized) for column in ("Name", "Status")))

            multi = transform(imported[0], "regex_replace", ["Email", "BackupEmail"], expected["prompts"]["replacement"], replacement="[REDACTED]")
            check("Multi-column email replacement 800 / 700", multi["metadata"]["changed_cells"] == {"Email": 800, "BackupEmail": 700})
            cached = transform(imported[0], "regex_replace", ["Email"], expected["prompts"]["replacement"], replacement="[REDACTED]")
            check("Repeated validated plan uses Redis cache", cached["metadata"]["cache_hit"] is True)
            listed = request("GET", "/datasets")["datasets"]
            check("Both retained datasets listed", {source["id"] for source in imported} <= {item["id"] for item in listed})

            if args.expire_checkpoint:
                print("EXPIRE_REAL_TEST_CONNECTION=" + connection["id"], flush=True)
                print("Waiting 180 seconds for operator to expire ONLY this run's application connection.", flush=True)
                for _ in range(90):
                    response = client.get(f"/api/s3/connections/{connection['id']}/files")
                    if response.status_code == 410:
                        break
                    response.raise_for_status()
                    time.sleep(2)
                check("Expired real connection cannot list new files", response.status_code == 410)
                request("POST", "/files/inspect", {"connection_id": connection["id"], "source_key": "test_data.csv"}, 410)
                check("Expired real connection cannot import new files", True)
                for source in imported:
                    result = transform(source, "regex_replace", ["Email"], expected["prompts"]["replacement"], replacement="AFTER_EXPIRY")
                    check("Snapshot still processes after connection expiry: " + source["source_key"], result["input_dataset_id"] == source["id"] and result["metadata"]["changed_cells"] == {"Email": 800})
                    check("Dataset retention unchanged by connection expiry", request("GET", "/jobs/" + source["id"])["dataset_expires_at"] == source["dataset_expires_at"])
                report["expiry_test"] = "Accelerated application connection expiry, not elapsed one-hour or natural STS expiration."

            with httpx.Client(base_url=base, timeout=35) as other:
                unlock(other)
                check("Different browser session cannot access dataset", other.get("/api/datasets").json()["datasets"] == [] and other.get("/api/jobs/" + imported[0]["id"]).status_code == 404)
            for item in report["aws_objects"]:
                after = s3.head_object(Bucket=credentials["bucket"], Key=item["key"])
                check("Original AWS object unchanged: " + item["key"], after["ETag"] == item["etag"] and after["ContentLength"] == item["bytes"])
            report["all_executed_checks_passed"] = True
    except Exception as error:
        # Deliberately avoid raw client exception bodies/configuration or credential values.
        report["run_error"] = {"type": type(error).__name__, "message": str(error) if isinstance(error, AssertionError) else "External operation failed; inspect privately without disclosing credentials."}
        raise SystemExit("Acceptance stopped; consult the safe report. Credentials were not printed.") from None
    finally:
        save()
        print(json.dumps({"report": str(args.report), "real_aws": report["real_aws"], "checks": len(report["checks"]), "executed_checks_passed": report["all_executed_checks_passed"]}), flush=True)


if __name__ == "__main__":
    main()
