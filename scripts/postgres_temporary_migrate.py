"""Initialize the private PostgreSQL temporary-report schema (explicit local action)."""
from pathlib import Path

from pagecheck.persistence.postgres.temporary import _connect_from_env


def main() -> None:
    migration = Path(__file__).resolve().parents[1] / "migrations" / "0001_temporary_postgres.sql"
    sql = migration.read_text(encoding="utf-8")
    with _connect_from_env() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("PostgreSQL temporary audit schema is ready. No credentials were printed.")


if __name__ == "__main__":
    main()
