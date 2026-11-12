import json

import pytest

from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.reporting.consolidation.normalize import normalize_check
from pagecheck.reporting.consolidation.summary import (
    group_actions,
    priority_findings,
    summarize_checks,
)

URL = "https://example.com/landing"


def _seo(*, status="failed", score=75.0):
    return {
        "checks": [
            {"check_id": "SEO_TITLE", "module": "seo", "status": status,
             "severity": "medium", "title": "Title presente", "weight": 3,
             "team": "SEO / Conteúdo", "recommendation": "Adicionar title",
             "evidence": {"source": "beautifulsoup", "observed_value": None}},
            {"check_id": "SEO_CANONICAL", "module": "seo", "status": "passed",
             "severity": "info", "title": "Canonical", "evidence": {"observed_value": URL}},
        ],
        "score": score, "coverage": 1.0, "partial_score": False,
        "ruleset_version": "seo-1.0.0",
    }


def _conversion():
    return {"checks": [
        {"check_id": "NAV_LINK_1", "module": "navigation", "status": "not_verified",
         "severity": "info", "title": "Destino não consultado"},
        {"check_id": "TRACK_UTM", "module": "tracking", "status": "not_applicable",
         "title": "Sem campanha"},
    ]}


def _external():
    return {"engines": {
        "lighthouse": {"engine": "lighthouse", "status": "completed",
                       "scores": {"seo": 91, "performance": 99}, "findings": [
                           {"id": "lh:t", "source": "lighthouse", "module": "technical",
                            "status": "warning", "severity": "high", "title": "Lighthouse warning",
                            "evidence": {"audit_id": "t"}, "owner": "Frontend"},
                       ], "limitations": []},
        "axe": {"engine": "axe", "status": "completed", "findings": [], "limitations": []},
        "impeccable": {"engine": "impeccable", "status": "completed", "findings": [],
                       "limitations": ["Requer revisão humana"]},
    }}


def _base(**kwargs):
    return consolidate_audit(requested_url=URL, final_url=URL,
                             niche="Tecnologia", objective="leads", **kwargs)


def test_no_sources_is_partial_and_unverified():
    report = _base()
    assert report["status"] == "partial"
    assert report["scores"] == {"overall": None, "internal": {"seo": None},
                                 "lighthouse": None}
    assert report["source_states"]["engines"]["axe"] == "not_verified"
    assert report["source_states"]["visuals"]["mobile"] == "not_verified"
    assert report["summary"]["check_coverage"]["ratio"] is None


def test_score_sources_are_separate():
    report = _base(seo=_seo(), external=_external())
    assert report["scores"]["internal"]["seo"]["score"] == 75.0
    assert report["scores"]["lighthouse"]["seo"] == 91
    assert report["scores"]["overall"] is None
    assert report["scores"]["internal"]["seo"]["ruleset_version"] == "seo-1.0.0"


def test_conversion_not_verified_not_counted_as_passed():
    report = _base(conversion=_conversion())
    assert report["summary"]["counts"]["not_verified"] == 1
    assert report["summary"]["counts"]["not_applicable"] == 1
    assert report["summary"]["check_coverage"]["ratio"] == 0.0
    assert report["status"] == "partial"


def test_findings_are_prioritized_and_grouped():
    report = _base(seo=_seo(), external=_external())
    assert [f["severity"] for f in report["findings"]] == ["high", "medium"]
    teams = {g["team"] for g in report["actions_by_team"]}
    assert "SEO / Conteúdo" in teams and "Frontend" in teams
    assert report["summary"]["priority_count"] == 2


def test_visual_coordinates_and_viewport_preserved():
    visual = {"viewport": {"width": 390, "height": 800}, "findings": [
        {"id": "layout-overflow", "category": "layout", "status": "failed",
         "severity": "medium", "title": "Overflow horizontal", "owner": "Frontend",
         "box": {"x": 0, "y": 550, "width": 100, "height": 40}},
    ], "screenshots": {"annotated": "artifacts/mobile.png"}}
    report = _base(visuals={"mobile": visual})
    finding = report["findings"][0]
    assert finding["viewport"] == "mobile"
    assert finding["evidence"]["box"]["y"] == 550
    assert report["screenshots"]["mobile"]["annotated"] == "artifacts/mobile.png"
    assert report["source_states"]["visuals"]["desktop"] == "not_verified"


def test_visual_without_explicit_status_is_warning_not_passed():
    item = normalize_check({"id": "img-broken", "category": "images",
                             "title": "Imagem quebrada", "box": {"x": 5}},
                           source="playwright", page_url=URL,
                           default_module="visual", viewport="desktop")
    assert item["status"] == "warning"
    assert item["severity"] == "medium"


