from pathlib import Path
from urllib.parse import urlparse

import psycopg

from app.config import settings


def _sync_dsn() -> str:
    dsn = settings.database_url
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if dsn.startswith("postgresql+psycopg://"):
        return dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn


def _ensure_migration_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(64) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    conn.commit()


def _is_applied(conn: psycopg.Connection, version: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,))
        return cur.fetchone() is not None


def _mark_applied(conn: psycopg.Connection, version: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO schema_migrations(version) VALUES (%s) ON CONFLICT (version) DO NOTHING",
            (version,),
        )
    conn.commit()


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
        row = cur.fetchone()
        return bool(row and row[0])


def run_migrations() -> None:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    dsn = _sync_dsn()

    with psycopg.connect(dsn, autocommit=False) as conn:
        _ensure_migration_table(conn)
        conversations_exists = _table_exists(conn, "conversations")

        for file_path in files:
            version = file_path.name
            if _is_applied(conn, version):
                continue

            if version.startswith("001_") and conversations_exists:
                _mark_applied(conn, version)
                continue

            sql_text = file_path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql_text)
            conn.commit()
            _mark_applied(conn, version)


if __name__ == "__main__":
    run_migrations()
