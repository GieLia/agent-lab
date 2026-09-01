import hashlib
from pathlib import Path

import psycopg

from app.db import get_db_uri


ROOT = Path(
    "/opt/agent-lab"
)

MIGRATION_DIR = (
    ROOT
    / "infra"
    / "postgres"
    / "migrations"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def ensure_migration_table(
    connection,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE SCHEMA IF NOT EXISTS measurement
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
            measurement.schema_migration (
                migration_name TEXT PRIMARY KEY,
                migration_sha256 CHAR(64) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CHECK (
                    migration_sha256
                    ~ '^[0-9a-f]{64}$'
                )
            )
            """
        )


def get_applied(
    connection,
    migration_name: str,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT migration_sha256
            FROM measurement.schema_migration
            WHERE migration_name = %s
            """,
            (
                migration_name,
            ),
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return row[0]


def apply_migration(
    connection,
    path: Path,
) -> str:
    content = path.read_bytes()

    digest = sha256(
        content
    )

    existing = get_applied(
        connection,
        path.name,
    )

    if existing is not None:
        if existing != digest:
            raise RuntimeError(
                "Migration checksum mismatch: "
                f"{path.name}"
            )

        print(
            "MIGRATION_ALREADY_APPLIED",
            path.name,
        )

        return "already-applied"

    sql = content.decode(
        "utf-8"
    )

    with connection.cursor() as cursor:
        cursor.execute(
            sql
        )

        cursor.execute(
            """
            INSERT INTO
                measurement.schema_migration (
                    migration_name,
                    migration_sha256
                )
            VALUES (%s, %s)
            """,
            (
                path.name,
                digest,
            ),
        )

    print(
        "MIGRATION_APPLIED",
        path.name,
    )

    return "applied"


def main() -> None:
    migrations = sorted(
        MIGRATION_DIR.glob(
            "[0-9][0-9][0-9]_*.sql"
        )
    )

    if not migrations:
        raise RuntimeError(
            "No migrations found"
        )

    connection = psycopg.connect(
        get_db_uri()
    )

    try:
        ensure_migration_table(
            connection
        )

        connection.commit()

        for migration in migrations:
            try:
                apply_migration(
                    connection,
                    migration,
                )

                connection.commit()

            except Exception:
                connection.rollback()
                raise

    finally:
        connection.close()

    print(
        "MEASUREMENT_MIGRATIONS_OK"
    )


if __name__ == "__main__":
    main()
