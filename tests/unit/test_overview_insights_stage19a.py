"""Stage 19A: the new charts must be clear and never inflate page defects."""
from __future__ import annotations

from copy import deepcopy

import pytest

from pagecheck.ui.components.overview_insights import (
    actionable_rows,
    area_bars_html,
    count_label,
    coverage_bars_html,
    missing_evidence_rows,
    prioritized_findings,
    seo_keyword_groups,
    source_counts,
)


def hubspot_like_report():
    return {
        "status": "partial",
        "summary": {
            "counts": {"failed": 1, "warning": 3, "passed": 9, "not_verified": 246},
            "by_module": {
                "accessibility": {"failed": 1, "warning": 0, "passed": 0},
                "navigation": {"failed": 0, "warning": 1, "passed": 1, "not_verified": 242},
                "seo": {"failed": 0, "warning": 2, "passed": 7, "not_verified": 1},
                "forms": {"failed": 0, "warning": 0, "passed": 2, "not_verified": 2},
                "tracking": {"failed": 0, "warning": 0, "not_verified": 1},
            },
        },
        "findings": [
            {"id": "keyword2", "module": "seo", "status": "warning", "severity": "low"},
            {"id": "accessibility", "module": "accessibility", "status": "failed", "severity": "critical"},
            {"id": "nav", "module": "navigation", "status": "warning", "severity": "medium"},
            {"id": "keyword1", "module": "seo", "status": "warning", "severity": "low"},
        ],
        "source_states": {"seo": "completed", "conversion": "completed", "visuals": {
            "desktop": "partial", "mobile": "partial"}, "engines": {
            "axe": "completed", "impeccable": "not_verified"}},
    }


def test_actionable_chart_counts_only_issues_and_reviews():
    rows = actionable_rows(hubspot_like_report())
    assert [(row["area"], row["issues"], row["reviews"]) for row in rows] == [
        ("seo", 0, 2), ("accessibility", 1, 0), ("navigation", 0, 1)]
    assert sum(row["total"] for row in rows) == 4


def test_actionable_chart_does_not_include_passed_or_unverified():
    rows = actionable_rows(hubspot_like_report())
    assert all(row["area"] not in {"forms", "tracking"} for row in rows)
    assert max(row["total"] for row in rows) == 2


def test_unverified_chart_is_distinct_from_findings():
    rows = missing_evidence_rows(hubspot_like_report())
    assert rows == [
        {"area": "navigation", "total": 242}, {"area": "forms", "total": 2},
        {"area": "seo", "total": 1}, {"area": "tracking", "total": 1},
    ]
    assert sum(row["total"] for row in rows) == 246


def test_coverage_sources_are_not_individual_checks():
    assert source_counts(hubspot_like_report()) == {
        "completed": 3, "partial": 2, "not_verified": 1}


def test_priorities_are_sorted_even_for_older_unsorted_reports():
    items = prioritized_findings(hubspot_like_report(), limit=3)
    assert [item["id"] for item in items] == ["accessibility", "nav", "keyword1"]


def test_priorities_do_not_modify_audited_data():
    report = hubspot_like_report()
    copy = deepcopy(report)
    prioritized_findings(report)
    assert report == copy


def test_priorities_do_not_promote_unverified_to_actionable():
    report = hubspot_like_report()
    report["findings"].insert(0, {"id": "unknown", "status": "not_verified",
                                  "severity": "critical", "module": "navigation"})
    assert "unknown" not in [item["id"] for item in prioritized_findings(report, limit=10)]


def test_priorities_respect_zero_limit():
    assert prioritized_findings(hubspot_like_report(), limit=0) == []


def test_legacy_report_falls_back_to_findings():
    report = hubspot_like_report()
    report["summary"]["by_module"] = {}
    rows = actionable_rows(report)
    assert sum(row["total"] for row in rows) == 4
    assert rows[0]["area"] == "seo"


