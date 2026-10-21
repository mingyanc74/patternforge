import hashlib
import json
import socket
import uuid
from datetime import timedelta
from urllib.parse import urlparse

import redis
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import signing
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import AppError
from core.models import Job, Outbox, S3Connection
from core.sample_bucket import CATALOG
from core.security import encrypt_credentials
from core.serializers import ConnectionInput, FileInput, JobInput
from core.services.results import read_page
from core.services.s3 import call_s3, client_for, fingerprint


def owner(request):
    if "owner" not in request.session:
        request.session["owner"] = uuid.uuid4().hex
    return request.session["owner"]


def live_connection(request, connection_id):
    item = get_object_or_404(S3Connection, id=connection_id, owner=owner(request))
    if (
        item.disconnected_at
        or item.expires_at <= timezone.now()
        or (item.source_type != "sample" and not item.ciphertext)
    ):
        raise AppError("CONNECTION_EXPIRED", "This connection expired. Connect to S3 again.", 410)
    return item


def serialize_job(job, full=True):
    value = {
        "id": str(job.id),
        "kind": job.kind,
        "source_key": job.source_key,
        "connection_id": str(job.connection_id),
        "bucket": job.connection.bucket,
        "region": job.connection.region,
        "source_type": job.connection.source_type,
        "operation": job.config.get("operation"),
        "sheet": job.config.get("sheet", ""),
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "progress_kind": "stage_estimate",
        "attempt": job.attempt,
        "cancel_requested": bool(job.cancel_requested_at),
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "result_expires_at": job.result_expires_at,
        "result_available": bool(job.manifest),
        "error": {"code": job.error_code, "message": job.error_message} if job.error_code else None,
    }
    if full:
        value.update(config=job.config, plan=job.plan, metadata=job.metadata)
    return value


class SessionView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # DRF's default only checks CSRF for authenticated accounts; anonymous owner sessions also need it.
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            SessionAuthentication().enforce_csrf(request)


class Bootstrap(SessionView):
    def get(self, request):
        owner(request)
        return Response(
            {
                "csrf_token": get_token(request),
                "llm_configured": bool(settings.LLM_API_KEY and settings.LLM_MODEL),
                "sample_bucket_enabled": settings.SAMPLE_BUCKET_ENABLED,
                "limits": {
                    "preview_rows": 100,
                    "max_page_rows": 500,
                    "max_file_bytes": settings.MAX_FILE_BYTES,
                    "max_excel_bytes": settings.MAX_EXCEL_BYTES,
                    "result_ttl_hours": settings.RESULT_TTL_HOURS,
                },
                "supported_operations": ["regex_replace", "regex_extract", "normalize"],
            }
        )


class Health(APIView):
    throttle_classes = []

    def get(self, request):
        services = {
            "database": False,
            "queue": False,
            "worker": False,
            "spark": False,
            "llm_configured": bool(settings.LLM_API_KEY and settings.LLM_MODEL),
        }
        try:
            connection.ensure_connection()
            services["database"] = True
        except Exception:
            pass
        try:
            services["queue"] = bool(
                redis.Redis.from_url(
                    settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5
                ).ping()
            )
        except redis.RedisError:
            pass
        try:
            services["worker"] = bool(
                redis.Redis.from_url(settings.CACHE_URL, socket_connect_timeout=0.3, socket_timeout=0.3).get(
                    "patternforge:worker-heartbeat"
                )
            )
        except redis.RedisError:
            pass
        if settings.SPARK_MASTER.startswith("local"):
            services["spark"] = True
        else:
            try:
                master = urlparse(settings.SPARK_MASTER)
                with socket.create_connection((master.hostname, master.port or 7077), timeout=0.3):
                    services["spark"] = True
            except (OSError, ValueError):
                pass
        return Response(
            {"status": "ready" if all(services.values()) else "setup_required", "services": services}
        )


