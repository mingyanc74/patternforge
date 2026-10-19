import base64
import os

os.environ["DJANGO_SECRET_KEY"] = "test-only-not-for-deployment"
os.environ["CREDENTIAL_KEY"] = base64.urlsafe_b64encode(b"0" * 32).decode()
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DJANGO_DEBUG"] = "1"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
from .settings import *  # noqa: E402,F403

REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
