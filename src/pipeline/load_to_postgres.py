from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import create_engine

from src.pipeline.apply_schema import main as apply_schema_main
from src.utils.config import get_database_url
from src.utils.logging import get_logger


logger = get_logger(__name__)
RAW_DIR = Path("data/raw")


TABLE_SPECS = [
    ("dim_users", ["user_id"]),
    ("fact_sessions", ["session_id"]),
    ("fact_events", ["event_id"]),
    ("fact_subscriptions", ["user_id"]),
    ("fact_cancellations", ["user_id"]),
    ("fact_support_tickets", ["ticket_id"]),
    ("fact_matches", ["user_id"]),
]


def _read_csv_columns(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def _copy_and_upsert(raw_conn, csv_path: Path, table_name: str, pk_columns: list[str]) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing input file: {csv_path}")

    columns = _read_csv_columns(csv_path)
    staging_name = f"staging_{table_name}"

    columns_sql = ", ".join(columns)
    pk_sql = ", ".join(pk_columns)
    non_pk_columns = [c for c in columns if c not in pk_columns]

    if non_pk_columns:
        update_sql = ", ".join(f"{col} = EXCLUDED.{col}" for col in non_pk_columns)
        conflict_clause = f"DO UPDATE SET {update_sql}"
    else:
        conflict_clause = "DO NOTHING"

    with raw_conn.cursor() as cursor:
        cursor.execute(f"CREATE TEMP TABLE {staging_name} (LIKE {table_name}) ON COMMIT DROP;")
        with csv_path.open("r", encoding="utf-8") as f:
            cursor.copy_expert(
                f"COPY {staging_name} ({columns_sql}) FROM STDIN WITH CSV HEADER",
                f,
            )

        cursor.execute(
            f"""
            INSERT INTO {table_name} ({columns_sql})
            SELECT {columns_sql}
            FROM {staging_name}
            ON CONFLICT ({pk_sql}) {conflict_clause};
            """
        )


def main() -> None:
    logger.info("Applying schema before load")
    apply_schema_main()

    engine = create_engine(get_database_url())
    raw_conn = engine.raw_connection()

    try:
        for table_name, pk_columns in TABLE_SPECS:
            csv_path = RAW_DIR / f"{table_name}.csv"
            logger.info("Loading %s", csv_path)
            _copy_and_upsert(raw_conn, csv_path, table_name, pk_columns)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        logger.exception("Data load failed")
        raise SystemExit(1)
    finally:
        raw_conn.close()

    logger.info("Data load completed successfully")


if __name__ == "__main__":
    main()
