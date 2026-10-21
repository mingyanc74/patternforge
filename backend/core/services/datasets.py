"""Import once in Celery; subsequent Spark jobs do not need S3 credentials."""

import hashlib
import io
import time

from django.conf import settings
from django.utils import timezone

from core.errors import PipelineError
from core.services.results import contained_path
from core.services.s3 import call_s3, client_for


def available(dataset):
    return bool(
        dataset.dataset_path and dataset.dataset_expires_at and dataset.dataset_expires_at > timezone.now()
    )


def snapshot_path(dataset):
    if not available(dataset):
        raise PipelineError("DATASET_EXPIRED", "This imported dataset expired. Connect and import it again.")
    path = contained_path(dataset.dataset_path)
    if not path.is_file():
        raise PipelineError("DATASET_UNAVAILABLE", "The imported file is unavailable. Import it again.")
    return path


def import_source(job, work, checkpoint):
    """Bounded, cancellable transfer; never accepts a client-supplied local path."""
    suffix = ".xlsx" if job.source_key.lower().endswith(".xlsx") else ".csv"
    path = work / ("import-source" + suffix)
    if job.connection.source_type == "sample":
        from core.sample_bucket import object_bytes

        source = io.BytesIO(object_bytes(job.source_key))
    else:
        args = {"Bucket": job.connection.bucket, "Key": job.source_key}
        if job.source_fingerprint.get("version_id"):
            args["VersionId"] = job.source_fingerprint["version_id"]
        if job.source_fingerprint.get("etag"):
            args["IfMatch"] = job.source_fingerprint["etag"]
        source = call_s3(client_for(job.connection).get_object, **args)["Body"]
    size, digest, started = 0, hashlib.sha256(), time.monotonic()
    try:
        with source, path.open("xb") as target:
            while True:
                checkpoint()
                if time.monotonic() - started > settings.JOB_TIMEOUT_SECONDS:
                    raise PipelineError("JOB_TIMEOUT", "Import exceeded the configured time limit.")
                chunk = (
                    call_s3(source.read, amt=1024 * 1024)
                    if hasattr(source, "iter_chunks")
                    else source.read(1024 * 1024)
                )
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_FILE_BYTES or (suffix == ".xlsx" and size > settings.MAX_EXCEL_BYTES):
                    raise PipelineError("FILE_TOO_LARGE", "The source exceeds its configured import limit.")
                digest.update(chunk)
                target.write(chunk)
        if size != job.source_fingerprint["size"]:
            raise PipelineError("SOURCE_CHANGED", "The source changed during import. Inspect it again.")
        path.chmod(0o600)
        return path, digest.hexdigest()
    except Exception:
        path.unlink(missing_ok=True)
        raise
