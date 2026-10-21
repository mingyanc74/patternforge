import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from core.errors import PipelineError
from core.models import Job, Outbox, S3Connection
from core.services.plans import get_plan
from core.services.results import build_manifest, contained_path
from core.services.s3 import ensure_unchanged


def scoped_update(job_id, lease, **values):
    return Job.objects.filter(id=job_id, lease=lease, status=Job.Status.RUNNING).update(**values)


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=15)


def run_spark(job, lease, work):
    submit = shutil.which("spark-submit") or shutil.which("spark-submit.cmd")
    if not submit:
        # PySpark installed in a virtualenv also exposes its launcher here.
        try:
            import pyspark

            submit = str(
                __import__("pathlib").Path(pyspark.__file__).parent
                / "bin"
                / ("spark-submit.cmd" if os.name == "nt" else "spark-submit")
            )
        except ImportError:
            raise PipelineError(
                "SPARK_NOT_AVAILABLE", "Install the Spark worker runtime before processing."
            ) from None
    spec = {
        "job_id": str(job.id),
        "lease": str(lease),
        "timeout": settings.JOB_TIMEOUT_SECONDS,
        "kind": job.kind,
        "config": job.config,
        "plan": job.plan,
        "source_key": job.source_key,
        "bucket": job.connection.bucket,
        "region": job.connection.region,
        "encrypted_credentials": job.connection.ciphertext,
        "endpoint": settings.S3_ENDPOINT_URL,
        "partitions": settings.SPARK_PARTITIONS,
        "max_excel_bytes": settings.MAX_EXCEL_BYTES,
        "max_excel_rows": settings.MAX_EXCEL_ROWS,
        "max_cell_chars": settings.MAX_CELL_CHARS,
    }
    if job.connection.source_type == "sample":
        from core.sample_bucket import object_bytes

        suffix = ".xlsx" if job.source_key.endswith(".xlsx") else ".csv"
        sample_path = work / ("sample-input" + suffix)
        sample_path.write_bytes(object_bytes(job.source_key))
        spec["local_source"] = str(sample_path)
    spec_path = work / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    try:
        spec_path.chmod(0o600)
    except OSError:
        pass
    command = [
        submit,
        "--master",
        settings.SPARK_MASTER,
        "--driver-memory",
        settings.SPARK_DRIVER_MEMORY,
        "--executor-memory",
        settings.SPARK_EXECUTOR_MEMORY,
        "--conf",
        "spark.executor.cores=" + os.getenv("SPARK_EXECUTOR_CORES", "1"),
        "--conf",
        "spark.cores.max=" + os.getenv("SPARK_MAX_CORES", "2"),
    ]
    if settings.SPARK_DRIVER_HOST:
        command += [
            "--conf",
            "spark.driver.host=" + settings.SPARK_DRIVER_HOST,
            "--conf",
            "spark.driver.bindAddress=0.0.0.0",
        ]
    command += [str(settings.BASE_DIR / "spark_engine" / "run_job.py"), str(spec_path)]
    env = {
        **os.environ,
        "CREDENTIAL_KEY": settings.CREDENTIAL_KEY,
        "PYSPARK_PYTHON": sys.executable,
        "PYSPARK_DRIVER_PYTHON": sys.executable,
    }
    if not env.get("SPARK_HOME"):
        from pathlib import Path

        import pyspark

        env["SPARK_HOME"] = str(Path(pyspark.__file__).parent)
    if os.name == "nt":
        from spark_engine.launcher import windows_submit

        command = windows_submit(command[1:], settings.SPARK_DRIVER_MEMORY)
    process = subprocess.Popen(
        command,
        env=env,
        cwd=settings.BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=os.name != "nt",
    )
    started, last_progress = time.monotonic(), None
    try:
        while process.poll() is None:
            current = Job.objects.only("status", "lease", "cancel_requested_at").get(id=job.id)
            if current.lease != lease or current.status != Job.Status.RUNNING:
                raise PipelineError("LEASE_LOST", "The worker lease was replaced.")
            if current.cancel_requested_at:
                raise PipelineError("CANCELLED", "Cancelled by user.")
            if time.monotonic() - started > settings.JOB_TIMEOUT_SECONDS:
                raise PipelineError("JOB_TIMEOUT", "Processing exceeded the configured time limit.")
            update = {"heartbeat_at": timezone.now()}
            progress_file = work / "progress.json"
            if progress_file.exists():
                try:
                    progress = json.loads(progress_file.read_text(encoding="utf-8"))
                    if progress != last_progress:
                        update.update(stage=progress["stage"], progress=min(95, int(progress["progress"])))
                        last_progress = progress
                except (ValueError, KeyError, OSError):
                    pass
            scoped_update(job.id, lease, **update)
            time.sleep(1)
        if process.returncode:
            failure = work / "failure.json"
            if failure.exists():
                info = json.loads(failure.read_text(encoding="utf-8"))
                raise PipelineError(info["code"], info["message"])
            raise PipelineError(
                "SPARK_EXECUTION_FAILED", "Spark stopped unexpectedly. Check worker resources.", True
            )
        return json.loads((work / "output.json").read_text(encoding="utf-8"))
    finally:
        stop_process(process)
        spec_path.unlink(missing_ok=True)
        # A workbook/staged CSV is no longer needed after the driver has stopped.
        for filename in ("input.xlsx", "excel.csv", "sample-input.csv", "sample-input.xlsx"):
            (work / filename).unlink(missing_ok=True)


