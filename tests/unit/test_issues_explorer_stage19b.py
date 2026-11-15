"""19B: a long list of findings stays filterable, concise and evidence-preserving."""
from copy import deepcopy

import pytest

from pagecheck.ui.components.issues_explorer import (
    finding_rows, finding_summary, filter_findings, findings_table,
)


def sample_report():
    return {"findings": [
        {"id": "seo2", "module": "seo", "title": "Keyword review",
         "recommendation": "Review title", "severity": "low", "status": "warning",
         "team": "SEO", "evidence": {"keyword": "marketing automation"}},
        {"id": "axe1", "module": "accessibility", "title": "Button missing name",
         "recommendation": "Add accessible text", "severity": "critical", "status": "failed",
         "source": "axe", "team": "Frontend", "evidence": {"nodes": ["a", "b"]}},
        {"id": "nav1", "module": "navigation", "title": "Link without href",
         "recommendation": "Confirm JavaScript behavior", "severity": "medium",
         "status": "warning", "team": "Frontend", "evidence": {}},
        {"id": "unverified", "module": "navigation", "title": "Link not visited",
         "status": "not_verified", "severity": "critical", "evidence": {}},
    ]}


def test_priority_order_preserves_unknown_critical_unverified_as_non_issue():
    rows = finding_rows(sample_report())
    assert rows[0]["status"] == "failed"  # action first, despite critical unverified item
    assert finding_summary(rows)["critical_issues"] == 1
    assert finding_summary(rows)["issues"] == 1


def test_default_filters_out_unverified():
    assert [r["check_id"] for r in filter_findings(finding_rows(sample_report()))] == [
        "axe1", "nav1", "seo2"]


def test_summary_counts_areas_not_nodes():
    result = finding_summary(finding_rows(sample_report()))
    assert result == {"total": 4, "issues": 1, "reviews": 2,
                      "critical_issues": 1, "areas_affected": 3}


def test_details_keep_evidence_without_mutation():
    report = sample_report()
    before = deepcopy(report)
    rows = finding_rows(report)
    assert next(row for row in rows if row["check_id"] == "axe1")["evidence"] == {"nodes": ["a", "b"]}
    assert report == before


def test_filters_combine_area_status_priority_and_search():
    rows = finding_rows(sample_report())
    assert [r["check_id"] for r in filter_findings(rows, area="Navigation",
            result="Needs review", priority="Medium", search="javascript")] == ["nav1"]


def test_filter_result_issue_and_not_verified_are_distinct():
    rows = finding_rows(sample_report())
    assert [r["check_id"] for r in filter_findings(rows, result="Issue")] == ["axe1"]
    assert [r["check_id"] for r in filter_findings(rows, result="Not verified")] == ["unverified"]


def test_filter_search_uses_casefold():
    rows = finding_rows(sample_report())
    assert len(filter_findings(rows, search="ACCESSIBLE")) == 1


def test_filter_no_match_is_empty():
    assert filter_findings(finding_rows(sample_report()), search="absent") == []


def test_table_has_bounded_display_strings_and_no_evidence_leak():
    rows = finding_rows(sample_report())
    table = findings_table(rows)
    assert len(table) == len(rows)
    assert all("evidence" not in item for item in table)
    assert {"Priority", "Area", "Finding", "Result", "Suggested action"} == set(table[0])


def test_missing_or_malformed_findings_do_not_crash():
    assert finding_rows({"findings": None}) == []
    assert finding_rows({"findings": {"a": 1}}) == []
    assert finding_rows({"findings": ["bad", 12]}) == []


def test_unknown_status_not_upgraded_to_passed():
    row = finding_rows({"findings": [{"id": "a", "status": "unexpected", "severity": "bad"}]})[0]
    assert row["status"] == "not_verified"
    assert row["severity"] == "info"


def test_description_callback_is_supported_for_translation():
    rows = finding_rows(sample_report(), describe=lambda _: ("Readable title", "Fix later"),
                        team_label=lambda _: "Technical review")
    assert all(row["title"] == "Readable title" and row["team"] == "Technical review"
               for row in rows)


def test_duplicate_titles_retain_distinct_original_indices():
    data = {"findings": [{"id": str(i), "status": "warning", "title": "Same"}
                          for i in range(500)]}
    rows = finding_rows(data)
    assert len(rows) == 500
    assert len({r["index"] for r in rows}) == 500
    assert len(filter_findings(rows, result="All")) == 500


@pytest.mark.parametrize("value", ["Critical", "High", "Medium", "Low", "Info"])
def test_priority_filter_supported_for_every_level(value):
    rows = finding_rows(sample_report())
    result = filter_findings(rows, result="All", priority=value)
    assert all(r["severity"] == value.lower() for r in result)
