"""Optional Neon/PostgreSQL round-trip; creates and deletes one synthetic report."""
from pathlib import Path

from pagecheck.persistence.postgres import TemporaryAuditStore


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    store = TemporaryAuditStore(root)
    report = {
        "schema_version": "audit-report-1.0", "requested_url": "https://example.com/",
        "final_url": "https://example.com/", "niche": "Documentation",
        "objective": "leads", "status": "partial", "source_states": {},
        "scores": {}, "summary": {}, "checks": [], "findings": [],
        "actions_by_team": [], "screenshots": {},
    }
    saved = store.save(report)
    token = saved["recovery_token"]
    try:
        loaded = store.load(token)
        assert loaded["requested_url"] == report["requested_url"]
        print("PostgreSQL: synthetic audit save/load succeeded. No recovery token printed.")
    finally:
        assert store.delete(token) is True
        print("PostgreSQL: synthetic audit deleted successfully.")


if __name__ == "__main__":
    main()
