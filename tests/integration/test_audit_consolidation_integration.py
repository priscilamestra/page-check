"""Fluxo real de regras existentes para o contrato único, sem rede/CLI."""
from pagecheck.application.use_cases.audit_conversion_page import audit_conversion_html
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.audits.seo.rules import audit_seo
from pagecheck.integrations.axe.adapter import normalize_axe
from pagecheck.application.use_cases.external_engines import combine_engines


def test_seo_and_conversion_produce_single_consistent_report():
    url = "https://example.com/landing"
    html = """<html><head><meta name='robots' content='noindex'></head>
      <body><h3>Serviço</h3><img src='/missing.png'>
      <a href='#unavailable'>Agendar</a><form><input name='email'></form></body></html>"""
    # A entrada abaixo tem o mesmo contrato da saída COMPLETA do parser.
    extracted = {"page_url": url, "title": None, "meta_description": None,
                 "meta_robots": "noindex", "canonical": None,
                 "headings": [{"level": "h3", "text": "Serviço"}],
                 "links": [{"text": "Agendar", "href": "#unavailable"}],
                 "images": [{"src": url + "/missing.png", "alt": None}]}
    seo = audit_seo(extracted, objective="organic_traffic")
    conv = audit_conversion_html(html, url, objective="leads")
    engines = combine_engines({"axe": normalize_axe({"violations": [], "incomplete": [], "passes": []})})
    report = consolidate_audit(requested_url=url, final_url=url, niche="SaaS",
                               objective="organic_traffic", seo=seo,
                               conversion=conv, external=engines)
    assert report["summary"]["counts"]["failed"] >= 4
    assert report["source_states"]["seo"] == "completed"
    assert report["source_states"]["engines"]["lighthouse"] == "not_verified"
    assert report["scores"]["lighthouse"] is None
    assert report["summary"]["priority_count"] >= 4
