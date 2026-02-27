import pandas as pd

from src.analysis.build_report import _decision_text


def test_decision_recommends_rollout_on_primary_win_no_guardrail_harm() -> None:
    df = pd.DataFrame(
        [
            {"metric": "activated_within_7d", "effect_abs": 0.02, "p_value": 0.01},
            {"metric": "cancelled_30d", "effect_abs": 0.0001, "p_value": 0.6},
            {"metric": "time_to_first_match_hours", "effect_abs": -0.1, "p_value": 0.3},
            {"metric": "support_tickets_30d", "effect_abs": -0.01, "p_value": 0.2},
        ]
    )

    decision, issues = _decision_text(df)

    assert "Recommend staged rollout" in decision
    assert issues == []
