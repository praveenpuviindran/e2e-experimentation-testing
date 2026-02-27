from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.utils.config import get_database_url
from src.utils.logging import get_logger


logger = get_logger(__name__)


def main() -> None:
    db_url = get_database_url()
    logger.info("Testing PostgreSQL connection")
    logger.info("Database URL host info loaded from environment")

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version() AS version, current_database() AS db_name"))
            row = result.mappings().one()
        logger.info("Connection successful")
        logger.info("Connected database: %s", row["db_name"])
        logger.info("PostgreSQL version: %s", row["version"])
    except SQLAlchemyError as exc:
        logger.exception("Connection test failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
