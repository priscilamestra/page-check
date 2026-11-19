"""Fast UX contract checks for the compact URL & parameters exploration."""
from copy import deepcopy

from pagecheck.ui.components.coverage_composition import source_composition_html
from pagecheck.ui.components.url_explorer import (
    area_summary,
    campaign_parameters,
    check_rows,
    destination_inventory_count,
    filter_rows,
    group_check_rows,
)


def sample():
    return {
        "requested_url": "https://example.com/landing?utm_source=google&utm_medium=cpc&token=private",
        "checks": [
            {"module": "tracking", "status": "passed", "check_id": "utm", "evidence": {"q": "yes"}},
            {"module": "navigation", "status": "not_verified", "check_id": "nav-1"},
            {"module": "navigation", "status": "not_verified", "check_id": "nav-2"},
            {"module": "navigation", "status": "warning", "check_id": "nav-3", "recommendation": "Check href"},
            {"module": "forms", "status": "failed", "check_id": "form-required"},
            {"module": "seo", "status": "failed", "check_id": "seo-do-not-include"},
        ],
    }


def test_utm_count_is_not_a_delivery_claim():
    info = campaign_parameters(sample())
    assert (info["utm"], info["total"], info["has_utm"]) == (2, 3, True)


def test_sensitive_query_value_is_hidden():
    params = campaign_parameters(sample())["parameters"]
    assert params[-1]["Value"] == "[hidden]"


def test_no_query_is_neutral():
    assert campaign_parameters({"requested_url": "https://example.com"}) == {
        "parameters": [], "total": 0, "utm": 0, "has_utm": False,
    }


def test_duplicate_keys_are_preserved():
    info = campaign_parameters({"requested_url": "https://x.test/?utm_source=a&utm_source=b"})
    assert info["utm"] == 2 and len(info["parameters"]) == 2


def test_invalid_requested_url_type_is_not_crash():
    assert campaign_parameters({"requested_url": [1, 2]})["total"] == 0


def test_only_relevant_modules_are_shown():
    assert len(check_rows(sample())) == 5


def test_priority_issues_before_unverified():
    rows = check_rows(sample())
    assert rows[0]["status"] == "failed"
    assert rows[1]["status"] == "warning"
    assert rows[2]["status"] == "not_verified"


def test_stable_source_indices_allow_evidence_lookup():
    rows = check_rows(sample())
    assert [row["index"] for row in rows] == [4, 3, 1, 2, 0]
    assert rows[-1]["evidence"] == {"q": "yes"}


def test_counts_by_area_include_not_verified():
    summary = area_summary(check_rows(sample()))
    assert summary[1]["Not verified"] == 2
    assert summary[1]["Needs review"] == 1
    assert summary[2]["Issues"] == 1


def test_default_filter_prevents_hundreds_of_initial_cards():
    rows = check_rows(sample())
    assert [r["status"] for r in filter_rows(rows)] == ["failed", "warning"]


def test_filter_by_status():
    assert len(filter_rows(check_rows(sample()), status="Not verified")) == 2


def test_filter_by_module():
    assert len(filter_rows(check_rows(sample()), area="Forms", status="All")) == 1


def test_text_search_is_case_insensitive():
    assert len(filter_rows(check_rows(sample()), status="All", search="NAV-2")) == 1


def test_empty_check_list_is_safe():
    assert check_rows({"checks": None}) == []


def test_report_not_modified_by_view_helpers():
    report = sample()
    original = deepcopy(report)
    filter_rows(check_rows(report), status="All")
    campaign_parameters(report)
    assert report == original


def test_repeated_unverified_links_are_grouped_without_losing_records():
    rows = check_rows(sample(), describe=lambda item: (
        "Link destination identified, not tested" if item.get("module") == "navigation"
        and item.get("status") == "not_verified" else item.get("check_id", "Check"),
        "Coverage limit" if item.get("status") == "not_verified" else "",
    ))
    grouped = group_check_rows(rows)
    navigation = next(row for row in grouped
                      if row["area"] == "navigation" and row["status"] == "not_verified")
    assert navigation["occurrences"] == 2
    assert [item["check_id"] for item in navigation["members"]] == ["nav-1", "nav-2"]


def test_element_destination_and_location_are_exposed_from_recorded_evidence():
    report = {"checks": [{
        "module": "navigation", "status": "warning", "check_id": "nav",
        "evidence": {"text": "Buy", "resolved_url": "https://example.com/buy",
                     "selector": "main > a:nth-of-type(1)"},
    }]}
    row = check_rows(report)[0]
    assert (row["element"], row["destination"], row["location"]) == (
        "Buy", "https://example.com/buy", "main > a:nth-of-type(1)")


def test_aggregated_link_inventory_keeps_count_and_example():
    report = {"checks": [{
        "module": "navigation", "status": "not_verified",
        "check_id": "NAV_DESTINATION_COVERAGE",
        "evidence": {"count": 204, "items": [
            {"text": "Docs", "resolved_url": "https://example.com/docs",
             "selector": "nav > a:nth-of-type(1)"},
        ]},
    }]}
    rows = check_rows(report)
    assert destination_inventory_count(rows) == 204
    assert rows[0]["destination"] == "https://example.com/docs"
    assert rows[0]["inventory_items"] == 204


def test_one_composition_bar_has_actual_total_and_all_statuses():
    text = source_composition_html({"completed": 3, "partial": 2, "not_verified": 2})
    assert text.count('height:29px') == 1
    assert "Completed: 3 of 7" in text
    assert "Limited: 2 of 7" in text
    assert "Not verified: 2 of 7" in text


def test_bogus_counts_do_not_create_fake_graph():
    assert source_composition_html({"completed": True, "partial": -2,
                                    "not_verified": "5"}) == ""
