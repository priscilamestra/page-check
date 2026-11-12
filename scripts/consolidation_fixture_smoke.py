"""Exemplo de consolidação offline. Não representa auditoria de site real.

Usa o contrato completo do parser, testes de HTML existentes e JSONs de
referência dos motores. Os dados são FIctícios e há etapas não verificadas.
"""
from __future__ import annotations

import json
from pathlib import Path

from pagecheck.application.use_cases.audit_conversion_page import audit_conversion_html
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.application.use_cases.external_engines import combine_engines
from pagecheck.audits.seo.rules import audit_seo
from pagecheck.integrations.axe.adapter import normalize_axe
from pagecheck.integrations.impeccable.adapter import normalize_impeccable
from pagecheck.integrations.lighthouse.adapter import normalize_lighthouse

ROOT = Path(__file__).resolve().parents[1]
URL = "https://example.com/landing-exemplo"


def main() -> None:
    html = (ROOT / "tests/fixtures/pages/seo_problems.html").read_text("utf-8")
    # Snapshot completo equivalente ao contrato de parse_html(), construído
    # para esta fixture; o parser real já foi validado em etapas anteriores.
    extracted = {
        "page_url": URL, "title": None, "meta_description": None,
        "meta_robots": "noindex, follow", "canonical": None,
        "headings": [{"level": "h3", "text": "Detalhes do serviço"}],
        "links": [{"text": "Contato", "href": "/contato"}],
        "images": [{"src": "https://example.com/assets/banner-sem-alt.png", "alt": None}],
    }
    fixture_dir = ROOT / "tests/fixtures/engines"
    engines = combine_engines({
        "lighthouse": normalize_lighthouse(json.loads((fixture_dir / "lighthouse.json").read_text("utf-8"))),
        "axe": normalize_axe(json.loads((fixture_dir / "axe.json").read_text("utf-8"))),
        "impeccable": normalize_impeccable(json.loads((fixture_dir / "impeccable.json").read_text("utf-8"))),
    })
    result = consolidate_audit(
        requested_url=URL, final_url=URL, niche="Tecnologia / SaaS",
        objective="organic_traffic", seo=audit_seo(extracted, objective="organic_traffic"),
        conversion=audit_conversion_html(html, URL, objective="organic_traffic"),
        external=engines,
        audit_id="offline-demo-stage15",
    )
    destination = ROOT / "artifacts" / "consolidation_stage15" / "consolidated_audit.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "file": str(destination), "status": result["status"],
        "findings": len(result["findings"]),
        "counts": result["summary"]["counts"],
        "unverified_sources": result["source_states"]["visuals"],
        "demo": True,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
