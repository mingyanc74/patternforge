import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
CREDENTIAL_KEY = os.getenv("CREDENTIAL_KEY", "")
if not SECRET_KEY or not CREDENTIAL_KEY:
    raise ImproperlyConfigured("Run python scripts/bootstrap.py to create local secrets first.")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = list(filter(None, os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")))
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.SafeErrorMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []
db_url = os.getenv("DATABASE_URL", "sqlite:///" + str(BASE_DIR.parent / "data" / "development.sqlite3"))
if db_url.startswith("sqlite:"):
    db_path = db_url.removeprefix("sqlite:///")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": db_path, "OPTIONS": {"timeout": 20}}
    }
else:
    parsed = urlparse(db_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname,
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": 60,
        }
    }
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 7 * 24 * 3600
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0") == "1"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR.parent / DATA_DIR
DATA_DIR = DATA_DIR.resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_URL = os.getenv("CACHE_URL", "redis://127.0.0.1:6379/2")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = os.getenv("RESULT_BACKEND_URL", "redis://127.0.0.1:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_RESULT_EXPIRES = 86400
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 7200,
    "socket_timeout": 3,
    "socket_connect_timeout": 3,
}
CELERY_TASK_DEFAULT_QUEUE = "processing"
CELERY_TASK_ROUTES = {
    "core.tasks.maintenance": {"queue": "control"},
    "core.tasks.dispatch_pending": {"queue": "control"},
}
CELERY_BEAT_SCHEDULE = {
    "dispatch-outbox": {"task": "core.tasks.dispatch_pending", "schedule": 5.0},
    "recover-and-clean": {"task": "core.tasks.maintenance", "schedule": 30.0},
}
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_JSON_SCHEMA = os.getenv("LLM_JSON_SCHEMA", "1") == "1"
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[2]")
SPARK_DRIVER_HOST = os.getenv("SPARK_DRIVER_HOST", "")
SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "1g")
SPARK_EXECUTOR_MEMORY = os.getenv("SPARK_EXECUTOR_MEMORY", "1g")
SPARK_PARTITIONS = int(os.getenv("SPARK_PARTITIONS", "8"))
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
S3_ALLOW_HTTP = os.getenv("S3_ALLOW_HTTP", "0") == "1"
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(2 * 1024**3)))
MAX_EXCEL_BYTES = int(os.getenv("MAX_EXCEL_BYTES", str(100 * 1024**2)))
MAX_EXCEL_ROWS = int(os.getenv("MAX_EXCEL_ROWS", "1048576"))
MAX_CELL_CHARS = int(os.getenv("MAX_CELL_CHARS", "65536"))
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "1800"))
RESULT_TTL_HOURS = int(os.getenv("RESULT_TTL_HOURS", "24"))
TEMP_TTL_HOURS = int(os.getenv("TEMP_TTL_HOURS", "24"))
CREDENTIAL_TTL_HOURS = int(os.getenv("CREDENTIAL_TTL_HOURS", "24"))
MAX_ACTIVE_JOBS_PER_SESSION = int(os.getenv("MAX_ACTIVE_JOBS_PER_SESSION", "3"))
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "core.errors.exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "300/min"},
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"safe": {"()": "core.security.RedactingFilter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["safe"]}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "botocore": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
        "py4j": {"level": "WARNING"},
    },
}