class Connections(SessionView):
    def get(self, request):
        connections = S3Connection.objects.filter(
            owner=owner(request), disconnected_at__isnull=True, expires_at__gt=timezone.now()
        )
        return Response(
            {
                "connections": [
                    {
                        "id": str(item.id),
                        "bucket": item.bucket,
                        "region": item.region,
                        "source_type": item.source_type,
                        "expires_at": item.expires_at,
                    }
                    for item in connections
                ]
            }
        )

    def post(self, request):
        serializer = ConnectionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data
        credentials = {name: fields.get(name, "") for name in ("access_key", "secret_key", "session_token")}
        client = client_for(credentials=credentials, region=fields["region"])
        info = call_s3(client.head_bucket, Bucket=fields["bucket"])
        region = (
            info.get("ResponseMetadata", {})
            .get("HTTPHeaders", {})
            .get("x-amz-bucket-region", fields["region"])
        )
        call_s3(client.list_objects_v2, Bucket=fields["bucket"], MaxKeys=1)
        if S3Connection.objects.filter(owner=owner(request), disconnected_at__isnull=True).count() >= 20:
            raise AppError(
                "CONNECTION_LIMIT", "Disconnect an existing connection before creating another.", 429
            )
        item = S3Connection.objects.create(
            owner=owner(request),
            bucket=fields["bucket"],
            region=region,
            ciphertext=encrypt_credentials(credentials),
            expires_at=timezone.now() + timedelta(hours=settings.CREDENTIAL_TTL_HOURS),
        )
        return Response(
            serialize_connection(item),
            status=201,
        )


def serialize_connection(item):
    return {
        "id": str(item.id),
        "bucket": item.bucket,
        "region": item.region,
        "source_type": item.source_type,
        "expires_at": item.expires_at,
    }


