"""Delete expired rows + screenshots. Schedule this securely in production."""
from pathlib import Path

from pagecheck.persistence.postgres import TemporaryAuditStore


def main() -> None:
    store = TemporaryAuditStore(Path(__file__).resolve().parents[1])
    deleted = store.purge_expired()
    print(f"Expired temporary audit records deleted: {deleted}")


if __name__ == "__main__":
    main()
