import pandas as pd

from src.analysis.build_dashboard_bundle import compute_funnel, compute_variant_summary


def _sample_user_level() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4],
            "assigned_variant": ["control", "control", "treatment", "treatment"],
            "activated_within_7d": [0, 1, 1, 1],
            "retained_d7": [0, 1, 1, 1],
            "retained_d30": [0, 0, 1, 1],
            "cancelled_30d": [0, 0, 1, 0],
            "time_to_first_match_hours": [5.0, 8.0, 4.0, 6.0],
            "support_tickets_30d": [0, 1, 0, 0],
            "noncompliance_flag": [0, 0, 1, 0],
            "onboarding_started": [1, 1, 1, 1],
            "onboarding_completed": [0, 1, 1, 1],
            "session_booked": [0, 1, 1, 1],
        }
    )


def test_compute_variant_summary_shape() -> None:
    """Variant summary should contain one row per variant with the expected metric columns.

    Given a user-level table with 2 variants (control, treatment), the summary should
    return exactly 2 rows and include key rate columns used by the dashboard.
    """
    summary = compute_variant_summary(_sample_user_level())
    assert len(summary) == 2
    assert {"activation_rate_7d", "retention_rate_d7", "noncompliance_rate"}.issubset(summary.columns)


def test_compute_funnel_has_signup_and_activation_rows() -> None:
    """Funnel table should have one row per (step, variant) pair including signup and activation.

    With 2 variants and 5 funnel steps (signup, onboarding_started, onboarding_completed,
    session_booked, activated_within_7d), the funnel frame should have exactly 10 rows.
    """
    funnel = compute_funnel(_sample_user_level())
    assert {"signup", "activated_within_7d"}.issubset(set(funnel["step"]))
    assert len(funnel) == 10
