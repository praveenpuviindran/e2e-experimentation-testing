from __future__ import annotations

import math
from statistics import NormalDist


def required_n_per_group_binary(
    baseline_rate: float,
    mde_abs: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    p1 = min(max(baseline_rate, 1e-6), 1 - 1e-6)
    p2 = min(max(baseline_rate + mde_abs, 1e-6), 1 - 1e-6)

    z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
    z_beta = NormalDist().inv_cdf(power)

    p_bar = (p1 + p2) / 2
    term1 = z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
    term2 = z_beta * math.sqrt((p1 * (1 - p1)) + (p2 * (1 - p2)))

    n = ((term1 + term2) ** 2) / (mde_abs**2)
    return int(math.ceil(n))


def mde_binary_for_sample_size(
    baseline_rate: float,
    n_control: int,
    n_treatment: int,
    alpha: float = 0.05,
    power: float = 0.8,
) -> float:
    n_per_group = max(2, min(n_control, n_treatment))

    low, high = 1e-4, 0.5
    for _ in range(40):
        mid = (low + high) / 2
        needed = required_n_per_group_binary(
            baseline_rate=baseline_rate,
            mde_abs=mid,
            alpha=alpha,
            power=power,
        )
        if needed <= n_per_group:
            high = mid
        else:
            low = mid

    return float(high)
