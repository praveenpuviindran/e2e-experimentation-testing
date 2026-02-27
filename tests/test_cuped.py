import numpy as np

from src.analysis.cuped import apply_cuped


def test_cuped_reduces_variance_with_correlated_covariate() -> None:
    rng = np.random.default_rng(123)
    x = rng.normal(0, 1, 4000)
    y = 0.6 * x + rng.normal(0, 1, 4000)

    result = apply_cuped(y, x)

    assert result.adjusted_variance < result.raw_variance
    assert result.variance_reduction_pct > 0
