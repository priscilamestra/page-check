import pytest
from pagecheck.integrations.engine_result import EngineOutputError
from pagecheck.integrations.lighthouse.adapter import normalize_lighthouse
from pagecheck.integrations.axe.adapter import normalize_axe
from pagecheck.integrations.impeccable.adapter import normalize_impeccable


def test_lighthouse_scores_preserve_zero():
    r = normalize_lighthouse({"categories": {"seo": {"score": 0.0},
                                               "performance": {"score": .75}}, "audits": {}})
    assert r["scores"]["seo"] == 0
    assert r["scores"]["performance"] == 75
    assert r["scores"]["accessibility"] is None


def test_lighthouse_audit_finding():
    r = normalize_lighthouse({"categories": {"seo": {"score": .8, "auditRefs": [{"id": "h1"}]}},
                              "audits": {"h1": {"title": "Heading", "score": 0}}})
    assert r["findings"][0]["id"] == "lighthouse:h1"


def test_lighthouse_does_not_invent_manual_failures():
    r = normalize_lighthouse({"categories": {"seo": {"score": .8, "auditRefs": [{"id": "manual"}]}},
                              "audits": {"manual": {"score": 0, "scoreDisplayMode": "manual"}}})
    assert r["findings"] == []


def test_lighthouse_rejects_invalid_score():
    with pytest.raises(EngineOutputError):
        normalize_lighthouse({"categories": {"seo": {"score": 5}}})


def test_lighthouse_rejects_invalid_json():
    with pytest.raises(EngineOutputError):
        normalize_lighthouse([])


def test_axe_nodes_and_severity():
    r = normalize_axe({"violations": [{"id": "image-alt", "impact": "serious",
                                       "nodes": [{"target": ["img"]}]}], "passes": []})
    assert r["findings"][0]["severity"] == "high"
    assert r["findings"][0]["evidence"]["selectors"] == [["img"]]


def test_axe_clean_result_is_not_full_compliance():
    r = normalize_axe({"violations": [], "passes": []})
    assert not r["findings"]
    assert "revisão humana" in r["limitations"][0]


def test_axe_requires_violations():
    with pytest.raises(EngineOutputError):
        normalize_axe({"passes": []})


def test_impeccable_list_and_envelope():
    assert len(normalize_impeccable([{"ruleId": "x"}])["findings"]) == 1
    assert normalize_impeccable({"findings": []})["findings"] == []


def test_impeccable_invalid_shape():
    with pytest.raises(EngineOutputError):
        normalize_impeccable({"message": "ok"})


def test_impeccable_missing_rule():
    with pytest.raises(EngineOutputError):
        normalize_impeccable([{"message": "no id"}])
