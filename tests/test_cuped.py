import numpy as np

from src.analysis.cuped import apply_cuped


def test_cuped_reduces_variance_with_correlated_covariate() -> None:
    """CUPED adjustment on a strongly correlated covariate should reduce outcome variance.

    When y and x are positively correlated (r ≈ 0.6), subtracting theta * (x - mean(x))
    should produce an adjusted outcome with strictly lower variance than the raw outcome.
    """
    rng = np.random.default_rng(123)
    x = rng.normal(0, 1, 4000)
    y = 0.6 * x + rng.normal(0, 1, 4000)

    result = apply_cuped(y, x)

    assert result.adjusted_variance < result.raw_variance
    assert result.variance_reduction_pct > 0
