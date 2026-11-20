import json
import subprocess
from types import SimpleNamespace

import pytest

from pagecheck.application.use_cases.external_engines import combine_engines
from pagecheck.integrations.cli_runner import local_binary, run_local_json_command
from pagecheck.integrations.engine_result import result


def test_missing_binary(tmp_path):
    assert local_binary(tmp_path, "lighthouse") is None


def test_unknown_binary_rejected(tmp_path):
    with pytest.raises(ValueError):
        local_binary(tmp_path, "curl")


def test_impeccable_exit_2_is_success(tmp_path):
    obj = [{"ruleId":"small-text", "message":"Tiny text"}]
    def fake(*args, **kwargs):
        assert kwargs["timeout"] == 90
        return SimpleNamespace(returncode=2, stdout=json.dumps(obj), stderr="")
    r = run_local_json_command("impeccable", ["impeccable", "detect"], root=tmp_path, run=fake)
    assert r["status"] == "completed" and len(r["findings"]) == 1


def test_impeccable_exit_1_is_not_verified(tmp_path):
    def fake(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="[]", stderr="error")
    r = run_local_json_command("impeccable", ["impeccable"], root=tmp_path, run=fake)
    assert r["status"] == "not_verified"


def test_lighthouse_invalid_json_is_not_verified(tmp_path):
    def fake(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="broken", stderr="")
    r = run_local_json_command("lighthouse", ["lighthouse"], root=tmp_path, run=fake)
    assert r["status"] == "not_verified"


def test_subprocess_timeout_isolated(tmp_path):
    def fake(*args, **kwargs):
        raise subprocess.TimeoutExpired("test", 5)
    r = run_local_json_command("lighthouse", ["lighthouse"], root=tmp_path, run=fake)
    assert r["status"] == "not_verified"


def test_combiner_is_partial_when_one_engine_fails():
    x = combine_engines({"axe": result("axe")})
    assert x["status"] == "partial"
    assert x["engines"]["impeccable"]["status"] == "not_verified"


def test_combiner_all_available():
    x = combine_engines({n: result(n) for n in ("axe", "impeccable")})
    assert x["status"] == "completed"


def test_combiner_none():
    assert combine_engines({})["status"] == "not_verified"
