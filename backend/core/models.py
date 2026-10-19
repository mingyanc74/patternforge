import uuid

from django.db import models


class S3Connection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=64, db_index=True)
    bucket = models.CharField(max_length=255)
    region = models.CharField(max_length=64, default="us-east-1")
    ciphertext = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    disconnected_at = models.DateTimeField(null=True, blank=True)


class Job(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED"
        RUNNING = "RUNNING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        CANCELLED = "CANCELLED"

    TERMINAL = (Status.SUCCESS, Status.FAILED, Status.CANCELLED)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=64, db_index=True)
    connection = models.ForeignKey(S3Connection, on_delete=models.PROTECT)
    kind = models.CharField(max_length=16, default="transform")
    source_key = models.CharField(max_length=1024)
    source_fingerprint = models.JSONField(default=dict)
    config = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    stage = models.CharField(max_length=64, default="QUEUED")
    progress = models.PositiveSmallIntegerField(default=0)
    attempt = models.PositiveSmallIntegerField(default=0)
    lease = models.UUIDField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    plan = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    manifest = models.CharField(max_length=1024, blank=True)
    result_expires_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=128, null=True, blank=True)
    request_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["owner", "idempotency_key"], name="job_owner_idem")]


class Outbox(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, primary_key=True)
    available_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
