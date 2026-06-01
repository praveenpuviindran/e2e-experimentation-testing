import numpy as np

from src.analysis.multiple_testing import benjamini_hochberg


def test_bh_adjusted_values_are_monotone_when_sorted() -> None:
    """Benjamini-Hochberg adjusted p-values must be monotone non-decreasing when sorted by rank.

    The BH procedure adjusts p-values as q_i = p_(i) * m / i (capped at 1, made monotone).
    After sorting by raw p-value, the adjusted values should be non-decreasing and all in [0, 1].
    """
    p = np.array([0.04, 0.002, 0.3, 0.01, 0.2])
    q = benjamini_hochberg(p)

    order = np.argsort(p)
    sorted_q = q[order]
    assert np.all(sorted_q[:-1] <= sorted_q[1:])
    assert np.all((q >= 0) & (q <= 1))
