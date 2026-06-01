from pathlib import Path


def test_schema_sql_exists() -> None:
    """The warehouse DDL file must exist and define the two core tables.

    dim_users and fact_events are required by every downstream pipeline step.
    This test acts as a guard against accidental deletion or rename of the schema file.
    """
    schema_path = Path("sql/schema/schema.sql")
    assert schema_path.exists(), "sql/schema/schema.sql must exist"
    content = schema_path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS dim_users" in content
    assert "CREATE TABLE IF NOT EXISTS fact_events" in content
