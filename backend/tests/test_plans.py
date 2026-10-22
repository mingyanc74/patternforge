import copy
from unittest.mock import MagicMock

import fakeredis
import pytest
from core.errors import PipelineError
from core.models import Job
from core.services.plans import get_plan, validate_java_pattern, validate_plan


def test_model_generation_schema_is_operation_specific():
    from core.services.plans import PLAN_SCHEMA, schema_for_operation

    replace = schema_for_operation("regex_replace")["properties"]
    assert replace["operation"]["enum"] == ["regex_replace"]
    assert replace["group"]["enum"] == [0]
    assert replace["steps"]["maxItems"] == 0
    normalize = schema_for_operation("normalize")["properties"]
    assert normalize["pattern"] == {"type": "null"}
    assert normalize["group"]["enum"] == [0]
    assert PLAN_SCHEMA["properties"]["operation"]["enum"] == ["regex_replace", "regex_extract", "normalize"]


@pytest.mark.parametrize("schema_mode", [True, False])
def test_model_request_keeps_data_and_credentials_private(email_plan, mocker, settings, schema_mode):
    import json

    from core.services.plans import request_plan

    settings.LLM_API_KEY = "test-only-key"
    settings.LLM_MODEL = "test-only-model"
    settings.LLM_JSON_SCHEMA = schema_mode
    http_client = mocker.patch("core.services.plans.httpx.Client").return_value.__enter__.return_value
    response = http_client.post.return_value
    response.status_code = 200
    response.is_success = True
    response.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(email_plan)}}]
    }
    # Keep a genuine Chinese instruction at runtime, not literal JSON escape text.
    config = {
        "operation": "regex_replace",
        "prompt": "\u8bc6\u522b\u6587\u672c\u4e2d\u7684\u7535\u5b50\u90ae\u7bb1\u5730\u5740",
        "target_columns": ["Email"],
        "replacement": "private-replacement",
        "preview": ["private-cell"],
        "secret_key": "private-aws",
    }
    assert request_plan(config) == email_plan
    payload = http_client.post.call_args.kwargs["json"]
    assert (
        "\u8bc6\u522b\u6587\u672c\u4e2d\u7684\u7535\u5b50\u90ae\u7bb1\u5730\u5740"
        in payload["messages"][-1]["content"]
    )
    assert "\\u8bc6" not in payload["messages"][-1]["content"]
    messages = json.dumps(payload["messages"])
    assert (
        "private-replacement" not in messages
        and "private-cell" not in messages
        and "private-aws" not in messages
    )
    assert payload["store"] is False
    if schema_mode:
        assert payload["response_format"]["json_schema"]["schema"]["properties"]["operation"]["enum"] == [
            "regex_replace"
        ]
    else:
        assert "Required JSON schema:" in payload["messages"][0]["content"]


@pytest.mark.parametrize("pattern", ["(", "a*", "(a+)+$", "(a|aa)+$", r"(a)\1", "(?=a)", ".*x"])
def test_rejects_invalid_empty_or_dangerous_regex(email_plan, pattern):
    plan = {**email_plan, "pattern": pattern}
    with pytest.raises(PipelineError):
        validate_plan(plan, "regex_replace")


def test_valid_email_and_normalization_plan(email_plan):
    assert validate_plan(email_plan, "regex_replace") == email_plan
    normalized = {
        "operation": "normalize",
        "pattern": None,
        "group": 0,
        "steps": ["trim", "collapse_whitespace", "lowercase"],
        "explanation": "Clean text.",
    }
    assert validate_plan(normalized, "normalize") == normalized
    with pytest.raises(PipelineError):
        validate_plan({**normalized, "steps": ["eval"]}, "normalize")
    with pytest.raises(PipelineError):
        validate_plan({**email_plan, "code": "import os"}, "regex_replace")


def test_llm_cannot_change_operation(email_plan):
    with pytest.raises(PipelineError):
        validate_plan(email_plan, "normalize")


def test_unspecified_or_refused_regex_requires_clarification(email_plan):
    with pytest.raises(PipelineError) as error:
        validate_plan(
            {**email_plan, "pattern": None, "explanation": "Specify the identifier format."}, "regex_replace"
        )
    assert error.value.code == "RULE_NEEDS_CLARIFICATION"
    assert "prefix" in error.value.message
    # The old cache version must not reuse rules generated under the guessing policy.
    from core.services.plans import VERSION

    assert VERSION == "plan-v1-safe-subset-3"


def test_java_real_engine_validation(email_plan):
    validate_java_pattern(email_plan)
    with pytest.raises(PipelineError):
        validate_java_pattern({**email_plan, "pattern": "["})


def test_cache_reuses_verified_plan_and_isolates_owner(saved_connection, email_plan, mocker, settings):
    settings.LLM_MODEL = "test-model"
    fake = fakeredis.FakeRedis(decode_responses=True)
    lock = MagicMock()
    lock.acquire.return_value = True
    mocker.patch.object(fake, "lock", return_value=lock)
    mocker.patch("core.services.plans.cache_client", return_value=fake)
    generate = mocker.patch("core.services.plans.request_plan", return_value=email_plan)
    java = mocker.patch("core.services.plans.validate_java_pattern")
    job = Job(
        owner=saved_connection.owner,
        config={"operation": "regex_replace", "prompt": "Find emails", "target_columns": ["Email"]},
    )
    assert get_plan(job)[1] is False
    assert get_plan(job)[1] is True
    assert generate.call_count == 1 and java.call_count == 1
    other = copy.copy(job)
    other.owner = "another-owner"
    assert get_plan(other)[1] is False
    assert generate.call_count == 2


def test_missing_llm_configuration_never_falls_back_to_sample(settings):
    from core.services.plans import request_plan

    settings.LLM_API_KEY = ""
    with pytest.raises(PipelineError, match="LLM_NOT_CONFIGURED"):
        request_plan({"operation": "regex_replace", "prompt": "email", "target_columns": ["email"]})


def test_refused_plan_is_never_cached_or_java_executed(saved_connection, email_plan, mocker):
    fake = fakeredis.FakeRedis(decode_responses=True)
    lock = MagicMock()
    lock.acquire.return_value = True
    mocker.patch.object(fake, "lock", return_value=lock)
    mocker.patch("core.services.plans.cache_client", return_value=fake)
    mocker.patch("core.services.plans.request_plan", return_value={**email_plan, "pattern": None})
    java = mocker.patch("core.services.plans.validate_java_pattern")
    job = Job(
        owner=saved_connection.owner,
        config={"operation": "regex_replace", "prompt": "Find custom IDs", "target_columns": ["Email"]},
    )
    with pytest.raises(PipelineError, match="RULE_NEEDS_CLARIFICATION"):
        get_plan(job)
    java.assert_not_called()
    assert not fake.keys("plan:*")
    lock.release.assert_called_once()
