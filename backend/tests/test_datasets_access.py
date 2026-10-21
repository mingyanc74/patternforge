from datetime import timedelta
from unittest.mock import Mock

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from core.models import Job
from core.services.datasets import import_source
from core.tasks import maintenance, process_job
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_imported_dataset_outlives_s3_connection(
    client, saved_connection, bucket, data_dir, email_plan, mocker
):
    submitted = client.post(
        "/api/files/inspect",
        {"connection_id": str(saved_connection.id), "source_key": "customers.csv"},
        format="json",
    )
    imported = Job.objects.get(pk=submitted.data["id"])
    original = bucket.get_object(Bucket=saved_connection.bucket, Key="customers.csv")["Body"].read()

    def preview(job, lease, work):
        assert job._snapshot_path.read_bytes() == original
        return {
            "columns": [
                {"name": "ID", "type": "string"},
                {"name": "Name", "type": "string"},
                {"name": "Email", "type": "string"},
            ],
            "preview": [{"ID": "001", "Name": "John Doe", "Email": "john.doe@example.com"}],
            "requires_sheet": False,
        }

    runner = mocker.patch("core.tasks.run_spark", side_effect=preview)
    process_job(str(imported.id))
    imported.refresh_from_db()
    assert imported.status == "SUCCESS" and imported.dataset_path
    assert client.get("/api/datasets").data["datasets"][0]["dataset_available"] is True
    saved_connection.expires_at = timezone.now() - timedelta(seconds=1)
    saved_connection.disconnected_at = timezone.now()
    saved_connection.ciphertext = ""
    saved_connection.save()
    assert client.get(f"/api/s3/connections/{saved_connection.id}/files").status_code == 410
    assert (
        client.post(
            "/api/files/inspect",
            {"connection_id": str(saved_connection.id), "source_key": "customers.csv"},
            format="json",
        ).status_code
        == 410
    )
    # Even removing the original from the TEST fixture cannot change an imported snapshot.
    bucket.delete_object(Bucket=saved_connection.bucket, Key="customers.csv")
    body = {
        "connection_id": str(saved_connection.id),
        "source_key": "customers.csv",
        "inspection_id": str(imported.id),
        "operation": "regex_replace",
        "target_columns": ["Email"],
        "prompt": "Find email addresses",
        "replacement": "REDACTED",
    }
    submitted = client.post("/api/jobs", body, format="json")
    assert submitted.status_code == 202, submitted.data
    transform = Job.objects.get(pk=submitted.data["id"])
    assert transform.input_dataset_id == imported.id
    aws_check = mocker.patch("core.tasks.ensure_unchanged", side_effect=AssertionError("No S3 after import"))
    mocker.patch("core.tasks.get_plan", return_value=(email_plan, False))

    def execute(job, lease, work):
        from core.services.datasets import snapshot_path

        assert snapshot_path(job.input_dataset).read_bytes() == original
        (work / "parquet").mkdir()
        pq.write_table(
            pa.table({"ID": ["001"], "Email": ["REDACTED"]}), work / "parquet" / "part-00000.parquet"
        )
        return {
            "row_count": 1,
            "columns": [{"name": "ID", "type": "string"}, {"name": "Email", "type": "string"}],
            "changed_cells": {"Email": 1},
        }

    runner.side_effect = execute
    process_job(str(transform.id))
    transform.refresh_from_db()
    assert transform.status == "SUCCESS"
    assert client.get(f"/api/jobs/{transform.id}/results").data["rows"] == [
        {"ID": "001", "Email": "REDACTED"}
    ]
    aws_check.assert_not_called()
    from pathlib import Path

    assert Path(imported.dataset_path).exists()
    other = APIClient()
    other.get("/api/bootstrap")
    assert other.get("/api/datasets").data["datasets"] == []
    assert other.post("/api/jobs", body, format="json").status_code == 404


