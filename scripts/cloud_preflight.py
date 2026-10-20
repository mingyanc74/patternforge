"""Read-only independent-host checks. Never print secrets or provision paid resources."""

import argparse
import base64
import ipaddress
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path


def check_config(values):
    """Validate the production overlay's required inputs, without displaying their values."""
    errors = []
    domain = values.get("DOMAIN", "").strip()
    valid_domain = bool(
        re.fullmatch(
            r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
            r"[a-zA-Z]{2,63}",
            domain,
        )
    )
    try:
        ipaddress.ip_address(domain)
        valid_domain = False
    except ValueError:
        pass
    if not valid_domain or domain.endswith((".localhost", ".example", ".test")):
        errors.append("DOMAIN must be a real DNS hostname; bare IPs and URLs are not supported here.")
    for name, minimum in [("DJANGO_SECRET_KEY", 40), ("POSTGRES_PASSWORD", 24)]:
        value = values.get(name, "")
        if len(value) < minimum or value in {"patternforge", "change-me"}:
            errors.append(name + " must be a strong, independently generated private secret.")
    try:
        key = base64.urlsafe_b64decode(values.get("CREDENTIAL_KEY", "").encode())
        if len(key) != 32:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("CREDENTIAL_KEY must be a valid 32-byte Fernet key.")
    if values.get("S3_ENDPOINT_URL", "").strip():
        errors.append("Remove S3_ENDPOINT_URL for real Amazon S3 acceptance; test endpoints are not allowed.")
    if values.get("S3_ALLOW_HTTP", "0") != "0":
        errors.append("S3_ALLOW_HTTP must be 0 for the public deployment.")
    monitor = values.get("FLOWER_BASIC_AUTH", "")
    if ":" not in monitor or len(monitor.split(":", 1)[-1]) < 24 or "change-this" in monitor:
        errors.append("FLOWER_BASIC_AUTH must use a strong private password, even on loopback.")
    return errors


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values


def command_json(args, cwd):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise ValueError("Required Docker command failed; output withheld to protect configuration.")
    return json.loads(result.stdout)


def check_compose(config):
    errors = []
    services = config.get("services", {})
    for name, service in services.items():
        for port in service.get("ports", []):
            if name != "gateway" and port.get("host_ip") not in {"127.0.0.1", "::1"}:
                errors.append(name + ": non-gateway port must remain loopback-only.")
    web = services.get("web", {}).get("environment", {})
    for name, expected in [
        ("DJANGO_DEBUG", "0"),
        ("SESSION_COOKIE_SECURE", "1"),
        ("SECURE_SSL_REDIRECT", "1"),
    ]:
        if str(web.get(name)) != expected:
            errors.append(name + ": required secure production override is missing.")
    for name in ("web", "worker", "dispatcher"):
        env = services.get(name, {}).get("environment", {})
        if env.get("S3_ENDPOINT_URL") or env.get("S3_ALLOW_HTTP", "0") != "0":
            errors.append(name + ": synthetic/insecure S3 configuration is not allowed.")
        if env.get("LLM_BASE_URL") != "http://local-model:8089/v1":
            errors.append(name + ": must use the internal genuine model in this free-only deployment.")
    if "fixtures" in services:
        errors.append("CI provider fixtures must not be deployed publicly.")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-only", action="store_true", help="Skip Linux/Docker/resource checks")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not (root / ".env").is_file():
        raise SystemExit("Run scripts/bootstrap.py first. No configuration was changed.")
    errors = check_config(read_env(root / ".env"))
    if not args.config_only:
        if platform.system() != "Linux":
            errors.append("Run the full preflight on the independent Linux cloud host.")
        else:
            memory = int(Path("/proc/meminfo").read_text().split("MemTotal:")[1].split()[0]) * 1024
            if memory < 10 * 1024**3:
                errors.append(
                    "This full CPU-model stack targets at least 10 GiB total host RAM (12 GB class)."
                )
            if shutil.disk_usage(root).free < 20 * 1024**3:
                errors.append(
                    "At least 20 GiB free disk is needed before building images and downloading weights."
                )
        try:
            command_json(["docker", "info", "--format", "{{json .ServerVersion}}"], root)
            config = command_json(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    "compose.local-model.yml",
                    "-f",
                    "compose.production.yml",
                    "config",
                    "--format",
                    "json",
                ],
                root,
            )
            errors.extend(check_compose(config))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            errors.append("Docker Engine and Compose v2 must work; configuration output was not printed.")
    for error in errors:
        print("FAIL: " + error)
    if errors:
        raise SystemExit(1)
    print(
        "PASS: checked configuration only."
        if args.config_only
        else "PASS: host and merged configuration checks."
    )
    print("Not proof of ARM runtime, DNS, TLS, capacity, real AWS access, model quality or completed jobs.")
    print("Nothing was deployed or changed. Continue with the independent-cloud acceptance checklist.")


if __name__ == "__main__":
    main()
