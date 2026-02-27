from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from src.pipeline.apply_schema import main as apply_schema_main
from src.utils.config import get_database_url
from src.utils.logging import get_logger


logger = get_logger(__name__)

METRICS_SQL_FILES = [
    Path("sql/metrics/funnels.sql"),
    Path("sql/metrics/retention.sql"),
    Path("sql/metrics/guardrails.sql"),
    Path("sql/metrics/experiment_readout_tables.sql"),
]


def _execute_sql_file(engine, sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"Missing metrics SQL file: {sql_path}")

    sql_text = sql_path.read_text(encoding="utf-8")
    logger.info("Applying metrics SQL: %s", sql_path)
    with engine.begin() as conn:
        conn.exec_driver_sql(sql_text)


def main() -> None:
    logger.info("Ensuring base schema exists")
    apply_schema_main()

    engine = create_engine(get_database_url())
    try:
        for sql_path in METRICS_SQL_FILES:
            _execute_sql_file(engine, sql_path)
    except (SQLAlchemyError, FileNotFoundError) as exc:
        logger.exception("Failed to build metrics layer: %s", exc)
        raise SystemExit(1) from exc

    logger.info("Metrics layer built successfully")


if __name__ == "__main__":
    main()
