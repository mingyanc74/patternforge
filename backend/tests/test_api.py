from datetime import timedelta
from unittest.mock import Mock

import pytest
from core.models import Job, Outbox
from core.security import decrypt_credentials
from core.services.s3 import fingerprint
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def inspect_job(client, saved_connection, bucket):
    response = client.post(
        "/api/files/inspect",
        {"connection_id": str(saved_connection.id), "source_key": "customers.csv"},
        format="json",
    )
    assert response.status_code == 202, response.data
    job = Job.objects.get(id=response.data["id"])
    job.status = Job.Status.SUCCESS
    job.metadata = {
        "columns": [
            {"name": "ID", "type": "string"},
            {"name": "Name", "type": "string"},
            {"name": "Email", "type": "string"},
        ],
        "preview": [],
        "requires_sheet": False,
    }
    job.result_expires_at = timezone.now() + timedelta(hours=1)
    job.save()
    return job


@pytest.mark.django_db
def test_connect_dynamic_credentials_and_encrypts(client, bucket):
    response = client.post(
        "/api/s3/connections",
        {
            "bucket": "user-owned-bucket",
            "region": "us-east-1",
            "access_key": "another-test-user",
            "secret_key": "unique-secret-value",
        },
        format="json",
    )
    assert response.status_code == 201
    from core.models import S3Connection

    item = S3Connection.objects.get(id=response.data["id"])
    assert "unique-secret-value" not in item.ciphertext
    assert "unique-secret-value" not in str(response.data)
    assert decrypt_credentials(item.ciphertext)["secret_key"] == "unique-secret-value"


def test_file_listing_pagination_and_supported_formats(client, saved_connection, bucket):
    for index in range(101):
        bucket.put_object(Bucket=saved_connection.bucket, Key=f"reports/{index:03}.csv", Body=b"id\n1")
    bucket.put_object(Bucket=saved_connection.bucket, Key="reports/readme.txt", Body=b"not supported")
    url = f"/api/s3/connections/{saved_connection.id}/files"
    first = client.get(url, {"prefix": "reports/"})
    assert first.status_code == 200 and len(first.data["files"]) == 100
    second = client.get(url, {"prefix": "reports/", "cursor": first.data["next_cursor"]})
    assert second.status_code == 200 and len(second.data["files"]) == 2
    keys = [f["key"] for f in first.data["files"] + second.data["files"]]
    assert len(set(keys)) == 102
    assert second.data["files"][-1]["supported"] is False
    assert client.get(url, {"prefix": "other/", "cursor": first.data["next_cursor"]}).status_code == 400


def test_submission_is_async_and_idempotent(client, saved_connection, bucket, mocker):
    inspection = inspect_job(client, saved_connection, bucket)
    heavy = mocker.patch("core.tasks.process_job.apply_async")
    body = {
        "connection_id": str(saved_connection.id),
        "source_key": "customers.csv",
        "inspection_id": str(inspection.id),
        "operation": "regex_replace",
        "prompt": "Find email addresses",
        "target_columns": ["Email"],
        "replacement": "REDACTED",
    }
    first = client.post("/api/jobs", body, format="json", HTTP_IDEMPOTENCY_KEY="unique-request")
    assert first.status_code == 202, first.data
    assert first.data["status"] == "QUEUED"
    assert not heavy.called
    assert Outbox.objects.filter(job_id=first.data["id"]).exists()
    again = client.post("/api/jobs", body, format="json", HTTP_IDEMPOTENCY_KEY="unique-request")
    assert again.data["id"] == first.data["id"]
    conflict = client.post(
        "/api/jobs", {**body, "replacement": "OTHER"}, format="json", HTTP_IDEMPOTENCY_KEY="unique-request"
    )
    assert conflict.status_code == 409


def test_missing_replacement_differs_from_empty(client, saved_connection, bucket):
    inspection = inspect_job(client, saved_connection, bucket)
    body = {
        "connection_id": str(saved_connection.id),
        "source_key": "customers.csv",
        "inspection_id": str(inspection.id),
        "operation": "regex_replace",
        "prompt": "Find emails",
        "target_columns": ["Email"],
    }
    assert client.post("/api/jobs", body, format="json").status_code == 400
    assert client.post("/api/jobs", {**body, "replacement": ""}, format="json").status_code == 202


def test_column_and_parsing_mismatch_rejected(client, saved_connection, bucket):
    inspection = inspect_job(client, saved_connection, bucket)
    body = {
        "connection_id": str(saved_connection.id),
        "source_key": "customers.csv",
        "inspection_id": str(inspection.id),
        "operation": "regex_extract",
        "prompt": "Find emails",
        "target_columns": ["Missing"],
        "new_column": "found",
    }
    assert client.post("/api/jobs", body, format="json").status_code == 400
    assert (
        client.post(
            "/api/jobs", {**body, "target_columns": ["Email"], "new_column": "email"}, format="json"
        ).status_code
        == 400
    )
    assert client.post("/api/jobs", {**body, "delimiter": ";"}, format="json").status_code == 400


def test_sessions_cannot_read_cancel_or_list_others_resources(client, saved_connection, bucket):
    job = inspect_job(client, saved_connection, bucket)
    other = APIClient()
    other.get("/api/bootstrap")
    assert other.get(f"/api/jobs/{job.id}").status_code == 404
    assert other.post(f"/api/jobs/{job.id}/cancel").status_code == 404
    assert other.get(f"/api/s3/connections/{saved_connection.id}/files").status_code == 404
    assert other.delete(f"/api/s3/connections/{saved_connection.id}").status_code == 404
    assert other.get("/api/jobs").data["jobs"] == []


