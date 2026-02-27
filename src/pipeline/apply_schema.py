from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from src.utils.config import get_database_url
from src.utils.logging import get_logger


logger = get_logger(__name__)
SCHEMA_SQL_PATH = Path("sql/schema/schema.sql")


def main() -> None:
    if not SCHEMA_SQL_PATH.exists():
        raise SystemExit(f"Schema file missing: {SCHEMA_SQL_PATH}")

    sql_text = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    engine = create_engine(get_database_url())

    logger.info("Applying schema from %s", SCHEMA_SQL_PATH)
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(sql_text)
    except SQLAlchemyError as exc:
        logger.exception("Failed to apply schema: %s", exc)
        raise SystemExit(1) from exc

    logger.info("Schema applied successfully")


if __name__ == "__main__":
    main()
