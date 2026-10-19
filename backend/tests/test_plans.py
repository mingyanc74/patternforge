import copy
from unittest.mock import MagicMock

import fakeredis
import pytest
from core.errors import PipelineError
from core.models import Job
from core.services.plans import get_plan, validate_java_pattern, validate_plan


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
