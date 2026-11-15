"""Unrecognized Impeccable output must remain unverified with useful schema info."""
from types import SimpleNamespace

import pytest

from pagecheck.integrations.engine_result import EngineOutputError
from pagecheck.integrations.impeccable.adapter import normalize_impeccable
from pagecheck.integrations.cli_runner import run_local_json_command


def test_missing_rule_reports_record_number_not_raw_values():
    payload = [{"ruleId": "valid"}, {"message": "PRIVATE CONTENT", "severity": "warning"}]
    with pytest.raises(EngineOutputError) as err:
        normalize_impeccable(payload)
    assert "finding #2" in str(err.value)
    assert "message" in str(err.value)
    assert "PRIVATE CONTENT" not in str(err.value)


def test_unknown_schema_fails_without_fabricating_results(tmp_path):
    def completed(*args, **kwargs):
        return SimpleNamespace(returncode=2, stdout='[{"message":"SECRET","severity":"warning"}]')
    result = run_local_json_command(
        "impeccable", ["impeccable", "detect", "--json", "snapshot.html"],
        root=tmp_path, run=completed,
    )
    assert result["status"] == "not_verified"
    assert result["findings"] == []
    assert "finding #1" in result["limitations"][0]
    assert "SECRET" not in result["limitations"][0]


def test_valid_impeccable_still_reports_completed():
    assert normalize_impeccable([{"ruleId": "small-text"}])["status"] == "completed"
