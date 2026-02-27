from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.utils.logging import get_logger


logger = get_logger(__name__)

REPORTS_DIR = Path("reports")
TABLES_DIR = REPORTS_DIR / "tables"


def _fmt_pct(value: float) -> str:
    return f"{100 * value:.2f}%"


def _fmt_num(value: float) -> str:
    return f"{value:.4f}"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ab_results = pd.read_csv(TABLES_DIR / "ab_results_v1.csv")
    power_mde = pd.read_csv(TABLES_DIR / "power_mde.csv")
    cuped = pd.read_csv(TABLES_DIR / "cuped_results.csv")
    segments = pd.read_csv(TABLES_DIR / "segment_analysis.csv")
    return ab_results, power_mde, cuped, segments


def _decision_text(ab_results: pd.DataFrame) -> tuple[str, list[str]]:
    primary = ab_results.loc[ab_results["metric"] == "activated_within_7d"].iloc[0]

    guardrails = ab_results[ab_results["metric"].isin(["cancelled_30d", "time_to_first_match_hours", "support_tickets_30d"])].copy()
    guardrail_issues = []

    for row in guardrails.itertuples(index=False):
        if row.effect_abs > 0 and row.p_value < 0.05:
            guardrail_issues.append(f"{row.metric} worsened (effect={row.effect_abs:.4f}, p={row.p_value:.4f})")

    primary_win = (primary.effect_abs > 0) and (primary.p_value < 0.05)

    if primary_win and not guardrail_issues:
        decision = "Recommend staged rollout of treatment onboarding (10% -> 50% -> 100%) with guardrail monitoring."
    elif primary_win and guardrail_issues:
        decision = "Do not fully roll out yet; primary improved but guardrail risks require mitigation and follow-up test."
    else:
        decision = "Do not roll out treatment yet; primary metric did not meet decision threshold."

    return decision, guardrail_issues


