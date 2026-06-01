from pathlib import Path


def test_required_metrics_sql_files_exist() -> None:
    """All four required metrics SQL files must exist in sql/metrics/.

    These files define the analytics layer (funnels, retention, guardrails, readout tables)
    used by both the Python analysis pipeline and the Streamlit dashboard.
    """
    required = [
        "sql/metrics/funnels.sql",
        "sql/metrics/retention.sql",
        "sql/metrics/guardrails.sql",
        "sql/metrics/experiment_readout_tables.sql",
    ]

    for rel_path in required:
        assert Path(rel_path).exists(), f"Missing metrics SQL file: {rel_path}"


def test_funnel_sql_has_activation_view() -> None:
    """funnels.sql must define the vw_activation_user_level view with the activated_within_7d column.

    The Streamlit dashboard and analysis pipeline depend on this view as the primary
    source of activation flags per user.
    """
    content = Path("sql/metrics/funnels.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW vw_activation_user_level" in content
    assert "activated_within_7d" in content
