from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CupedResult:
    adjusted_outcome: np.ndarray
    theta: float
    variance_reduction_pct: float
    raw_variance: float
    adjusted_variance: float


def apply_cuped(outcome: np.ndarray, covariate: np.ndarray) -> CupedResult:
    y = np.asarray(outcome, dtype=float)
    x = np.asarray(covariate, dtype=float)

    if len(y) != len(x):
        raise ValueError("Outcome and covariate must have same length")

    x_centered = x - x.mean()
    x_var = np.var(x_centered)

    if x_var == 0:
        adjusted = y.copy()
        raw_var = float(np.var(y))
        return CupedResult(
            adjusted_outcome=adjusted,
            theta=0.0,
            variance_reduction_pct=0.0,
            raw_variance=raw_var,
            adjusted_variance=raw_var,
        )

    theta = float(np.cov(y, x_centered, ddof=1)[0, 1] / np.var(x_centered, ddof=1))
    adjusted = y - theta * x_centered

    raw_var = float(np.var(y, ddof=1))
    adj_var = float(np.var(adjusted, ddof=1))
    variance_reduction = 100.0 * (1.0 - (adj_var / raw_var)) if raw_var > 0 else 0.0

    return CupedResult(
        adjusted_outcome=adjusted,
        theta=theta,
        variance_reduction_pct=float(variance_reduction),
        raw_variance=raw_var,
        adjusted_variance=adj_var,
    )