def test_expired_dataset_retained_while_job_active_then_reclaimed(client, saved_connection, data_dir):
    folder = data_dir / "jobs" / "import"
    folder.mkdir(parents=True)
    path = folder / "import-source.csv"
    path.write_text("ID\n001\n")
    dataset = Job.objects.create(
        owner=saved_connection.owner,
        connection=saved_connection,
        kind="inspect",
        status="SUCCESS",
        source_key="customers.csv",
        dataset_path=str(path),
        dataset_expires_at=timezone.now() - timedelta(seconds=1),
    )
    job = Job.objects.create(
        owner=dataset.owner, connection=saved_connection, input_dataset=dataset, source_key=dataset.source_key
    )
    maintenance()
    assert path.exists()
    assert client.get("/api/datasets").data["datasets"] == []
    job.status = "CANCELLED"
    job.save()
    maintenance()
    dataset.refresh_from_db()
    assert not path.exists() and dataset.dataset_path == ""


def test_partial_import_is_not_retained(saved_connection, data_dir, mocker):
    from core.errors import PipelineError

    job = Job(connection=saved_connection, source_key="customers.csv", source_fingerprint={"size": 999})
    fake = Mock()
    fake.get_object.return_value = {"Body": __import__("io").BytesIO(b"ID\n001\n")}
    mocker.patch("core.services.datasets.client_for", return_value=fake)
    with pytest.raises(PipelineError, match="SOURCE_CHANGED"):
        import_source(job, data_dir, lambda: None)
    assert not (data_dir / "import-source.csv").exists()


def test_gate_is_separate_from_aws_and_preserves_session_owner(settings):
    cache.clear()
    settings.DEMO_ACCESS_PASSWORD_HASH = make_password("test-entrance-password")
    client = APIClient(enforce_csrf_checks=True)
    boot = client.get("/api/bootstrap")
    assert boot.data["access_required"] is True and "limits" not in boot.data
    assert client.get("/api/datasets").status_code == 403
    assert client.get("/api/jobs").status_code == 403
    assert (
        client.post("/api/access/unlock", {"password": "test-entrance-password"}, format="json").status_code
        == 403
    )
    wrong = client.post(
        "/api/access/unlock",
        {"password": "do-not-echo"},
        format="json",
        HTTP_X_CSRFTOKEN=boot.data["csrf_token"],
    )
    assert wrong.status_code == 403 and "do-not-echo" not in str(wrong.data)
    response = client.post(
        "/api/access/unlock",
        {"password": "test-entrance-password"},
        format="json",
        HTTP_X_CSRFTOKEN=boot.data["csrf_token"],
    )
    assert response.status_code == 200
    opened = client.get("/api/bootstrap")
    assert opened.data["access_required"] is False and opened.data["access_gate_enabled"] is True
    identity = client.session["owner"]
    assert client.get("/api/datasets").status_code == 200
    assert (
        client.post(
            "/api/s3/connections", {}, format="json", HTTP_X_CSRFTOKEN=opened.data["csrf_token"]
        ).status_code
        == 400
    )
    response = client.post("/api/access/lock", {}, format="json", HTTP_X_CSRFTOKEN=opened.data["csrf_token"])
    assert response.status_code == 200 and client.session["owner"] == identity
    assert client.get("/api/bootstrap").data["access_required"] is True


def test_gate_rate_limit_and_rotation(settings):
    cache.clear()
    settings.DEMO_ACCESS_PASSWORD_HASH = make_password("test-only-gate")
    client = APIClient()
    client.get("/api/bootstrap")
    for _ in range(5):
        assert client.post("/api/access/unlock", {"password": "wrong"}, format="json").status_code == 403
    assert client.post("/api/access/unlock", {"password": "wrong"}, format="json").status_code == 429
    cache.clear()
    assert client.post("/api/access/unlock", {"password": "test-only-gate"}, format="json").status_code == 200
    settings.DEMO_ACCESS_PASSWORD_HASH = make_password("rotated-gate")
    assert client.get("/api/jobs").status_code == 403
