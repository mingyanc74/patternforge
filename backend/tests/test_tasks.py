import uuid
from datetime import timedelta

import pyarrow as pa
import pyarrow.parquet as pq
from core.errors import PipelineError
from core.models import Job, Outbox
from core.tasks import dispatch_pending, maintenance, process_job
from django.utils import timezone


def queued(connection):
    job = Job.objects.create(
        owner=connection.owner,
        connection=connection,
        source_key="customers.csv",
        config={
            "operation": "regex_replace",
            "prompt": "Find emails",
            "target_columns": ["Email"],
            "replacement": "REDACTED",
        },
    )
    Outbox.objects.create(job=job, available_at=timezone.now())
    return job


def test_success_is_published_once_and_duplicate_delivery_is_harmless(
    saved_connection, data_dir, email_plan, mocker
):
    job = queued(saved_connection)
    mocker.patch("core.tasks.ensure_unchanged")
    mocker.patch("core.tasks.get_plan", return_value=(email_plan, False))

    def execute(job, lease, work):
        (work / "parquet").mkdir()
        pq.write_table(pa.table({"Email": ["REDACTED"]}), work / "parquet" / "part-00000.parquet")
        return {
            "row_count": 1,
            "changed_cells": {"Email": 1},
            "columns": [{"name": "Email", "type": "string"}],
        }

    runner = mocker.patch("core.tasks.run_spark", side_effect=execute)
    process_job(str(job.id))
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCESS and job.progress == 100 and job.manifest
    manifest = job.manifest
    process_job(str(job.id))
    job.refresh_from_db()
    assert runner.call_count == 1 and job.manifest == manifest


def test_retry_is_bounded_and_has_no_partial_result(saved_connection, data_dir, mocker):
    job = queued(saved_connection)
    mocker.patch(
        "core.tasks.ensure_unchanged", side_effect=PipelineError("S3_TEMPORARY_ERROR", "Retry later.", True)
    )
    for attempt in range(1, 4):
        process_job(str(job.id))
        job.refresh_from_db()
        assert job.attempt == attempt and not job.manifest
        assert job.status == (Job.Status.QUEUED if attempt < 3 else Job.Status.FAILED)
    assert list((data_dir / "jobs" / str(job.id)).iterdir()) == []


def test_invalid_credentials_do_not_retry(saved_connection, data_dir, mocker):
    job = queued(saved_connection)
    mocker.patch(
        "core.tasks.ensure_unchanged", side_effect=PipelineError("S3_CREDENTIALS_INVALID", "Reconnect.")
    )
    process_job(str(job.id))
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED and job.attempt == 1


def test_cancel_during_work_does_not_publish_result(saved_connection, data_dir, email_plan, mocker):
    job = queued(saved_connection)
    mocker.patch("core.tasks.ensure_unchanged")
    mocker.patch("core.tasks.get_plan", return_value=(email_plan, False))

    def stop(job, lease, work):
        Job.objects.filter(id=job.id).update(cancel_requested_at=timezone.now())
        raise PipelineError("CANCELLED", "Cancelled by user.")

    mocker.patch("core.tasks.run_spark", side_effect=stop)
    process_job(str(job.id))
    job.refresh_from_db()
    assert job.status == Job.Status.CANCELLED and not job.manifest


def test_dispatch_preserves_outbox_when_broker_is_unavailable(saved_connection, mocker):
    job = queued(saved_connection)
    publish = mocker.patch("core.tasks.process_job.apply_async", side_effect=ConnectionError)
    assert dispatch_pending() == 0
    assert Outbox.objects.get(job=job).sent_at is None
    publish.side_effect = None
    assert dispatch_pending() == 1
    publish.assert_called_with(args=[str(job.id)], task_id=str(job.id), retry=False)
    assert Outbox.objects.get(job=job).sent_at is not None


def test_stale_worker_recovers_with_invalidated_lease(saved_connection, mocker):
    job = queued(saved_connection)
    old_lease = uuid.uuid4()
    job.status, job.lease, job.attempt = Job.Status.RUNNING, old_lease, 1
    job.heartbeat_at = timezone.now() - timedelta(minutes=5)
    job.save()
    maintenance()
    job.refresh_from_db()
    assert job.status == Job.Status.QUEUED and job.lease is None
    assert Outbox.objects.get(job=job).sent_at is None


def test_cancelled_outbox_rows_do_not_starve_new_jobs(saved_connection, mocker):
    old_jobs = [
        Job(
            owner=saved_connection.owner,
            connection=saved_connection,
            source_key="old.csv",
            status=Job.Status.CANCELLED,
        )
        for _ in range(51)
    ]
    Job.objects.bulk_create(old_jobs)
    Outbox.objects.bulk_create([Outbox(job=job, available_at=timezone.now()) for job in old_jobs])
    waiting = queued(saved_connection)
    publish = mocker.patch("core.tasks.process_job.apply_async")
    assert dispatch_pending() == 1
    publish.assert_called_once_with(args=[str(waiting.id)], task_id=str(waiting.id), retry=False)
