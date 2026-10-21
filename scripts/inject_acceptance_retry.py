"""Operator-only single-job transient failure; never fake a successful S3 response.

Run in the isolated web application container with its existing configuration.
The real Celery worker performs attempt 2 after this process exits. No service,
network, model or shared module in a running worker is modified.
"""

import argparse
import os
import uuid
from unittest.mock import patch

import django


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection-id", type=uuid.UUID, required=True)
    parser.add_argument("--job-id", type=uuid.UUID, required=True)
    args = parser.parse_args()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from core.errors import PipelineError
    from core.models import Job, S3Connection
    from core.services.s3 import client_for, fingerprint
    from core.tasks import process_job
    from django.utils import timezone

    connection = S3Connection.objects.get(
        pk=args.connection_id, source_type="amazon_s3",
        bucket="patternforge-test-20261021-a7f4c2",
        disconnected_at__isnull=True, expires_at__gt=timezone.now(),
    )
    assert not Job.objects.filter(pk=args.job_id).exists()
    assert not Job.objects.filter(owner=connection.owner, status__in=["QUEUED", "RUNNING"]).exists()
    actual = fingerprint(client_for(connection), connection.bucket, "test_data.csv")
    job = Job.objects.create(
        id=args.job_id, owner=connection.owner, connection=connection, kind="inspect",
        source_key="test_data.csv", source_fingerprint=actual,
        config={"sheet": "", "delimiter": ",", "encoding": "UTF-8"},
    )
    failure = PipelineError("S3_TEMPORARY_ERROR", "Acceptance-only single-attempt transient fault injection.", True)
    with patch("core.tasks.import_source", side_effect=failure):
        process_job(str(job.id))
    job.refresh_from_db()
    assert job.attempt == 1 and job.status == "QUEUED" and job.stage == "RETRYING"
    print("Single-job fault injected; persisted attempt=1, stage=RETRYING, real outbox retry scheduled.")
    print("No AWS success response, model result or Spark result was mocked. Other worker processes unchanged.")


if __name__ == "__main__":
    main()
