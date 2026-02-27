from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, text

from src.analysis.power import mde_binary_for_sample_size, required_n_per_group_binary
from src.analysis.stats_utils import estimate_ab
from src.utils.config import get_database_url
from src.utils.logging import get_logger


logger = get_logger(__name__)

TABLES_DIR = Path("reports/tables")
FIGURES_DIR = Path("reports/figures")

METRICS = [
    "activated_within_7d",
    "retained_d7",
    "retained_d30",
    "cancelled_30d",
    "time_to_first_match_hours",
    "support_tickets_30d",
]


def _load_experiment_data() -> pd.DataFrame:
    engine = create_engine(get_database_url())
    query = text(
        """
        SELECT
            user_id,
            assigned_variant,
            acquisition_channel,
            baseline_score,
            activated_within_7d,
            retained_d7,
            retained_d30,
            cancelled_30d,
            time_to_first_match_hours,
            support_tickets_30d
        FROM vw_experiment_user_metrics
        WHERE assigned_variant IN ('control', 'treatment')
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def _estimate_metrics(df: pd.DataFrame, n_bootstrap: int = 2000, seed: int = 42) -> pd.DataFrame:
    out_rows = []

    control_df = df[df["assigned_variant"] == "control"].copy()
    treatment_df = df[df["assigned_variant"] == "treatment"].copy()

    for metric in METRICS:
        control_vals = control_df[metric].dropna().to_numpy()
        treatment_vals = treatment_df[metric].dropna().to_numpy()

        estimate = estimate_ab(
            treatment=treatment_vals,
            control=control_vals,
            n_bootstrap=n_bootstrap,
            seed=seed,
        )

        out_rows.append(
            {
                "metric": metric,
                "control_mean": estimate.control_mean,
                "treatment_mean": estimate.treatment_mean,
                "effect_abs": estimate.effect_abs,
                "effect_rel": estimate.effect_rel,
                "ci_low": estimate.ci_low,
                "ci_high": estimate.ci_high,
                "p_value": estimate.p_value,
                "n_control": estimate.n_control,
                "n_treatment": estimate.n_treatment,
                "analysis_method": "difference_in_means + bootstrap_ci",
            }
        )

    return pd.DataFrame(out_rows)


def _plot_metric_rates(results: pd.DataFrame, output_path: Path) -> None:
    subset = results[results["metric"].isin(["activated_within_7d", "retained_d7", "retained_d30"])].copy()
    subset = subset.sort_values("metric")

    x = range(len(subset))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - width / 2 for i in x], subset["control_mean"], width=width, label="Control")
    ax.bar([i + width / 2 for i in x], subset["treatment_mean"], width=width, label="Treatment")

    ax.set_xticks(list(x))
    ax.set_xticklabels(subset["metric"], rotation=15, ha="right")
    ax.set_ylabel("Rate")
    ax.set_title("MindLift: Primary and Secondary Metric Rates")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _plot_effects(results: pd.DataFrame, output_path: Path) -> None:
    plot_df = results.sort_values("effect_abs").copy()
    y = range(len(plot_df))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.errorbar(
        x=plot_df["effect_abs"],
        y=list(y),
        xerr=[plot_df["effect_abs"] - plot_df["ci_low"], plot_df["ci_high"] - plot_df["effect_abs"]],
        fmt="o",
        capsize=3,
    )
    ax.axvline(0.0, color="black", linewidth=1, linestyle="--")
    ax.set_yticks(list(y))
    ax.set_yticklabels(plot_df["metric"])
    ax.set_xlabel("Treatment - Control")
    ax.set_title("Effect Estimates with 95% Bootstrap CI")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading experiment user metrics from PostgreSQL")
    df = _load_experiment_data()
    logger.info("Loaded %s rows", len(df))

    results = _estimate_metrics(df)

    results_path = TABLES_DIR / "ab_results_v1.csv"
    results.to_csv(results_path, index=False)
    logger.info("Wrote %s", results_path)

    primary_row = results.loc[results["metric"] == "activated_within_7d"].iloc[0]
    baseline_rate = float(primary_row["control_mean"])
    n_control = int(primary_row["n_control"])
    n_treatment = int(primary_row["n_treatment"])
    observed_mde = mde_binary_for_sample_size(
        baseline_rate=baseline_rate,
        n_control=n_control,
        n_treatment=n_treatment,
        alpha=0.05,
        power=0.80,
    )
    required_n_for_1pp = required_n_per_group_binary(
        baseline_rate=baseline_rate,
        mde_abs=0.01,
        alpha=0.05,
        power=0.80,
    )

    power_df = pd.DataFrame(
        [
            {
                "metric": "activated_within_7d",
                "alpha": 0.05,
                "power": 0.80,
                "baseline_rate_control": baseline_rate,
                "n_control": n_control,
                "n_treatment": n_treatment,
                "observed_mde_abs": observed_mde,
                "required_n_per_group_for_1pp_lift": required_n_for_1pp,
            }
        ]
    )
    power_path = TABLES_DIR / "power_mde.csv"
    power_df.to_csv(power_path, index=False)
    logger.info("Wrote %s", power_path)

    rates_path = FIGURES_DIR / "metric_rates_v1.png"
    effects_path = FIGURES_DIR / "effect_estimates_v1.png"
    _plot_metric_rates(results, rates_path)
    _plot_effects(results, effects_path)
    logger.info("Wrote %s", rates_path)
    logger.info("Wrote %s", effects_path)


if __name__ == "__main__":
    main()
