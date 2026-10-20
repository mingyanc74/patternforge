import base64
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "cloud_preflight", Path(__file__).resolve().parents[2] / "scripts/cloud_preflight.py"
)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def valid_config():
    return {
        "DOMAIN": "demo.my-host.org",
        "DJANGO_SECRET_KEY": "a" * 64,
        "POSTGRES_PASSWORD": "b" * 32,
        "CREDENTIAL_KEY": base64.urlsafe_b64encode(bytes(range(32))).decode(),
        "FLOWER_BASIC_AUTH": "admin:" + "c" * 32,
    }


def test_valid_production_inputs():
    assert preflight.check_config(valid_config()) == []


@pytest.mark.parametrize("domain", ["", "127.0.0.1", "https://demo.org", "*.demo.org", "app.test"])
def test_reject_invalid_production_hostname(domain):
    assert preflight.check_config({**valid_config(), "DOMAIN": domain})


def test_preflight_does_not_expose_bad_secret_values():
    errors = preflight.check_config(
        {**valid_config(), "CREDENTIAL_KEY": "private-bad-key", "S3_ENDPOINT_URL": "http://fixtures:5000"}
    )
    assert len(errors) == 2
    assert "private-bad-key" not in str(errors)


def test_reject_public_internal_ports_and_fixture_compose():
    errors = preflight.check_compose(
        {"services": {"redis": {"ports": [{"published": "6379"}]}, "fixtures": {}}}
    )
    assert any("loopback" in error for error in errors)
    assert any("fixtures" in error for error in errors)
