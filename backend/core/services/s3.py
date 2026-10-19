from pathlib import PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from core.errors import PipelineError
from core.security import decrypt_credentials


def client_for(connection=None, credentials=None, region=None):
    credentials = credentials or decrypt_credentials(connection.ciphertext)
    endpoint = settings.S3_ENDPOINT_URL or None
    if endpoint and endpoint.startswith("http:") and not settings.S3_ALLOW_HTTP:
        raise PipelineError("INSECURE_ENDPOINT", "HTTP S3 endpoints are disabled.")
    return boto3.client(
        "s3",
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"],
        aws_session_token=credentials.get("session_token") or None,
        region_name=region or getattr(connection, "region", "us-east-1"),
        endpoint_url=endpoint,
        config=Config(
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 2},
            s3={"addressing_style": "path" if endpoint else "auto"},
        ),
    )


def safe_s3_error(error):
    if isinstance(error, ClientError):
        code = str(error.response.get("Error", {}).get("Code", ""))
        if code in {"InvalidAccessKeyId", "SignatureDoesNotMatch", "InvalidToken", "ExpiredToken"}:
            return PipelineError("S3_CREDENTIALS_INVALID", "AWS credentials are invalid or expired.")
        if code in {"AccessDenied", "403", "Forbidden"}:
            return PipelineError(
                "S3_ACCESS_DENIED", "Bucket or object is inaccessible. Check its name and read permissions."
            )
        if code in {"NoSuchBucket", "NoSuchKey", "404", "NotFound"}:
            return PipelineError("S3_NOT_FOUND", "The bucket or object was not found, or is not accessible.")
        if code in {"SlowDown", "RequestTimeout", "InternalError", "ServiceUnavailable", "500", "503"}:
            return PipelineError("S3_TEMPORARY_ERROR", "S3 is temporarily unavailable. Please retry.", True)
        return PipelineError(
            "S3_REQUEST_FAILED", "S3 could not complete this request. Check region and permissions."
        )
    return PipelineError("S3_UNREACHABLE", "S3 could not be reached. Check network and region.", True)


def call_s3(call, **kwargs):
    try:
        return call(**kwargs)
    except (BotoCoreError, ClientError) as exc:
        raise safe_s3_error(exc) from None


def fingerprint(client, bucket, key):
    info = call_s3(client.head_object, Bucket=bucket, Key=key)
    if info["ContentLength"] == 0:
        raise PipelineError("EMPTY_FILE", "The selected file is empty. Choose a file with a header and data.")
    if info["ContentLength"] > settings.MAX_FILE_BYTES:
        raise PipelineError("FILE_TOO_LARGE", "The file exceeds the configured size limit.")
    suffix = PurePosixPath(key).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise PipelineError("UNSUPPORTED_FILE", "Choose a CSV or .xlsx Excel file.")
    if suffix == ".xlsx" and info["ContentLength"] > settings.MAX_EXCEL_BYTES:
        raise PipelineError("EXCEL_TOO_LARGE", "The Excel file exceeds the configured Excel limit.")
    return {
        "etag": info.get("ETag", ""),
        "size": info["ContentLength"],
        "modified": info["LastModified"].isoformat(),
        "version_id": info.get("VersionId", ""),
    }


def ensure_unchanged(connection, key, expected):
    current = fingerprint(client_for(connection), connection.bucket, key)
    if current != expected:
        raise PipelineError("SOURCE_CHANGED", "The source file changed. Inspect it again before processing.")
