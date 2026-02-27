import numpy as np

from src.analysis.multiple_testing import benjamini_hochberg


def test_bh_adjusted_values_are_monotone_when_sorted() -> None:
    p = np.array([0.04, 0.002, 0.3, 0.01, 0.2])
    q = benjamini_hochberg(p)

    order = np.argsort(p)
    sorted_q = q[order]
    assert np.all(sorted_q[:-1] <= sorted_q[1:])
    assert np.all((q >= 0) & (q <= 1))