def test_invalid_status_is_not_verified_and_evidenced():
    item = normalize_check({"check_id": "X", "status": "success"},
                           source="html_rules", page_url=URL, default_module="navigation")
    assert item["status"] == "not_verified"
    assert item["evidence"]["invalid_original_status"] == "success"


def test_duplicate_ids_are_unique_without_losing_checks():
    report = _base(conversion={"checks": [
        {"check_id": "DUP", "status": "failed", "module": "forms"},
        {"check_id": "DUP", "status": "failed", "module": "forms"},
    ]})
    assert len(report["checks"]) == 2
    assert report["checks"][1]["id"].endswith("#2")


def test_missing_completed_engine_is_not_verified():
    external = _external()
    external["engines"]["axe"] = {"engine": "axe", "status": "not_verified",
                                   "limitations": ["Axe não executou"], "findings": []}
    report = _base(external=external)
    assert report["source_states"]["engines"]["axe"] == "not_verified"
    assert report["engine_limitations"]["axe"] == ["Axe não executou"]


def test_strict_input_contract_rejects_malformed_source():
    with pytest.raises(TypeError):
        _base(visuals=[{"findings": []}])
    with pytest.raises(ValueError, match="seo.checks"):
        _base(seo={"checks": "not a list"})
    with pytest.raises(ValueError, match="external.engines"):
        _base(external={"engines": []})
    with pytest.raises(ValueError, match="Viewports"):
        _base(visuals={"tablet": {"findings": []}})


def test_zero_checks_is_not_a_passing_audit():
    report = _base(seo={"checks": [], "score": None, "coverage": 0.0})
    assert report["scores"]["internal"]["seo"]["score"] is None
    assert report["summary"]["counts"]["passed"] == 0
    assert report["status"] == "partial"


def test_json_serializable_report():
    report = _base(seo=_seo(), conversion=_conversion(), external=_external(), audit_id="demo-001")
    serial = json.loads(json.dumps(report, ensure_ascii=False))
    assert serial["audit_id"] == "demo-001"
    assert serial["summary"]["by_module"]["seo"]["passed"] == 1


def test_summary_counts_and_coverage_ignore_not_applicable():
    checks = [{"status": s, "id": str(i)} for i, s in enumerate(
        ["passed", "failed", "warning", "not_verified", "not_applicable"])]
    summary = summarize_checks(checks)
    assert summary["check_coverage"]["ratio"] == 0.75
    assert summary["check_coverage"]["applicable"] == 4


def test_priority_excludes_unverified_and_passed():
    checks = [{"status": "passed", "severity": "high", "id": "p"},
              {"status": "not_verified", "severity": "critical", "id": "u"},
              {"status": "failed", "severity": "medium", "id": "f"}]
    assert [x["id"] for x in priority_findings(checks)] == ["f"]


def test_group_actions_empty():
    assert group_actions([]) == []


def test_fully_completed_sources_without_unknown_checks():
    report = _base(
        seo=_seo(status="passed"), conversion={"checks": []},
        visuals={"desktop": {"findings": []}, "mobile": {"findings": []}},
        external=_external(),
    )
    assert report["status"] == "completed"
    assert report["summary"]["counts"]["warning"] == 1  # Lighthouse finding
    # Completed significa dados recebidos, não resultado sem defeitos.


def test_missing_engine_scores_not_zero():
    report = _base(external={"engines": {"lighthouse": {
        "engine": "lighthouse", "status": "not_verified", "scores": {"seo": 0},
        "limitations": ["timeout"]}}})
    assert report["scores"]["lighthouse"] is None


def test_source_findings_cannot_be_a_string():
    with pytest.raises(ValueError, match="findings"):
        _base(visuals={"mobile": {"findings": "oops"}})


def test_incomplete_scroll_is_partial_not_success():
    report = _base(visuals={"desktop": {"findings": [], "scroll_complete": False,
                                       "images": {"not_verified": 2},
                                       "geometry": {"truncated": True}}})
    assert report["source_states"]["visuals"]["desktop"] == "partial"
    assert len(report["visual_limitations"]["desktop"]) == 3


def test_confirmed_broken_image_is_failure():
    record = normalize_check(
        {"id": "image-broken-2", "category": "images", "severity": "high",
         "title": "Imagem não carregou"},
        source="playwright", page_url=URL, default_module="visual", viewport="mobile",
    )
    assert record["status"] == "failed"
    assert record["severity"] == "high"
