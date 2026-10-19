"""Native UI/API development. Real asynchronous jobs still require Redis and the Spark worker."""

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / "scripts" / "bootstrap.py")], check=True)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(root / "data" / "development.sqlite3"))
os.environ.setdefault("DATA_DIR", str(root / "data"))
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ.setdefault("CACHE_URL", "redis://127.0.0.1:6379/2")
os.environ.setdefault("SPARK_MASTER", "local[2]")
os.environ.setdefault("SPARK_DRIVER_HOST", "")
os.environ.setdefault("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
subprocess.run([sys.executable, str(root / "backend" / "manage.py"), "migrate", "--noinput"], check=True)
subprocess.run(
    [sys.executable, str(root / "backend" / "manage.py"), "runserver", "127.0.0.1:8000", "--noreload"],
    check=True,
)
