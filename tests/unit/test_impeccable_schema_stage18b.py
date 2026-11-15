import pytest
from pagecheck.integrations.impeccable.adapter import normalize_impeccable
from pagecheck.integrations.engine_result import EngineOutputError


def test_impeccable_snake_case_identifier():
    result = normalize_impeccable([{"rule_id": "gradient-text", "message": "avoid", "severity": "warning"}])
    assert result["status"] == "completed"
    assert result["findings"][0]["evidence"]["rule_id"] == "gradient-text"


def test_impeccable_nested_rule_key_and_exit_concept():
    result = normalize_impeccable({"findings": [{"rule": {"key": "small-text"}, "severity": "info"}]})
    assert result["findings"][0]["severity"] == "low"


def test_unknown_schema_not_silently_made_up():
    with pytest.raises(EngineOutputError):
        normalize_impeccable([{"message": "a problem", "line": 4}])


def test_empty_findings_count_as_completed():
    result = normalize_impeccable([])
    assert result["status"] == "completed" and result["metrics"]["findings"] == 0