@shared_task(name="core.tasks.process_job", acks_late=True, reject_on_worker_lost=True)
def process_job(job_id):
    with transaction.atomic():
        job = Job.objects.select_for_update().select_related("connection").get(id=job_id)
        if job.status != Job.Status.QUEUED:
            return
        if job.cancel_requested_at:
            job.status, job.stage, job.finished_at = Job.Status.CANCELLED, "CANCELLED", timezone.now()
            job.save(update_fields=["status", "stage", "finished_at"])
            return
        lease = uuid.uuid4()
        job.status, job.stage, job.progress = Job.Status.RUNNING, "VALIDATING", 10
        job.lease, job.heartbeat_at = lease, timezone.now()
        job.attempt += 1
        job.started_at = job.started_at or timezone.now()
        job.save()
    work = settings.DATA_DIR / "jobs" / str(job.id) / str(lease)
    work.mkdir(parents=True, exist_ok=False)
    try:
        if job.connection.disconnected_at or job.connection.expires_at <= timezone.now():
            raise PipelineError("CONNECTION_EXPIRED", "Reconnect to S3 and submit a new job.")
        ensure_unchanged(job.connection, job.source_key, job.source_fingerprint)
        if job.kind == "transform":
            scoped_update(job.id, lease, stage="GENERATING_PLAN", progress=20)

            def cancelled():
                current = Job.objects.only("cancel_requested_at", "lease").get(id=job.id)
                scoped_update(job.id, lease, heartbeat_at=timezone.now())
                return bool(current.cancel_requested_at or current.lease != lease)

            plan, cached = get_plan(job, cancelled)
            if cancelled():
                raise PipelineError("CANCELLED", "Cancelled by user.")
            job.plan = plan
            scoped_update(
                job.id, lease, plan=plan, metadata={"cache_hit": cached}, stage="VALIDATING_RULE", progress=30
            )
        metadata = run_spark(job, lease, work)
        ensure_unchanged(job.connection, job.source_key, job.source_fingerprint)
        metadata["cache_hit"] = job.kind == "transform" and cached
        manifest = str(build_manifest(work, metadata, lease)) if job.kind == "transform" else ""
        with transaction.atomic():
            final = Job.objects.select_for_update().get(id=job.id)
            if final.lease != lease or final.status != Job.Status.RUNNING:
                return
            if final.cancel_requested_at:
                final.status, final.stage = Job.Status.CANCELLED, "CANCELLED"
            else:
                final.status, final.stage, final.progress = Job.Status.SUCCESS, "COMPLETED", 100
                final.metadata, final.manifest = metadata, manifest
                final.result_expires_at = timezone.now() + timedelta(hours=settings.RESULT_TTL_HOURS)
            final.finished_at, final.error_code, final.error_message = timezone.now(), "", ""
            final.save()
    except Exception as exc:
        error = (
            exc
            if isinstance(exc, PipelineError)
            else PipelineError(
                "PROCESSING_ERROR", "Processing could not finish. Check the file and worker configuration."
            )
        )
        with transaction.atomic():
            final = Job.objects.select_for_update().get(id=job.id)
            if final.lease != lease or final.status != Job.Status.RUNNING:
                return
            if final.cancel_requested_at or error.code == "CANCELLED":
                final.status, final.stage = Job.Status.CANCELLED, "CANCELLED"
                final.finished_at = timezone.now()
            elif error.retryable and final.attempt < 3:
                final.status, final.stage = Job.Status.QUEUED, "RETRYING"
                final.lease = None
                Outbox.objects.update_or_create(
                    job=final,
                    defaults={
                        "available_at": timezone.now()
                        + timedelta(seconds=2**final.attempt + random.uniform(0, 2)),
                        "sent_at": None,
                    },
                )
            else:
                final.status, final.stage, final.finished_at = Job.Status.FAILED, "FAILED", timezone.now()
            final.error_code, final.error_message = error.code, error.message
            final.save()
    finally:
        current = Job.objects.only("manifest").get(id=job.id)
        if not current.manifest or str(work) not in current.manifest:
            shutil.rmtree(contained_path(work), ignore_errors=True)


