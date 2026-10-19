from datetime import timedelta

import boto3
import pytest
from core.models import S3Connection
from core.security import encrypt_credentials
from django.utils import timezone
from moto import mock_aws
from rest_framework.test import APIClient


@pytest.fixture
def client(db):
    value = APIClient()
    value.get("/api/bootstrap")
    return value


@pytest.fixture
def bucket():
    with mock_aws():
        s3 = boto3.client(
            "s3", region_name="us-east-1", aws_access_key_id="test-user", aws_secret_access_key="test-secret"
        )
        s3.create_bucket(Bucket="user-owned-bucket")
        s3.put_object(
            Bucket="user-owned-bucket",
            Key="customers.csv",
            Body=b"ID,Name,Email\n001,John Doe,john.doe@example.com\n002,Jane Smith,jane@domain.com\n",
        )
        yield s3


@pytest.fixture
def saved_connection(client, bucket):
    return S3Connection.objects.create(
        owner=client.session["owner"],
        bucket="user-owned-bucket",
        region="us-east-1",
        ciphertext=encrypt_credentials(
            {"access_key": "test-user", "secret_key": "test-secret", "session_token": ""}
        ),
        expires_at=timezone.now() + timedelta(hours=1),
    )


@pytest.fixture
def data_dir(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    return tmp_path


@pytest.fixture
def email_plan():
    return {
        "operation": "regex_replace",
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}\b",
        "group": 0,
        "steps": [],
        "explanation": "Match email-like addresses.",
    }