def test_cancel_queued_job_and_terminal_is_immutable(client, saved_connection):
    job = Job.objects.create(
        owner=saved_connection.owner, connection=saved_connection, source_key="customers.csv"
    )
    response = client.post(f"/api/jobs/{job.id}/cancel")
    assert response.data["status"] == "CANCELLED"
    assert client.post(f"/api/jobs/{job.id}/cancel").data["status"] == "CANCELLED"
    job.refresh_from_db()
    assert job.cancel_requested_at and job.finished_at


def test_expired_connection_rejected(client, saved_connection):
    saved_connection.expires_at = timezone.now() - timedelta(seconds=1)
    saved_connection.save()
    assert client.get(f"/api/s3/connections/{saved_connection.id}/files").status_code == 410


def test_anonymous_state_changes_enforce_csrf(bucket):
    strict = APIClient(enforce_csrf_checks=True)
    bootstrap = strict.get("/api/bootstrap")
    body = {"bucket": "user-owned-bucket", "access_key": "test-user", "secret_key": "test-secret"}
    assert strict.post("/api/s3/connections", body, format="json").status_code == 403
    assert (
        strict.post(
            "/api/s3/connections", body, format="json", HTTP_X_CSRFTOKEN=bootstrap.data["csrf_token"]
        ).status_code
        == 201
    )


def test_s3_permission_error_is_clear_and_redacted(client, mocker):
    from botocore.exceptions import ClientError

    fake = Mock()
    fake.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "secret-should-never-echo"}}, "HeadBucket"
    )
    mocker.patch("core.views.client_for", return_value=fake)
    response = client.post(
        "/api/s3/connections",
        {"bucket": "unknown-bucket", "access_key": "test-user", "secret_key": "secret-should-never-echo"},
        format="json",
    )
    assert response.status_code == 400 and response.data["error"]["code"] == "S3_ACCESS_DENIED"
    assert "secret-should-never-echo" not in str(response.data)


def test_source_fingerprint_includes_object_version(bucket):
    result = fingerprint(bucket, "user-owned-bucket", "customers.csv")
    assert set(result) == {"etag", "size", "modified", "version_id"}


def test_history_has_server_side_search_filter_pagination_and_safe_summary(client, saved_connection):
    for index in range(7):
        Job.objects.create(
            owner=saved_connection.owner,
            connection=saved_connection,
            kind="transform",
            source_key=f"reports/customer-{index}.csv",
            status="SUCCESS",
            config={"operation": "regex_replace", "sheet": "", "prompt": "private instruction"},
            manifest="published/result.json",
            result_expires_at=timezone.now() + timedelta(hours=1),
        )
    Job.objects.create(
        owner=saved_connection.owner,
        connection=saved_connection,
        kind="inspect",
        source_key="not-a-transform.csv",
    )
    url = "/api/jobs"
    first = client.get(url, {"kind": "transform", "limit": 5})
    assert first.status_code == 200 and first.data["total"] == 7
    assert len(first.data["jobs"]) == 5 and first.data["has_next"] is True
    second = client.get(url, {"kind": "transform", "limit": 5, "page": 2})
    assert len(second.data["jobs"]) == 2 and second.data["has_next"] is False
    assert not {job["id"] for job in first.data["jobs"]} & {job["id"] for job in second.data["jobs"]}
    entry = first.data["jobs"][0]
    assert entry["operation"] == "regex_replace" and entry["bucket"] == saved_connection.bucket
    assert "config" not in entry and "private instruction" not in str(first.data)
    assert client.get(url, {"search": entry["id"]}).data["total"] == 1
    assert client.get(url, {"search": "customer-2.csv"}).data["total"] == 1
    assert client.get(url, {"status": "FAILED"}).data["total"] == 0
    other = APIClient()
    other.get("/api/bootstrap")
    assert other.get(url, {"kind": "transform"}).data["total"] == 0


def test_history_expired_results_are_distinct_from_failed_jobs(client, saved_connection):
    for status, manifest, expires in [
        ("SUCCESS", "published.json", timezone.now() - timedelta(seconds=1)),
        ("SUCCESS", "", timezone.now() + timedelta(hours=1)),
        ("SUCCESS", "live.json", timezone.now() + timedelta(hours=1)),
        ("FAILED", "", None),
    ]:
        Job.objects.create(
            owner=saved_connection.owner,
            connection=saved_connection,
            kind="transform",
            source_key="source.csv",
            status=status,
            manifest=manifest,
            result_expires_at=expires,
        )
    expired = client.get("/api/jobs", {"status": "expired", "kind": "transform"})
    assert expired.status_code == 200 and expired.data["total"] == 2
    assert all(job["status"] == "SUCCESS" for job in expired.data["jobs"])


@pytest.mark.parametrize(
    "query",
    [
        {"page": 0},
        {"limit": 51},
        {"limit": "bad"},
        {"status": "unknown"},
        {"kind": "other"},
        {"search": "a" * 129},
    ],
)
def test_history_rejects_invalid_query(client, query):
    assert client.get("/api/jobs", query).status_code == 400


def test_production_health_uses_trusted_proxy_without_disabling_redirect(client, settings, mocker):
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    settings.ALLOWED_HOSTS = ["testserver", "localhost"]
    settings.SPARK_MASTER = "local[2]"
    mocker.patch("core.views.redis.Redis.from_url")
    # SecurityMiddleware snapshots redirect settings when a handler is first constructed.
    client = APIClient()
    insecure = client.get("/api/health", HTTP_HOST="localhost")
    assert insecure.status_code == 301
    assert insecure["Location"] == "https://localhost/api/health"
    internal = client.get("/api/health", HTTP_HOST="localhost", HTTP_X_FORWARDED_PROTO="https")
    assert internal.status_code == 200
    assert "services" in internal.data
