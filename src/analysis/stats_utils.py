from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class ABEstimate:
    control_mean: float
    treatment_mean: float
    effect_abs: float
    effect_rel: float
    p_value: float
    ci_low: float
    ci_high: float
    n_control: int
    n_treatment: int


def bootstrap_diff_in_means(
    treatment: np.ndarray,
    control: np.ndarray,
    n_bootstrap: int = 2000,
    seed: int = 42,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)

    treatment = np.asarray(treatment)
    control = np.asarray(control)

    t_size = len(treatment)
    c_size = len(control)
    diffs = np.empty(n_bootstrap, dtype=float)

    for i in range(n_bootstrap):
        t_sample = treatment[rng.integers(0, t_size, t_size)]
        c_sample = control[rng.integers(0, c_size, c_size)]
        diffs[i] = t_sample.mean() - c_sample.mean()

    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def estimate_ab(
    treatment: np.ndarray,
    control: np.ndarray,
    n_bootstrap: int = 2000,
    seed: int = 42,
) -> ABEstimate:
    treatment = np.asarray(treatment, dtype=float)
    control = np.asarray(control, dtype=float)

    treatment_mean = float(np.mean(treatment))
    control_mean = float(np.mean(control))
    effect_abs = treatment_mean - control_mean
    effect_rel = effect_abs / control_mean if control_mean != 0 else np.nan

    t_var = float(np.var(treatment, ddof=1)) if len(treatment) > 1 else 0.0
    c_var = float(np.var(control, ddof=1)) if len(control) > 1 else 0.0
    se = math.sqrt((t_var / max(len(treatment), 1)) + (c_var / max(len(control), 1)))
    if se == 0.0:
        p_value = 1.0
    else:
        z = abs(effect_abs / se)
        # Two-sided normal approximation for large-sample A/B testing.
        p_value = math.erfc(z / math.sqrt(2.0))
    ci_low, ci_high = bootstrap_diff_in_means(
        treatment=treatment,
        control=control,
        n_bootstrap=n_bootstrap,
        seed=seed,
    )

    return ABEstimate(
        control_mean=control_mean,
        treatment_mean=treatment_mean,
        effect_abs=effect_abs,
        effect_rel=effect_rel,
        p_value=float(p_value),
        ci_low=ci_low,
        ci_high=ci_high,
        n_control=len(control),
        n_treatment=len(treatment),
    )
