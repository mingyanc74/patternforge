"""Exercise the REAL HTTP/Celery/Redis/Spark stack against explicitly synthetic S3/model fixtures."""

import argparse
import csv
import io
import json
import time
from pathlib import Path

import boto3
import requests
from openpyxl import Workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--s3-url", default="http://localhost:5000")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--report", type=Path, default=Path("reports/local/e2e.json"))
    args = parser.parse_args()
    started = time.monotonic()
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
    writer.writerow(["ID", "Name", "Email", "Description"])
    for i in range(args.rows):
        writer.writerow(
            [str(i).zfill(8), f"  USER   {i}  ", f"user{i}@example.com", f"Order ORD-{i} shipped"]
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
    session.headers.update({"X-CSRFToken": csrf})

    def request(method, path, body=None, params=None, expected=200):
        response = session.request(
            method, args.base_url + "/api" + path, json=body, params=params, timeout=30
        )
        if response.status_code != expected:
            raise AssertionError(f"{path}: HTTP {response.status_code}: {response.text[:600]}")
        return response.json()

    def wait(job_id):
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            result = request("GET", "/jobs/" + job_id)
            if result["status"] in {"SUCCESS", "FAILED", "CANCELLED"}:
                assert result["status"] == "SUCCESS", result.get("error")
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
    jobs = []
    for operation, prompt, columns, extra in [
        ("regex_replace", "Find email addresses", ["Email"], {"replacement": "$REDACTED"}),
        ("regex_extract", "Extract order IDs", ["Description"], {"new_column": "order_id"}),
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
        assert page["total_rows"] == args.rows and len(page["rows"]) == min(25, args.rows)
        assert finished["metadata"]["partitions"] >= 2
        for row in page["rows"]:
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
            }
        )
    excel_config = {"connection_id": connection["id"], "source_key": "inputs/sample.xlsx"}
    sheets = wait(request("POST", "/files/inspect", excel_config, expected=202)["id"])
    assert sheets["metadata"]["requires_sheet"]
    selected = wait(
        request("POST", "/files/inspect", {**excel_config, "sheet": "Customers"}, expected=202)["id"]
    )
    assert selected["metadata"]["preview"] == [{"ID": "001", "Email": "alice@example.com"}]
    other = requests.Session()
    assert other.get(args.base_url + "/api/jobs/" + jobs[0]["job_id"], timeout=10).status_code == 404
    cancelled = request("POST", "/files/inspect", input_config, expected=202)
    cancel = request("POST", "/jobs/" + cancelled["id"] + "/cancel")
    assert cancel["cancel_requested"]
    report = {
        "status": "passed",
        "fixture_notice": "S3 and LLM are deterministic test fixtures; Celery, Redis, PostgreSQL and Spark are real.",
        "rows_per_operation": args.rows,
        "jobs": jobs,
        "excel": "passed",
        "isolation": "passed",
        "seconds": round(time.monotonic() - started, 2),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