def _build_markdown(
    ab_results: pd.DataFrame,
    power_mde: pd.DataFrame,
    cuped: pd.DataFrame,
    segments: pd.DataFrame,
) -> tuple[str, str, pd.DataFrame]:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    primary = ab_results.loc[ab_results["metric"] == "activated_within_7d"].iloc[0]
    secondary = ab_results[ab_results["metric"].isin(["retained_d7", "retained_d30"])].copy()
    guardrails = ab_results[ab_results["metric"].isin(["cancelled_30d", "time_to_first_match_hours", "support_tickets_30d"])].copy()

    mde_row = power_mde.iloc[0]
    decision, guardrail_issues = _decision_text(ab_results)

    sig_segments = segments[segments["significant_fdr_05"] == True].copy()  # noqa: E712
    top_segment = sig_segments.sort_values("effect_abs", ascending=False).head(1)

    cuped_reduction = cuped["variance_reduction_pct"].mean() if not cuped.empty else 0.0

    kpi_snapshot = pd.DataFrame(
        [
            {
                "primary_metric": "activated_within_7d",
                "control_rate": primary.control_mean,
                "treatment_rate": primary.treatment_mean,
                "absolute_lift": primary.effect_abs,
                "p_value": primary.p_value,
                "ci_low": primary.ci_low,
                "ci_high": primary.ci_high,
                "observed_mde_abs": mde_row.observed_mde_abs,
                "mean_cuped_variance_reduction_pct": cuped_reduction,
            }
        ]
    )

    sec_lines = "\n".join(
        [
            f"- `{row.metric}`: control={_fmt_pct(row.control_mean)}, treatment={_fmt_pct(row.treatment_mean)}, lift={_fmt_pct(row.effect_abs)}, p={_fmt_num(row.p_value)}"
            for row in secondary.itertuples(index=False)
        ]
    )

    guardrail_lines = "\n".join(
        [
            f"- `{row.metric}`: control={_fmt_num(row.control_mean)}, treatment={_fmt_num(row.treatment_mean)}, delta={_fmt_num(row.effect_abs)}, p={_fmt_num(row.p_value)}"
            for row in guardrails.itertuples(index=False)
        ]
    )

    segment_note = (
        f"Top significant segment: `{top_segment.iloc[0]['segment_dimension']}={top_segment.iloc[0]['segment_value']}` "
        f"with lift={_fmt_pct(top_segment.iloc[0]['effect_abs'])} (FDR p={_fmt_num(top_segment.iloc[0]['p_value_fdr'])})."
        if not top_segment.empty
        else "No segment passed FDR significance threshold in pre-registered segment analysis."
    )

    risk_lines = "\n".join([f"- {issue}" for issue in guardrail_issues]) if guardrail_issues else "- No statistically significant guardrail degradations detected."

    readout_md = f"""# MindLift Experiment Readout

Generated: {now_utc}

## 1) Hypothesis
The redesigned onboarding flow increases 7-day activation without harming cancellation rate, match latency, or support burden.

## 2) Design Summary
- Randomization: 50/50 by `assigned_variant` (ITT primary)
- Population: new signups
- Primary metric: `activated_within_7d`
- Secondary metrics: `retained_d7`, `retained_d30`
- Guardrails: `cancelled_30d`, `time_to_first_match_hours`, `support_tickets_30d`

## 3) Primary Result
- Control activation: {_fmt_pct(primary.control_mean)}
- Treatment activation: {_fmt_pct(primary.treatment_mean)}
- Absolute lift: {_fmt_pct(primary.effect_abs)}
- 95% CI: [{_fmt_pct(primary.ci_low)}, {_fmt_pct(primary.ci_high)}]
- p-value: {_fmt_num(primary.p_value)}

## 4) Secondary Results
{sec_lines}

## 5) Guardrails
{guardrail_lines}

## 6) Power / MDE
- Observed sample sizes: control={int(mde_row.n_control)}, treatment={int(mde_row.n_treatment)}
- Observed MDE (80% power, alpha=0.05): {_fmt_pct(mde_row.observed_mde_abs)}
- Required n/group for +1pp lift: {int(mde_row.required_n_per_group_for_1pp_lift)}

## 7) CUPED
- Mean variance reduction across primary/secondary metrics: {cuped_reduction:.2f}%

## 8) Segment Analysis (Pre-Registered)
- Segments tested: acquisition_channel, device, age_bucket
- {segment_note}

## 9) Decision Recommendation
{decision}

## 10) Risks
{risk_lines}

## 11) Next Steps
1. Run a staged production rollout with guardrail alert thresholds.
2. Validate instrumentation quality for onboarding-complete/session-booked events.
3. Re-run experiment or holdout monitoring if rollout proceeds.
"""

    exec_md = f"""# MindLift Executive Summary (One Page)

## Recommendation
{decision}

## Key KPI
- Activation lift (7-day): {_fmt_pct(primary.effect_abs)} ({_fmt_pct(primary.control_mean)} -> {_fmt_pct(primary.treatment_mean)})

## Statistical Rigor
- 95% CI for activation lift: [{_fmt_pct(primary.ci_low)}, {_fmt_pct(primary.ci_high)}]
- Observed MDE at current traffic: {_fmt_pct(mde_row.observed_mde_abs)}
- CUPED mean variance reduction: {cuped_reduction:.2f}%

## Guardrails
{risk_lines}

## Practical Next Step
Run staged rollout with explicit stop criteria for guardrails and keep ITT monitoring as primary decision framework.
"""

    return readout_md, exec_md, kpi_snapshot


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    ab_results, power_mde, cuped, segments = _load_inputs()
    readout_md, exec_md, kpi_snapshot = _build_markdown(ab_results, power_mde, cuped, segments)

    readout_path = REPORTS_DIR / "experiment_readout.md"
    readout_path.write_text(readout_md, encoding="utf-8")
    logger.info("Wrote %s", readout_path)

    exec_path = REPORTS_DIR / "executive_summary.md"
    exec_path.write_text(exec_md, encoding="utf-8")
    logger.info("Wrote %s", exec_path)

    snapshot_path = TABLES_DIR / "readout_kpi_snapshot.csv"
    kpi_snapshot.to_csv(snapshot_path, index=False)
    logger.info("Wrote %s", snapshot_path)


if __name__ == "__main__":
    main()
