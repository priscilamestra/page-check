"""Demonstra auditoria passiva a partir de arquivo de teste local."""
from __future__ import annotations

import json
from pathlib import Path

from pagecheck.application.use_cases.audit_conversion_page import audit_conversion_html

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "tests/fixtures/pages/conversion_tracking.html").read_text(encoding="utf-8")
report = audit_conversion_html(
    html,
    "https://example.com/landing?utm_source=linkedin&utm_medium=social&utm_campaign=demo",
    niche="SaaS B2B", objective="leads",
)
out_dir = ROOT / "artifacts" / "browser_stage13"
out_dir.mkdir(parents=True, exist_ok=True)
file = out_dir / "conversion_audit.json"
file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"counts": report["counts"], "report": str(file)}, ensure_ascii=False, indent=2))
