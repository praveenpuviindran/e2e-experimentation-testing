from __future__ import annotations

import getpass
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy.engine import URL


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    admin_database: str

    def sqlalchemy_url(self, database_override: str | None = None) -> str:
        db_name = database_override or self.database
        url = URL.create(
            drivername="postgresql+psycopg2",
            username=self.user,
            password=self.password if self.password else None,
            host=self.host,
            port=self.port,
            database=db_name,
        )
        return str(url)


def get_postgres_config() -> PostgresConfig:
    load_dotenv()

    default_user = os.getenv("USER") or getpass.getuser()
    return PostgresConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "mindlift"),
        user=os.getenv("PGUSER", default_user),
        password=os.getenv("PGPASSWORD", ""),
        admin_database=os.getenv("PGADMIN_DATABASE", "postgres"),
    )


def get_database_url() -> str:
    load_dotenv()
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return get_postgres_config().sqlalchemy_url()


def get_admin_database_url() -> str:
    load_dotenv()
    explicit = os.getenv("DATABASE_ADMIN_URL")
    if explicit:
        return explicit
    config = get_postgres_config()
    return config.sqlalchemy_url(database_override=config.admin_database)