def test_bad_summary_values_do_not_turn_into_counts():
    report = hubspot_like_report()
    report["summary"]["by_module"] = {
        "foo": {"failed": True, "warning": -2},
        "bar": {"failed": "19", "warning": None},
        "baz": {"failed": 1, "warning": 0},
    }
    assert actionable_rows(report) == [{"area": "baz", "issues": 1, "reviews": 0, "total": 1}]


def test_zero_actionable_data_gives_no_fake_bars():
    assert actionable_rows({"summary": {"by_module": {}}, "findings": []}) == []
    assert area_bars_html([]) == ""


def test_actionable_chart_has_visible_numbers_without_hover():
    html = area_bars_html(actionable_rows(hubspot_like_report()))
    assert "2 reviews" in html
    assert "1 issue" in html
    assert "Seo" in html
    assert "role=\"img\"" in html
    assert "title=\"" not in html


def test_unverified_chart_is_single_measure_neutral():
    html = area_bars_html(missing_evidence_rows(hubspot_like_report()), missing=True)
    assert "242 unverified checks" in html
    assert "#718096" in html
    assert "#D45B68" not in html
    assert "Issues" not in html


def test_untrusted_area_labels_are_escaped():
    html = area_bars_html([{"area": '<img src=x onerror="alert(1)">',
                                "issues": 1, "reviews": 0, "total": 1}])
    assert "<img" not in html
    assert "&lt;Img" in html


def test_single_bar_uses_full_width_not_stacked_values():
    html = area_bars_html([{"area": "a", "issues": 1, "reviews": 2, "total": 3},
                           {"area": "b", "issues": 1, "reviews": 0, "total": 1}])
    assert "width:100.0%" in html
    assert "width:33.3333%" in html
    assert html.count("background:#D45B68") == 2


@pytest.mark.parametrize("value,singular,expected", [
    (1, "issue", "1 issue"), (2, "issue", "2 issues"),
    (1, "review", "1 review"), (3, "review", "3 reviews"),
])
def test_count_labels(value, singular, expected):
    assert count_label(value, singular) == expected


def test_old_source_states_stay_not_verified():
    report = {"source_states": {"seo": "completed", "conversion": "not_verified",
                                "visuals": {}, "engines": {}}}
    assert source_counts(report) == {"completed": 1, "partial": 0, "not_verified": 5}


def test_coverage_chart_has_three_separate_labeled_bars():
    html = coverage_bars_html(source_counts(hubspot_like_report()))
    assert "3 / 6 sources" in html
    assert "2 / 6 sources" in html
    assert html.count("<div style=\"height:11px;") == 3
    assert "Completed" in html and "Limited" in html and "Not verified" in html


def test_coverage_chart_widths_are_relative_to_total_not_to_max():
    html = coverage_bars_html({"completed": 3, "partial": 2, "not_verified": 2})
    assert "width:42.8571%" in html
    assert html.count("width:28.5714%") == 2


def test_empty_coverage_does_not_invent_full_completion():
    assert coverage_bars_html({}) == ""


def test_keyword_groups_use_only_recorded_seo_evidence():
    report = {"checks": [
        {"check_id": "SEO_TARGET_KEYWORD_1", "status": "warning",
         "evidence": {"keyword": "automation", "locations": {"visible_copy": True}}},
        {"check_id": "SEO_TARGET_KEYWORD_2", "status": "warning",
         "evidence": {"keyword": "sales ops", "locations": {"visible_copy": False}}},
        {"check_id": "SEO_TARGET_KEYWORD_3", "status": "passed",
         "evidence": {"keyword": "crm", "locations": {"title": True}}},
    ]}
    groups = seo_keyword_groups(report)
    assert groups["missing_or_improve"] == [
        {"term": "automation"},
        {"term": "sales ops"},
    ]
    assert groups["review_relevance"] == []


def test_keyword_groups_do_not_invent_relevance_without_evidence():
    assert seo_keyword_groups({"checks": []}) == {
        "missing_or_improve": [], "review_relevance": []}