@shared_task(name="core.tasks.dispatch_pending")
def dispatch_pending():
    sent = 0
    for item in Outbox.objects.filter(
        sent_at__isnull=True, available_at__lte=timezone.now(), job__status=Job.Status.QUEUED
    ).order_by("available_at")[:50]:
        if item.job.status != Job.Status.QUEUED:
            continue
        try:
            process_job.apply_async(args=[str(item.job_id)], task_id=str(item.job_id), retry=False)
        except Exception:
            Outbox.objects.filter(pk=item.pk).update(attempts=F("attempts") + 1)
            break
        Outbox.objects.filter(pk=item.pk, sent_at__isnull=True).update(sent_at=timezone.now())
        sent += 1
    return sent


@shared_task(name="core.tasks.maintenance")
def maintenance():
    now = timezone.now()
    stale = now - timedelta(seconds=120)
    for item in Job.objects.filter(status=Job.Status.RUNNING, heartbeat_at__lt=stale):
        with transaction.atomic():
            job = Job.objects.select_for_update().get(id=item.id)
            if job.status != Job.Status.RUNNING or job.heartbeat_at >= stale:
                continue
            # Invalidate the old lease; a still-live worker notices and kills its driver.
            job.lease = None
            if job.cancel_requested_at or job.attempt >= 3:
                job.status = Job.Status.CANCELLED if job.cancel_requested_at else Job.Status.FAILED
                job.stage, job.finished_at = job.status, now
                job.error_code, job.error_message = "WORKER_LOST", "The processing worker stopped responding."
            else:
                job.status, job.stage = Job.Status.QUEUED, "RECOVERING"
                Outbox.objects.update_or_create(job=job, defaults={"available_at": now, "sent_at": None})
            job.save()
    Outbox.objects.filter(job__status=Job.Status.QUEUED, sent_at__lt=stale).update(sent_at=None)
    for job in Job.objects.filter(status__in=Job.TERMINAL, result_expires_at__lt=now).exclude(
        metadata={"expired": True}
    ):
        if job.manifest:
            folder = contained_path(job.manifest).parent
            shutil.rmtree(folder, ignore_errors=True)
        Job.objects.filter(id=job.id).update(manifest="", metadata={"expired": True})
    active_connections = Job.objects.filter(status__in=[Job.Status.QUEUED, Job.Status.RUNNING])
    S3Connection.objects.filter(Q(expires_at__lt=now) | Q(disconnected_at__isnull=False)).exclude(
        id__in=active_connections.values("connection_id")
    ).exclude(ciphertext="").update(ciphertext="")
    cleanup_abandoned_attempts(now)


def cleanup_abandoned_attempts(now):
    """Reclaim crash leftovers after retention; never touch active jobs or a published live result."""
    old = Job.objects.filter(
        status__in=Job.TERMINAL, finished_at__lt=now - timedelta(hours=settings.TEMP_TTL_HOURS)
    ).only("id", "manifest")
    for job in old.iterator(chunk_size=100):
        root = contained_path(settings.DATA_DIR / "jobs" / str(job.id))
        expected = (settings.DATA_DIR / "jobs" / str(job.id)).absolute()
        if root != expected or not root.is_dir() or root.is_symlink():
            continue
        published = contained_path(job.manifest).parent if job.manifest else None
        for child in root.iterdir():
            if not child.is_dir() or child.is_symlink():
                continue
            try:
                uuid.UUID(child.name)
            except ValueError:
                continue
            target = contained_path(child)
            if target.parent != root or target == published:
                continue
            shutil.rmtree(target, ignore_errors=True)
