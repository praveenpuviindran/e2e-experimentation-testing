import numpy as np

from src.analysis.stats_utils import bootstrap_diff_in_means, estimate_ab


def test_bootstrap_ci_contains_true_difference_for_simple_case() -> None:
    """Bootstrap confidence interval should bracket the observed difference in means.

    For a simple binary example with a clear treatment lift, the 95% CI produced by
    bootstrap_diff_in_means must contain the observed (non-bootstrapped) difference.
    """
    control = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    treatment = np.array([1, 1, 1, 1, 0, 1, 1, 1])

    ci_low, ci_high = bootstrap_diff_in_means(treatment=treatment, control=control, n_bootstrap=1000, seed=7)

    observed = treatment.mean() - control.mean()
    assert ci_low <= observed <= ci_high


def test_estimate_ab_returns_expected_fields() -> None:
    """estimate_ab should return a result struct with all required fields and valid values.

    Verifies that the effect direction is correct (treatment > control), sample sizes
    are recorded accurately, and the p-value is a valid probability in [0, 1].
    """
    control = np.array([1.0, 2.0, 3.0, 4.0])
    treatment = np.array([2.0, 3.0, 4.0, 5.0])

    est = estimate_ab(treatment=treatment, control=control, n_bootstrap=500, seed=9)

    assert est.effect_abs > 0
    assert est.n_control == 4
    assert est.n_treatment == 4
    assert 0.0 <= est.p_value <= 1.0
