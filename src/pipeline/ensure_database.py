from __future__ import annotations

import re

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.utils.config import get_admin_database_url, get_postgres_config
from src.utils.logging import get_logger


logger = get_logger(__name__)
_VALID_DB_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ensure_target_database_exists() -> None:
    cfg = get_postgres_config()
    target_db = cfg.database

    if not _VALID_DB_NAME.match(target_db):
        raise SystemExit(
            "Invalid PGDATABASE. Use only letters, numbers, and underscores "
            f"(got: {target_db!r})."
        )

    admin_engine = create_engine(get_admin_database_url())
    try:
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": target_db},
            ).scalar_one_or_none()

            if exists:
                return

            logger.info("Target database '%s' not found; creating it", target_db)
            conn.exec_driver_sql(f"CREATE DATABASE {target_db}")
    except SQLAlchemyError as exc:
        message = str(exc)
        logger.exception("Unable to ensure target database exists")

        if "role" in message and "does not exist" in message:
            raise SystemExit(
                "PostgreSQL role does not exist for current PGUSER. "
                "Fix .env: set PGUSER to your local postgres username (usually your mac username), "
                "and set PGPASSWORD if required."
            ) from exc

        if "password authentication failed" in message:
            raise SystemExit(
                "PostgreSQL authentication failed. Update PGUSER/PGPASSWORD in .env and retry."
            ) from exc

        raise SystemExit(
            "Could not connect to admin database to create/check PGDATABASE. "
            "Set PGADMIN_DATABASE (usually 'postgres') or DATABASE_ADMIN_URL in .env."
        ) from exc
