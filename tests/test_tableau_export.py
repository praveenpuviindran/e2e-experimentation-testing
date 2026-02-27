import pandas as pd

from src.analysis.export_tableau_data import _build_funnel, _build_variant_summary


def _sample_user_level() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4],
            "assigned_variant": ["control", "control", "treatment", "treatment"],
            "onboarding_started": [1, 1, 1, 1],
            "onboarding_completed": [1, 0, 1, 1],
            "session_booked": [1, 0, 1, 0],
            "activated_within_7d": [1, 0, 1, 0],
            "retained_d7": [1, 0, 1, 1],
            "retained_d30": [0, 0, 1, 0],
            "cancelled_30d": [0, 0, 0, 1],
            "time_to_first_match_hours": [10.0, 20.0, 9.0, 8.0],
            "support_tickets_30d": [0, 1, 0, 0],
        }
    )


def test_build_variant_summary_shapes() -> None:
    grouped, lift = _build_variant_summary(_sample_user_level())
    assert len(grouped) == 2
    assert len(lift) == 6
    assert {"control_value", "treatment_value", "absolute_lift"}.issubset(lift.columns)


def test_build_funnel_has_all_steps_per_variant() -> None:
    funnel = _build_funnel(_sample_user_level())
    assert len(funnel) == 10
    assert set(funnel["step_name"]) == {
        "signup",
        "onboarding_started",
        "onboarding_completed",
        "session_booked",
        "activated_within_7d",
    }
