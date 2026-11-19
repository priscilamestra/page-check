"""Regras de SEO avaliadas exclusivamente com HTML de demonstração."""

import pytest

from pagecheck.acquisition.http.parser import parse_html
from pagecheck.audits.seo.rules import audit_seo

URL = "https://example.com/landing"


def parse(content: str) -> dict:
    return parse_html(content, URL)


def by_id(result: dict, check_id: str) -> dict:
    return next(c for c in result["checks"] if c["check_id"] == check_id)


def test_complete_page_scores_full_for_organic_traffic():
    data = parse("""<html><head><title>Serviço de tecnologia</title>
       <meta name='description' content='Conheça o serviço'>
       <link rel='canonical' href='/landing'></head>
       <body><h1>Soluções para empresas</h1><h2>Benefícios</h2>
       <img src='/logo.svg' alt='Logo'></body></html>""")
    result = audit_seo(data, objective="organic_traffic")
    assert result["score"] == 100.0
    assert result["coverage"] == 1.0
    assert result["findings"] == []


def test_missing_title_and_description_have_failing_evidence():
    result = audit_seo(parse("<h1>Olá</h1>"))
    assert by_id(result, "SEO_TITLE")["status"] == "failed"
    assert by_id(result, "SEO_DESCRIPTION")["status"] == "failed"
    assert by_id(result, "SEO_TITLE")["evidence"]["observed_value"] is None
    assert result["score"] < 100
    breakdown = result["score_breakdown"]
    assert breakdown["points_earned"] < breakdown["points_possible"]
    assert {row["check_id"] for row in breakdown["deductions"]} >= {
        "SEO_TITLE", "SEO_DESCRIPTION",
    }


def test_score_breakdown_matches_the_published_score():
    result = audit_seo(parse("<title>Example</title><h1>One</h1><h1>Two</h1>"))
    breakdown = result["score_breakdown"]
    assert result["score"] == round(
        100 * breakdown["points_earned"] / breakdown["points_possible"], 1
    )
    assert any(row["check_id"] == "SEO_H1" and row["points_lost"] == 1.5
               for row in breakdown["deductions"])


def test_missing_h1_is_failure():
    result = audit_seo(parse("<h2>Sem h1</h2>"))
    assert by_id(result, "SEO_H1")["status"] == "failed"


def test_multiple_h1_is_warning_not_hard_failure():
    result = audit_seo(parse("<h1>Um</h1><h1>Dois</h1>"))
    assert by_id(result, "SEO_H1")["status"] == "warning"


def test_heading_level_jump_warns():
    result = audit_seo(parse("<h1>Um</h1><h3>Três</h3>"))
    assert by_id(result, "SEO_HEADING_ORDER")["status"] == "warning"


def test_canonical_is_a_warning_when_missing():
    result = audit_seo(parse("<h1>Um</h1>"))
    assert by_id(result, "SEO_CANONICAL")["status"] == "warning"


def test_noindex_blocks_organic_intent_not_paid_leads():
    data = parse("<meta name='robots' content='NOINDEX, follow'><h1>Um</h1>")
    organic = audit_seo(data, objective="organic_traffic")
    paid = audit_seo(data, objective="leads")
    assert by_id(organic, "SEO_NOINDEX")["status"] == "failed"
    assert by_id(paid, "SEO_NOINDEX")["status"] == "not_applicable"
    assert organic["checks_applicable"] == paid["checks_applicable"] + 1


def test_missing_image_alt_warnings_but_empty_decorative_alt_accepted():
    data = parse("<h1>Um</h1><img src='/a.png'><img src='/b.png' alt=''>")
    result = audit_seo(data)
    assert by_id(result, "SEO_IMAGE_ALT")["status"] == "warning"
    assert by_id(result, "SEO_IMAGE_ALT")["evidence"]["observed_value"]["missing_alt_sources"] == ["https://example.com/a.png"]


def test_without_images_rule_is_not_applicable():
    result = audit_seo(parse("<h1>Um</h1>"))
    assert by_id(result, "SEO_IMAGE_ALT")["status"] == "not_applicable"


def test_incomplete_parser_data_is_not_verified_not_passed():
    result = audit_seo({"page_url": URL, "title": "Algo"}, objective="organic_traffic")
    assert by_id(result, "SEO_H1")["status"] == "not_verified"
    assert result["coverage"] < 0.70
    assert result["partial_score"] is True


def test_reject_unsupported_objective():
    with pytest.raises(ValueError):
        audit_seo(parse("<h1>Um</h1>"), objective="ranking_google")
