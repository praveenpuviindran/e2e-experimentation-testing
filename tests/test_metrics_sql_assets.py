from pathlib import Path


def test_required_metrics_sql_files_exist() -> None:
    required = [
        "sql/metrics/funnels.sql",
        "sql/metrics/retention.sql",
        "sql/metrics/guardrails.sql",
        "sql/metrics/experiment_readout_tables.sql",
    ]

    for rel_path in required:
        assert Path(rel_path).exists(), f"Missing metrics SQL file: {rel_path}"


def test_funnel_sql_has_activation_view() -> None:
    content = Path("sql/metrics/funnels.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW vw_activation_user_level" in content
    assert "activated_within_7d" in content
