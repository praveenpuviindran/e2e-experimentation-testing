import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


def get_postgres_config() -> PostgresConfig:
    load_dotenv()
    return PostgresConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "mindlift"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
    )


def get_database_url() -> str:
    load_dotenv()
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return get_postgres_config().sqlalchemy_url
