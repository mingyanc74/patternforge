from datetime import timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from core.models import Job
from core.services.results import build_manifest
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.fixture
def result_job(saved_connection, data_dir):
    job = Job.objects.create(
        owner=saved_connection.owner,
        connection=saved_connection,
        source_key="customers.csv",
        status=Job.Status.SUCCESS,
        result_expires_at=timezone.now() + timedelta(hours=1),
    )
    work = data_dir / "jobs" / str(job.id) / "result-version"
    (work / "parquet").mkdir(parents=True)
    columns = [{"name": "ID", "type": "string"}, {"name": "Email", "type": "string"}]
    for index in range(3):
        table = pa.Table.from_pylist(
            [
                {"ID": str(number), "Email": None if number % 5 == 0 else "REDACTED"}
                for number in range(index * 7, (index + 1) * 7)
            ]
        )
        pq.write_table(table, work / "parquet" / f"part-{index:05}.parquet", row_group_size=3)
    job.manifest = str(build_manifest(work, {"columns": columns, "row_count": 21}, "version-1"))
    job.save()
    return job


def test_pages_cross_files_and_rowgroups_without_loss_or_duplicates(client, result_job):
    cursor, ids = "", []
    while True:
        response = client.get(f"/api/jobs/{result_job.id}/results", {"cursor": cursor, "limit": 4})
        assert response.status_code == 200, response.data
        ids.extend(row["ID"] for row in response.data["rows"])
        cursor = response.data["next_cursor"]
        if not cursor:
            break
    assert ids == list(map(str, range(21)))


def test_cursor_tampering_page_limits_and_owner(client, result_job):
    url = f"/api/jobs/{result_job.id}/results"
    assert client.get(url, {"limit": 501}).status_code == 400
    assert client.get(url, {"limit": -1}).status_code == 400
    assert client.get(url, {"cursor": "tampered"}).status_code == 400
    assert APIClient().get(url).status_code == 404


def test_expired_and_not_ready_results_are_distinct(client, result_job):
    url = f"/api/jobs/{result_job.id}/results"
    result_job.result_expires_at = timezone.now() - timedelta(seconds=1)
    result_job.save()
    assert client.get(url).status_code == 410
    result_job.status = Job.Status.FAILED
    result_job.save()
    assert client.get(url).status_code == 409


def test_zero_rows_are_valid_with_schema(client, result_job):
    import json
    from pathlib import Path

    manifest = Path(result_job.manifest)
    data = json.loads(manifest.read_text())
    data.update(row_count=0, groups=[])
    manifest.write_text(json.dumps(data))
    response = client.get(f"/api/jobs/{result_job.id}/results")
    assert response.status_code == 200 and response.data["rows"] == []
    assert response.data["total_rows"] == 0 and len(response.data["columns"]) == 2
