"""Offline smoke test for Stage 17 local history and the HTML evidence ZIP.

Every invocation saves a NEW local history entry. No website is fetched.
"""
from __future__ import annotations

import json
from pathlib import Path

from pagecheck.persistence.sqlite.history import AuditHistory
from pagecheck.reporting.exports import findings_csv, zip_export

ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    ROOT / "artifacts" / "page_audits" / "stage16d_fixture" / "consolidated_visual_audit.json",
    ROOT / "artifacts" / "consolidation_stage15" / "consolidated_audit.json",
)


def main() -> None:
    source = next((path for path in INPUTS if path.is_file()), None)
    if source is None:
        raise SystemExit(
            "No local reference report found. Run:\n"
            "  uv run python scripts/visual_report_fixture_smoke.py\n"
            "or\n"
            "  uv run python scripts/consolidation_fixture_smoke.py"
        )
    report = json.loads(source.read_text(encoding="utf-8"))
    store = AuditHistory(ROOT)
    saved = store.save(report)
    restored = store.load(saved["audit_id"])
    out = ROOT / "artifacts" / "history_stage17"
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit_report.zip").write_bytes(zip_export(restored, ROOT))
    (out / "findings.csv").write_bytes(findings_csv(restored))
    print(json.dumps({
        "saved_id": saved["audit_id"],
        "source_report": str(source),
        "stored_report": str(store.reports_dir / saved["audit_id"] / "report.json"),
        "zip": str(out / "audit_report.zip"),
        "csv": str(out / "findings.csv"),
        "has_screenshots": saved["has_screenshots"],
        "history_count_first_page": len(store.list()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
