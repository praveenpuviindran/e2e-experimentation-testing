from pathlib import Path


def test_schema_sql_exists() -> None:
    schema_path = Path("sql/schema/schema.sql")
    assert schema_path.exists(), "sql/schema/schema.sql must exist"
    content = schema_path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS dim_users" in content
    assert "CREATE TABLE IF NOT EXISTS fact_events" in content