class SampleConnection(SessionView):
    def post(self, request):
        if not settings.SAMPLE_BUCKET_ENABLED:
            raise AppError("SAMPLE_DISABLED", "The sample bucket is disabled on this server.", 404)
        # Never accept credentials, paths, bucket names or endpoints for this adapter.
        if request.data:
            raise AppError("INVALID_SAMPLE_REQUEST", "The sample connection takes no parameters.")
        from core.sample_bucket import BUCKET, REGION

        identity = owner(request)
        with transaction.atomic():
            if not request.session.session_key:
                request.session.save()
            Session.objects.select_for_update().get(session_key=request.session.session_key)
            item = S3Connection.objects.filter(
                owner=identity,
                source_type="sample",
                disconnected_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if item:
                return Response(serialize_connection(item))
            if S3Connection.objects.filter(owner=identity, disconnected_at__isnull=True).count() >= 20:
                raise AppError("CONNECTION_LIMIT", "Disconnect an existing connection first.", 429)
            item = S3Connection.objects.create(
                owner=identity,
                bucket=BUCKET,
                region=REGION,
                source_type="sample",
                ciphertext="",
                expires_at=timezone.now() + timedelta(hours=settings.CREDENTIAL_TTL_HOURS),
            )
        return Response(serialize_connection(item), status=201)


class Disconnect(SessionView):
    def delete(self, request, connection_id):
        item = get_object_or_404(S3Connection, id=connection_id, owner=owner(request))
        item.disconnected_at = timezone.now()
        if not item.job_set.filter(status__in=[Job.Status.QUEUED, Job.Status.RUNNING]).exists():
            item.ciphertext = ""
        item.save()
        return Response(status=204)


class Files(SessionView):
    def get(self, request, connection_id):
        item = live_connection(request, connection_id)
        prefix = request.query_params.get("prefix", "")
        cursor = request.query_params.get("cursor")
        args = {"Bucket": item.bucket, "Prefix": prefix, "MaxKeys": 100}
        if len(prefix) > 1024:
            raise AppError("INVALID_PREFIX", "The path prefix is too long.")
        if cursor:
            try:
                data = signing.loads(cursor, salt="s3-files", max_age=3600)
                if (
                    data["connection"] != str(item.id)
                    or data["owner"] != item.owner
                    or data["prefix"] != prefix
                ):
                    raise ValueError
                args["ContinuationToken"] = data["token"]
            except (signing.BadSignature, KeyError, ValueError, TypeError):
                raise AppError("INVALID_CURSOR", "The file page expired. Refresh the list.") from None
        result = call_s3(client_for(item).list_objects_v2, **args)
        next_cursor = None
        if result.get("NextContinuationToken"):
            next_cursor = signing.dumps(
                {
                    "connection": str(item.id),
                    "owner": item.owner,
                    "prefix": prefix,
                    "token": result["NextContinuationToken"],
                },
                salt="s3-files",
                compress=True,
            )
        return Response(
            {
                "files": [
                    {
                        "key": entry["Key"],
                        "size": entry["Size"],
                        "modified": entry["LastModified"],
                        "supported": entry["Key"].lower().endswith((".csv", ".xlsx")),
                        **(
                            {"description": CATALOG.get(entry["Key"], "")}
                            if item.source_type == "sample"
                            else {}
                        ),
                    }
                    for entry in result.get("Contents", [])
                    if not entry["Key"].endswith("/")
                ],
                "next_cursor": next_cursor,
            }
        )


def create_job(request, fields, kind):
    identity = owner(request)
    item = live_connection(request, fields["connection_id"])
    config = {
        key: value
        for key, value in fields.items()
        if key not in {"connection_id", "source_key", "inspection_id"}
    }
    if kind == "transform":
        config["inspection_id"] = str(fields["inspection_id"])
    request_hash = hashlib.sha256(
        json.dumps(
            {"connection": str(item.id), "key": fields["source_key"], "kind": kind, "config": config},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    idem = request.headers.get("Idempotency-Key")
    if idem and len(idem) > 128:
        raise AppError("INVALID_IDEMPOTENCY_KEY", "The idempotency key is too long.")
    if idem:
        previous = Job.objects.filter(owner=identity, idempotency_key=idem).first()
        if previous:
            if previous.request_hash != request_hash:
                raise AppError(
                    "IDEMPOTENCY_CONFLICT",
                    "This request key was already used with different parameters.",
                    409,
                )
            return previous
    if kind == "transform":
        inspect = get_object_or_404(
            Job,
            id=fields["inspection_id"],
            owner=identity,
            kind="inspect",
            status=Job.Status.SUCCESS,
            connection=item,
            source_key=fields["source_key"],
        )
        if inspect.result_expires_at and inspect.result_expires_at <= timezone.now():
            raise AppError("INSPECTION_EXPIRED", "Inspect the file again before processing.", 410)
        if inspect.metadata.get("requires_sheet"):
            raise AppError("SHEET_REQUIRED", "Select a worksheet and inspect it first.")
        for option in ("sheet", "delimiter", "encoding"):
            actual = (
                inspect.metadata.get("sheet", inspect.config.get("sheet", ""))
                if option == "sheet"
                else inspect.config.get(option)
            )
            if config.get(option, "") != (actual or ""):
                raise AppError("INSPECTION_MISMATCH", "Parsing options changed. Inspect the file again.")
        columns = {col["name"] for col in inspect.metadata["columns"]}
        if not set(config["target_columns"]).issubset(columns):
            raise AppError("COLUMN_NOT_FOUND", "Select existing columns from the preview.")
        if config["operation"] == "regex_extract" and config["new_column"].casefold() in {
            c.casefold() for c in columns
        }:
            raise AppError("COLUMN_CONFLICT", "Choose a new column name.")
        source_info = inspect.source_fingerprint
    else:
        source_info = fingerprint(client_for(item), item.bucket, fields["source_key"])
    try:
        with transaction.atomic():
            # Lock the owner connection to serialize submissions and enforce a bounded queue per session.
            if not request.session.session_key:
                request.session.save()
            Session.objects.select_for_update().get(session_key=request.session.session_key)
            if (
                Job.objects.filter(owner=identity, status__in=[Job.Status.QUEUED, Job.Status.RUNNING]).count()
                >= settings.MAX_ACTIVE_JOBS_PER_SESSION
            ):
                raise AppError("JOB_LIMIT", "You have too many active jobs. Wait or cancel one.", 429)
            job = Job.objects.create(
                owner=identity,
                connection=item,
                source_key=fields["source_key"],
                kind=kind,
                config=config,
                source_fingerprint=source_info,
                idempotency_key=idem,
                request_hash=request_hash,
            )
            Outbox.objects.create(job=job, available_at=timezone.now())
            return job
    except IntegrityError:
        previous = Job.objects.filter(owner=identity, idempotency_key=idem).first()
        if previous and previous.request_hash == request_hash:
            return previous
        raise AppError("IDEMPOTENCY_CONFLICT", "This request key was already used.", 409) from None


class Inspect(SessionView):
    def post(self, request):
        serializer = FileInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_job(request, serializer.validated_data, "inspect")
        return Response({**serialize_job(job), "status_url": f"/api/jobs/{job.id}"}, status=202)


class Jobs(SessionView):
    def get(self, request):
        params = request.query_params
        try:
            page, limit = int(params.get("page", "1")), int(params.get("limit", "50"))
            if not 1 <= page <= 100000 or not 1 <= limit <= 50:
                raise ValueError
        except ValueError:
            raise AppError(
                "INVALID_PAGINATION", "Choose a valid page and a page size from 1 to 50."
            ) from None
        jobs = Job.objects.filter(owner=owner(request)).select_related("connection")
        kind = params.get("kind", "")
        if kind:
            if kind not in {"inspect", "transform"}:
                raise AppError("INVALID_FILTER", "Choose a valid job kind.")
            jobs = jobs.filter(kind=kind)
        status = params.get("status", "")
        if status == "expired":
            jobs = jobs.filter(status=Job.Status.SUCCESS, kind="transform").filter(
                Q(result_expires_at__lte=timezone.now()) | Q(manifest="")
            )
        elif status:
            if status not in Job.Status.values:
                raise AppError("INVALID_FILTER", "Choose a valid job status.")
            jobs = jobs.filter(status=status)
        query = params.get("search", "").strip()
        if len(query) > 128:
            raise AppError("INVALID_FILTER", "Search text must be at most 128 characters.")
        if query:
            jobs = jobs.filter(Q(source_key__icontains=query) | Q(id__icontains=query.replace("-", "")))
        count = jobs.count()
        start = (page - 1) * limit
        return Response(
            {
                "jobs": [
                    serialize_job(job, full=False)
                    for job in jobs.order_by("-created_at", "-id")[start : start + limit]
                ],
                "total": count,
                "page": page,
                "page_size": limit,
                "has_next": start + limit < count,
            }
        )

    def post(self, request):
        serializer = JobInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_job(request, serializer.validated_data, "transform")
        return Response({**serialize_job(job), "status_url": f"/api/jobs/{job.id}"}, status=202)


class JobDetail(SessionView):
    def get(self, request, job_id):
        return Response(serialize_job(get_object_or_404(Job, id=job_id, owner=owner(request))))


class Cancel(SessionView):
    def post(self, request, job_id):
        with transaction.atomic():
            job = get_object_or_404(Job.objects.select_for_update(), id=job_id, owner=owner(request))
            if job.status not in Job.TERMINAL:
                job.cancel_requested_at = job.cancel_requested_at or timezone.now()
                if job.status == Job.Status.QUEUED:
                    job.status, job.stage, job.finished_at = Job.Status.CANCELLED, "CANCELLED", timezone.now()
                else:
                    job.stage = "CANCELLING"
                job.save()
        return Response(serialize_job(job))


class Results(SessionView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id, owner=owner(request), kind="transform")
        if job.status != Job.Status.SUCCESS:
            raise AppError("RESULT_NOT_READY", "Results are available only after successful processing.", 409)
        if not job.result_expires_at or job.result_expires_at <= timezone.now() or not job.manifest:
            raise AppError("RESULT_EXPIRED", "This result expired. Submit the processing request again.", 410)
        try:
            limit = int(request.query_params.get("limit", "100"))
            if not 1 <= limit <= 500:
                raise ValueError
        except ValueError:
            raise AppError("INVALID_PAGE_SIZE", "Page size must be between 1 and 500.") from None
        return Response(read_page(job, request.query_params.get("cursor"), limit))


class Metrics(APIView):
    throttle_classes = []

    def get(self, request):
        registry = CollectorRegistry()
        counts = Gauge("patternforge_jobs", "Persisted jobs by status", ["status"], registry=registry)
        for status in Job.Status.values:
            counts.labels(status=status).set(Job.objects.filter(status=status).count())
        pending = Gauge("patternforge_outbox_pending", "Jobs awaiting broker publication", registry=registry)
        pending.set(Outbox.objects.filter(sent_at__isnull=True, job__status=Job.Status.QUEUED).count())
        cached = Gauge(
            "patternforge_cached_plans", "Completed transformations that reused a plan", registry=registry
        )
        cached.set(
            Job.objects.filter(kind="transform", status=Job.Status.SUCCESS, metadata__cache_hit=True).count()
        )
        retries = Gauge(
            "patternforge_retry_attempts",
            "Total additional attempts in the latest 1000 jobs",
            registry=registry,
        )
        latest = list(Job.objects.order_by("-created_at")[:1000])
        retries.set(sum(max(0, item.attempt - 1) for item in latest))
        runtime = Gauge(
            "patternforge_job_runtime_seconds",
            "Recent completed runtime summary",
            ["stat"],
            registry=registry,
        )
        durations = [
            (item.finished_at - item.started_at).total_seconds()
            for item in latest
            if item.started_at and item.finished_at
        ]
        runtime.labels(stat="count").set(len(durations))
        runtime.labels(stat="sum").set(sum(durations))
        queued = Gauge(
            "patternforge_queue_wait_seconds",
            "Recent started queue wait summary",
            ["stat"],
            registry=registry,
        )
        waits = [(item.started_at - item.created_at).total_seconds() for item in latest if item.started_at]
        queued.labels(stat="count").set(len(waits))
        queued.labels(stat="sum").set(sum(waits))
        return HttpResponse(generate_latest(registry), content_type="text/plain; version=0.0.4")
