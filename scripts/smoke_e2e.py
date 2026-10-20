"""Exercise the REAL HTTP/Celery/Redis/Spark stack against explicitly synthetic S3/model fixtures."""

import argparse
import csv
import io
import json
import os
import platform
import sys
import time
from pathlib import Path

import boto3
import requests
from openpyxl import Workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--s3-url", default="http://localhost:5000")
    parser.add_argument("--cluster-url", default="http://localhost:8009/cluster")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument(
        "--genuine-model", action="store_true", help="Label a run using the real CPU model overlay"
    )
    parser.add_argument("--report", type=Path, default=Path("reports/local/e2e.json"))
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("rows must be positive")
    started = time.monotonic()

    def cluster():
        response = requests.get(args.cluster_url, timeout=5)
        response.raise_for_status()
        return response.json()

    for _ in range(120):
        try:
            if (
                requests.get(args.base_url + "/api/health", timeout=5).json()["status"] == "ready"
                and cluster()["alive_workers"] >= 2
            ):
                break
        except (requests.RequestException, ValueError, KeyError):
            pass
        time.sleep(1)
    else:
        raise AssertionError("The application did not report ready processing services.")
    s3 = boto3.client(
        "s3",
        endpoint_url=args.s3_url,
        region_name="us-east-1",
        aws_access_key_id="ci-test-user",
        aws_secret_access_key="ci-test-secret",
    )
    bucket = "dynamic-e2e-" + str(int(time.time()))
    s3.create_bucket(Bucket=bucket)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        ["ID", "Name", "Email", "Description", "City", "Country", "Phone", "Status", "Date", "Notes"]
    )
    for i in range(args.rows):
        writer.writerow(
            [
                str(i).zfill(8),
                f"  USER   {i}  ",
                f"user{i}@example.com",
                f"Order ORD-{i} shipped",
                "Sydney",
                "AU",
                "+61 400 123 456",
                "active",
                "2026-10-19",
                "Customer record",
            ]
        )
    s3.put_object(Bucket=bucket, Key="inputs/customers.csv", Body=stream.getvalue().encode())
    book = Workbook()
    book.active.title = "Customers"
    book.active.append(["ID", "Email"])
    book.active.append(["001", "alice@example.com"])
    book.create_sheet("Other").append(["Value"])
    excel = io.BytesIO()
    book.save(excel)
    s3.put_object(Bucket=bucket, Key="inputs/sample.xlsx", Body=excel.getvalue())
    session = requests.Session()
    csrf = session.get(args.base_url + "/api/bootstrap", timeout=10).json()["csrf_token"]
    session.headers.update({"X-CSRFToken": csrf, "Origin": args.base_url.rstrip("/")})

    def request(method, path, body=None, params=None, expected=200):
        response = session.request(
            method, args.base_url + "/api" + path, json=body, params=params, timeout=30
        )
        if response.status_code != expected:
            raise AssertionError(f"{path}: HTTP {response.status_code}: {response.text[:600]}")
        return response.json()

    def wait(job_id, expected_status="SUCCESS"):
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            result = request("GET", "/jobs/" + job_id)
            if result["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                assert result["status"] == expected_status, result.get("error")
                return result
            time.sleep(1)
        raise AssertionError("Job timed out")

    connection = request(
        "POST",
        "/s3/connections",
        {
            "bucket": bucket,
            "access_key": "ci-test-user",
            "secret_key": "ci-test-secret",
            "region": "us-east-1",
        },
        expected=201,
    )
    files = request("GET", f"/s3/connections/{connection['id']}/files", params={"prefix": "inputs/"})
    assert len(files["files"]) == 2
    input_config = {"connection_id": connection["id"], "source_key": "inputs/customers.csv"}
    inspection = wait(request("POST", "/files/inspect", input_config, expected=202)["id"])
    assert inspection["metadata"]["preview"][0]["ID"] == "00000000"
    if args.genuine_model:
        ambiguous = wait(
            request(
                "POST",
                "/jobs",
                {
                    **input_config,
                    "inspection_id": inspection["id"],
                    "operation": "regex_extract",
                    "prompt": "Extract order IDs",
                    "target_columns": ["Description"],
                    "new_column": "unspecified_id",
                },
                expected=202,
            )["id"],
            expected_status="FAILED",
        )
        assert ambiguous["error"]["code"] == "RULE_NEEDS_CLARIFICATION"
        assert not ambiguous["result_available"] and not ambiguous["plan"]
        assert "patternforge-" + ambiguous["id"] not in cluster()["active_application_names"]
    jobs = []
    for operation, prompt, columns, extra in [
        ("regex_replace", "Find email addresses", ["Email"], {"replacement": "$REDACTED"}),
        (
            "regex_extract",
            "Extract order IDs beginning with ORD- followed by digits",
            ["Description"],
            {"new_column": "order_id"},
        ),
        ("normalize", "Trim, collapse whitespace, lowercase names", ["Name"], {}),
    ]:
        submitted = request(
            "POST",
            "/jobs",
            {
                **input_config,
                "inspection_id": inspection["id"],
                "operation": operation,
                "prompt": prompt,
                "target_columns": columns,
                **extra,
            },
            expected=202,
        )
        finished = wait(submitted["id"])
        page = request("GET", "/jobs/" + finished["id"] + "/results", params={"limit": 25})
        # Test-only, generated public samples: retain evidence even if a correctness check fails.
        args.report.parent.mkdir(parents=True, exist_ok=True)
        diagnostic = {
            "status": "incomplete",
            "fixture_notice": "Synthetic S3 and generated sample rows; genuine model"
            if args.genuine_model
            else "Synthetic S3 and deterministic model",
            "completed_operations": jobs,
            "current_operation": operation,
            "generated_plan": finished["plan"],
            "metadata": finished["metadata"],
            "expected_rows_and_changed_cells": args.rows,
            "first_sample_rows": page["rows"][:3],
        }
        args.report.write_text(json.dumps(diagnostic, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "operation": operation,
                    "plan": finished["plan"],
                    "rows": page["total_rows"],
                    "changed_cells": finished["metadata"]["changed_cells"],
                }
            ),
            flush=True,
        )
        assert page["total_rows"] == args.rows and len(page["rows"]) == min(25, args.rows)
        assert finished["metadata"]["partitions"] >= 2
        assert finished["metadata"]["executor_count"] >= 2, "The job must actually use two remote executors."
        assert sum(finished["metadata"]["changed_cells"].values()) == args.rows, (
            operation + ": changed-cell count mismatch; inspect the retained test-only report."
        )
        assert finished["metadata"]["cache_hit"] is False
        for row in page["rows"]:
            assert row["City"] == "Sydney" and row["Status"] == "active"
            if operation == "regex_replace":
                assert row["Email"] == "$REDACTED"
            elif operation == "regex_extract":
                assert row["order_id"] == "ORD-" + str(int(row["ID"]))
            else:
                assert row["Name"] == "user " + str(int(row["ID"]))
        if page["next_cursor"]:
            second = request(
                "GET",
                "/jobs/" + finished["id"] + "/results",
                params={"limit": 25, "cursor": page["next_cursor"]},
            )
            assert not {r["ID"] for r in page["rows"]} & {r["ID"] for r in second["rows"]}
        jobs.append(
            {
                "operation": operation,
                "job_id": finished["id"],
                "row_count": args.rows,
                "spark_seconds": finished["metadata"].get("spark_seconds"),
                "partitions": finished["metadata"]["partitions"],
                "executor_count": finished["metadata"]["executor_count"],
            }
        )
    excel_config = {"connection_id": connection["id"], "source_key": "inputs/sample.xlsx"}
    sheets = wait(request("POST", "/files/inspect", excel_config, expected=202)["id"])
    assert sheets["metadata"]["requires_sheet"]
    selected = wait(
        request("POST", "/files/inspect", {**excel_config, "sheet": "Customers"}, expected=202)["id"]
    )
    assert selected["metadata"]["preview"] == [{"ID": "001", "Email": "alice@example.com"}]
    excel_job = wait(
        request(
            "POST",
            "/jobs",
            {
                **excel_config,
                "sheet": "Customers",
                "inspection_id": selected["id"],
                "operation": "regex_replace",
                "prompt": "Find email addresses",
                "target_columns": ["Email"],
                "replacement": "REDACTED",
            },
            expected=202,
        )["id"]
    )
    assert excel_job["metadata"]["cache_hit"] is True
    excel_page = request("GET", "/jobs/" + excel_job["id"] + "/results")
    assert excel_page["rows"] == [{"ID": "001", "Email": "REDACTED"}]
    other = requests.Session()
    assert other.get(args.base_url + "/api/jobs/" + jobs[0]["job_id"], timeout=10).status_code == 404
    cancelled = request(
        "POST",
        "/jobs",
        {
            **input_config,
            "inspection_id": inspection["id"],
            "operation": "regex_replace",
            "prompt": "Find email addresses",
            "target_columns": ["Email"],
            "replacement": "CANCEL-ME",
        },
        expected=202,
    )
    application_name = "patternforge-" + cancelled["id"]
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if application_name in cluster()["active_application_names"]:
            break
        status = request("GET", "/jobs/" + cancelled["id"])
        assert status["status"] not in {"SUCCESS", "FAILED", "CANCELLED"}, (
            "The cancellation test did not observe a running Spark application."
        )
        time.sleep(0.25)
    else:
        raise AssertionError("The Spark application never became active for the cancellation test.")
    cancel_started = time.monotonic()
    cancel = request("POST", "/jobs/" + cancelled["id"] + "/cancel")
    assert cancel["cancel_requested"]
    while time.monotonic() - cancel_started < 60:
        status = request("GET", "/jobs/" + cancelled["id"])
        if status["status"] == "CANCELLED" and application_name not in cluster()["active_application_names"]:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("Cancellation did not stop the actual Spark application within 60 seconds.")
    report = {
        "status": "passed",
        "fixture_notice": (
            "S3 is a test fixture; LLM uses genuine local CPU inference; Celery, Redis, PostgreSQL and Spark are real."
            if args.genuine_model
            else "S3 and LLM are deterministic test fixtures; Celery, Redis, PostgreSQL and Spark are real."
        ),
        "rows_per_operation": args.rows,
        "columns": 10,
        "source_bytes": s3.head_object(Bucket=bucket, Key="inputs/customers.csv")["ContentLength"],
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "host_logical_cpus": os.cpu_count(),
            "spark": "3.5.8",
            "workers": 2,
            "executor_cores": 1,
            "executor_memory": "1g",
            "driver_memory": "1g",
        },
        "jobs": jobs,
        "excel": "inspect-and-transform-passed",
        "real_redis_plan_cache": "passed",
        "ambiguous_identifier_request": "refused-before-spark"
        if args.genuine_model
        else "not-a-fixture-check",
        "running_cancellation": "spark-application-stopped",
        "cancellation_seconds": round(time.monotonic() - cancel_started, 2),
        "isolation": "passed",
        "seconds": round(time.monotonic() - started, 2),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
