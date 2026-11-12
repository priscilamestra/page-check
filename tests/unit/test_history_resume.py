"""Deterministic tests for restoring a saved report after browser refresh."""

import pytest

from pagecheck.ui.history_resume import (
    clear_active_audit, remember_active_audit, resume_active_audit, valid_audit_id,
)

AUDIT_A = "a" * 32
AUDIT_B = "b" * 32


def test_audit_id_only_accepts_local_history_hex_identifier():
    assert valid_audit_id(AUDIT_A) == AUDIT_A
    for bad in (None, "../etc/passwd", "a" * 31, "A" * 32, "a" * 33, [AUDIT_A]):
        assert valid_audit_id(bad) is None


def test_open_saved_audit_keeps_only_id_in_query():
    session, query = {"pagecheck_report": {"secret": "local"}}, {"lang": "en"}
    remember_active_audit(session, query, AUDIT_A)
    assert query == {"lang": "en", "audit": AUDIT_A}
    assert session["pagecheck_active_history_id"] == AUDIT_A
    assert "secret" not in str(query)


def test_f5_new_session_restores_same_report_without_rerunning_audit():
    query = {"audit": AUDIT_B}
    new_session = {}
    calls = []
    def load(audit_id):
        calls.append(audit_id)
        return {"requested_url": "https://example.com/old"}
    assert resume_active_audit(new_session, query, load)
    assert new_session["pagecheck_report"]["requested_url"] == "https://example.com/old"
    assert new_session["pagecheck_origin"] == "Saved audit · local history"
    assert calls == [AUDIT_B]
    assert not resume_active_audit(new_session, query, load)
    assert calls == [AUDIT_B]


def test_change_audit_id_loads_requested_report_not_previous_one():
    session, query = {}, {"audit": AUDIT_A}
    calls = []
    def load(value):
        calls.append(value)
        return {"id": value}
    resume_active_audit(session, query, load)
    query["audit"] = AUDIT_B
    assert resume_active_audit(session, query, load)
    assert session["pagecheck_report"]["id"] == AUDIT_B
    assert calls == [AUDIT_A, AUDIT_B]


def test_invalid_query_is_ignored_and_removed_without_fetch():
    session, query = {}, {"audit": "../../secrets"}
    assert not resume_active_audit(session, query, lambda _: pytest.fail("must not fetch"))
    assert query == {}


def test_no_query_does_not_auto_open_the_newest_audit():
    assert not resume_active_audit({}, {}, lambda _: pytest.fail("must not fetch"))


def test_missing_saved_audit_does_not_modify_existing_report():
    session, query = {"pagecheck_report": {"id": "old"}}, {"audit": AUDIT_B}
    def load(_):
        raise ValueError("not found")
    with pytest.raises(ValueError):
        resume_active_audit(session, query, load)
    assert session["pagecheck_report"] == {"id": "old"}


def test_switch_to_imported_report_clears_old_history_reference():
    session, query = {"pagecheck_active_history_id": AUDIT_A}, {"audit": AUDIT_A, "lang": "en"}
    clear_active_audit(session, query)
    assert query == {"lang": "en"}
    assert "pagecheck_active_history_id" not in session


def test_remember_active_audit_rejects_invalid_id():
    session, query = {}, {}
    with pytest.raises(ValueError):
        remember_active_audit(session, query, "not-an-id")
    assert session == query == {}
