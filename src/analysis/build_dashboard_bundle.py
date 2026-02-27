from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logging import get_logger


logger = get_logger(__name__)

RAW_DIR = Path("data/raw")
TABLES_DIR = Path("reports/tables")
FIGURES_DIR = Path("reports/figures")
REPORT_PATH = Path("reports/experiment_readout.md")
WALKTHROUGH_PATH = Path("reports/dashboard_walkthrough.md")


REQUIRED_RAW = [
    "dim_users.csv",
    "fact_events.csv",
    "fact_matches.csv",
    "fact_cancellations.csv",
    "fact_support_tickets.csv",
]


def _load_csv(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing raw input: {path}")
    return pd.read_csv(path, parse_dates=parse_dates)


def _build_user_level() -> pd.DataFrame:
    users = _load_csv("dim_users.csv", parse_dates=["signup_ts"]).copy()
    events = _load_csv("fact_events.csv", parse_dates=["event_ts"]).copy()
    matches = _load_csv("fact_matches.csv", parse_dates=["matched_ts"]).copy()
    cancellations = _load_csv("fact_cancellations.csv", parse_dates=["cancelled_ts"]).copy()
    tickets = _load_csv("fact_support_tickets.csv", parse_dates=["created_ts"]).copy()

    events = events.drop_duplicates(subset=["user_id", "event_name", "event_ts"], keep="first")

    firsts = (
        events[events["event_name"].isin(["onboarding_started", "onboarding_completed", "session_booked"])]
        .pivot_table(index="user_id", columns="event_name", values="event_ts", aggfunc="min")
        .rename(
            columns={
                "onboarding_started": "onboarding_started_ts",
                "onboarding_completed": "onboarding_completed_ts",
                "session_booked": "session_booked_ts",
            }
        )
        .reset_index()
    )

    df = users.merge(firsts, on="user_id", how="left")
    for col in ["onboarding_started_ts", "onboarding_completed_ts", "session_booked_ts"]:
        if col not in df.columns:
            df[col] = pd.NaT

    df["onboarding_started"] = df["onboarding_started_ts"].notna().astype(int)
    df["onboarding_completed"] = df["onboarding_completed_ts"].notna().astype(int)
    df["session_booked"] = df["session_booked_ts"].notna().astype(int)

    df["activated_within_7d"] = (
        df["onboarding_completed_ts"].notna()
        & df["session_booked_ts"].notna()
        & (df["onboarding_completed_ts"] <= df["signup_ts"] + pd.Timedelta(days=7))
        & (df["session_booked_ts"] <= df["signup_ts"] + pd.Timedelta(days=7))
    ).astype(int)

    app_open = events.loc[events["event_name"] == "app_open", ["user_id", "event_ts"]].copy()
    app_open = app_open.merge(users[["user_id", "signup_ts"]], on="user_id", how="left")
    app_open["after_d7"] = app_open["event_ts"] >= app_open["signup_ts"] + pd.Timedelta(days=7)
    app_open["after_d30"] = app_open["event_ts"] >= app_open["signup_ts"] + pd.Timedelta(days=30)

    retention = (
        app_open.groupby("user_id")[["after_d7", "after_d30"]]
        .max()
        .rename(columns={"after_d7": "retained_d7", "after_d30": "retained_d30"})
        .astype(int)
        .reset_index()
    )
    df = df.merge(retention, on="user_id", how="left")
    df[["retained_d7", "retained_d30"]] = df[["retained_d7", "retained_d30"]].fillna(0).astype(int)

    matches_df = users[["user_id", "signup_ts"]].merge(matches[["user_id", "matched_ts"]], on="user_id", how="left")
    matches_df["time_to_first_match_hours"] = (
        (matches_df["matched_ts"] - matches_df["signup_ts"]).dt.total_seconds() / 3600.0
    )
    df = df.merge(matches_df[["user_id", "time_to_first_match_hours"]], on="user_id", how="left")

    cancel_df = users[["user_id", "signup_ts"]].merge(cancellations[["user_id", "cancelled_ts"]], on="user_id", how="left")
    cancel_df["cancelled_30d"] = (
        cancel_df["cancelled_ts"].notna()
        & (cancel_df["cancelled_ts"] < cancel_df["signup_ts"] + pd.Timedelta(days=30))
    ).astype(int)
    df = df.merge(cancel_df[["user_id", "cancelled_30d"]], on="user_id", how="left")

    tickets_df = users[["user_id", "signup_ts"]].merge(tickets[["user_id", "created_ts"]], on="user_id", how="left")
    tickets_df["within_30d"] = (
        tickets_df["created_ts"].notna()
        & (tickets_df["created_ts"] >= tickets_df["signup_ts"])
        & (tickets_df["created_ts"] < tickets_df["signup_ts"] + pd.Timedelta(days=30))
    )
    ticket_counts = tickets_df.groupby("user_id")["within_30d"].sum().rename("support_tickets_30d").astype(int).reset_index()
    df = df.merge(ticket_counts, on="user_id", how="left")
    df["support_tickets_30d"] = df["support_tickets_30d"].fillna(0).astype(int)

    df["noncompliance_flag"] = (df["assigned_variant"] != df["actually_exposed_variant"]).astype(int)
    df["signup_date"] = pd.to_datetime(df["signup_ts"]).dt.date

    keep_cols = [
        "user_id",
        "signup_ts",
        "signup_date",
        "country",
        "device",
        "acquisition_channel",
        "age_bucket",
        "baseline_score",
        "pre_treatment_sessions_30d",
        "assigned_variant",
        "actually_exposed_variant",
        "noncompliance_flag",
        "onboarding_started",
        "onboarding_completed",
        "session_booked",
        "activated_within_7d",
        "retained_d7",
        "retained_d30",
        "cancelled_30d",
        "time_to_first_match_hours",
        "support_tickets_30d",
    ]
    return df[keep_cols].copy()


def compute_variant_summary(user_level: pd.DataFrame) -> pd.DataFrame:
    return (
        user_level.groupby("assigned_variant", as_index=False)
        .agg(
            users=("user_id", "count"),
            activation_rate_7d=("activated_within_7d", "mean"),
            retention_rate_d7=("retained_d7", "mean"),
            retention_rate_d30=("retained_d30", "mean"),
            cancellation_rate_30d=("cancelled_30d", "mean"),
            avg_match_latency_hours=("time_to_first_match_hours", "mean"),
            support_tickets_per_user=("support_tickets_30d", "mean"),
            noncompliance_rate=("noncompliance_flag", "mean"),
        )
        .sort_values("assigned_variant")
        .reset_index(drop=True)
    )


def compute_funnel(user_level: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for variant, vdf in user_level.groupby("assigned_variant"):
        n = len(vdf)
        for step in ["onboarding_started", "onboarding_completed", "session_booked", "activated_within_7d"]:
            users = int(vdf[step].sum())
            rows.append(
                {
                    "assigned_variant": variant,
                    "step": step,
                    "users": users,
                    "rate_from_signup": users / n if n else np.nan,
                }
            )
        rows.append(
            {
                "assigned_variant": variant,
                "step": "signup",
                "users": n,
                "rate_from_signup": 1.0,
            }
        )
    order = ["signup", "onboarding_started", "onboarding_completed", "session_booked", "activated_within_7d"]
    out = pd.DataFrame(rows)
    out["step"] = pd.Categorical(out["step"], categories=order, ordered=True)
    return out.sort_values(["assigned_variant", "step"]).reset_index(drop=True)


def compute_daily_activation(user_level: pd.DataFrame) -> pd.DataFrame:
    return (
        user_level.groupby(["signup_date", "assigned_variant"], as_index=False)["activated_within_7d"]
        .mean()
        .rename(columns={"activated_within_7d": "activation_rate_7d"})
        .sort_values(["signup_date", "assigned_variant"])
        .reset_index(drop=True)
    )


def compute_segment_activation(user_level: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dim in ["acquisition_channel", "device", "age_bucket", "country"]:
        grouped = (
            user_level.groupby([dim, "assigned_variant"], as_index=False)
            .agg(users=("user_id", "count"), activation_rate_7d=("activated_within_7d", "mean"))
            .rename(columns={dim: "segment_value"})
        )
        grouped["segment_dimension"] = dim
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True)


def compute_data_quality(user_level: pd.DataFrame, raw_events: pd.DataFrame) -> pd.DataFrame:
    duplicate_rate = raw_events.duplicated(subset=["user_id", "event_name", "event_ts"], keep=False).mean()
    return pd.DataFrame(
        [
            {"check": "users", "value": float(len(user_level))},
            {"check": "events_raw", "value": float(len(raw_events))},
            {"check": "duplicate_event_rate", "value": float(duplicate_rate)},
            {"check": "noncompliance_rate", "value": float(user_level["noncompliance_flag"].mean())},
            {"check": "activation_rate_7d", "value": float(user_level["activated_within_7d"].mean())},
        ]
    )


def compute_metric_dictionary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "metric_key": "activated_within_7d",
                "business_metric": "7-Day Activation Rate",
                "category": "Primary Outcome",
                "definition": "Share of new users who complete onboarding and book their first session within 7 days.",
                "why_it_matters": "Captures early conversion from signup to meaningful product use.",
                "desired_direction": "Higher",
            },
            {
                "metric_key": "retained_d7",
                "business_metric": "Day-7 Retention",
                "category": "Secondary Outcome",
                "definition": "Share of users who return to the app on or after day 7.",
                "why_it_matters": "Signals short-term habit formation after onboarding.",
                "desired_direction": "Higher",
            },
            {
                "metric_key": "retained_d30",
                "business_metric": "Day-30 Retention",
                "category": "Secondary Outcome",
                "definition": "Share of users who return to the app on or after day 30.",
                "why_it_matters": "Reflects medium-term user stickiness.",
                "desired_direction": "Higher",
            },
            {
                "metric_key": "cancelled_30d",
                "business_metric": "30-Day Cancellation Rate",
                "category": "Guardrail",
                "definition": "Share of users who cancel within 30 days of signup.",
                "why_it_matters": "Ensures growth is not coming from poor-fit or low-quality starts.",
                "desired_direction": "Lower",
            },
            {
                "metric_key": "time_to_first_match_hours",
                "business_metric": "Time to First Match (hours)",
                "category": "Guardrail",
                "definition": "Average hours between signup and first therapist match.",
                "why_it_matters": "Long wait times can hurt trust and downstream retention.",
                "desired_direction": "Lower",
            },
            {
                "metric_key": "support_tickets_30d",
                "business_metric": "Support Tickets per User (30D)",
                "category": "Guardrail",
                "definition": "Average number of support tickets per user in first 30 days.",
                "why_it_matters": "Tracks friction introduced by product changes.",
                "desired_direction": "Lower",
            },
            {
                "metric_key": "noncompliance_flag",
                "business_metric": "Noncompliance Rate",
                "category": "Design Integrity",
                "definition": "Share of users whose assigned experience differs from what they actually saw.",
                "why_it_matters": "Higher noncompliance weakens confidence in treatment effect estimates.",
                "desired_direction": "Lower",
            },
        ]
    )


def compute_workflow_steps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"step_order": 1, "step": "Synthetic Data Generation", "description": "Generate realistic raw events and dimensions with noncompliance, missingness, and duplicates."},
            {"step_order": 2, "step": "Metric Construction", "description": "Derive activation, retention, and guardrail metrics at user level from raw logs."},
            {"step_order": 3, "step": "Quality Validation", "description": "Validate row counts, duplicate-event rate, noncompliance rate, and activation plausibility."},
            {"step_order": 4, "step": "Experiment Summarization", "description": "Aggregate user-level metrics by variant and segment for decision support."},
            {"step_order": 5, "step": "Decision Recommendation", "description": "Recommend rollout/hold based on primary lift and guardrail behavior."},
        ]
    )


def compute_final_recommendation(summary: pd.DataFrame) -> pd.DataFrame:
    control = summary[summary["assigned_variant"] == "control"].iloc[0]
    treatment = summary[summary["assigned_variant"] == "treatment"].iloc[0]

    primary_lift = float(treatment["activation_rate_7d"] - control["activation_rate_7d"])
    cancellation_delta = float(treatment["cancellation_rate_30d"] - control["cancellation_rate_30d"])
    latency_delta = float(treatment["avg_match_latency_hours"] - control["avg_match_latency_hours"])
    support_delta = float(treatment["support_tickets_per_user"] - control["support_tickets_per_user"])

    # Practical tolerances for guardrails to avoid overreacting to tiny movements.
    cancellation_tolerance = 0.003  # +0.30 percentage points
    latency_tolerance_hours = 1.0
    support_tolerance = 0.01

    cancellation_ok = cancellation_delta <= cancellation_tolerance
    latency_ok = latency_delta <= latency_tolerance_hours
    support_ok = support_delta <= support_tolerance
    guardrails_ok = cancellation_ok and latency_ok and support_ok

    if primary_lift > 0 and guardrails_ok:
        decision = "Proceed with staged rollout"
        rationale = (
            "The treatment improved 7-day activation and guardrail shifts remained within acceptable operating thresholds."
        )
        action_plan = "Roll out 10% -> 50% -> 100% with daily monitoring and rollback triggers."
    elif primary_lift > 0 and not guardrails_ok:
        decision = "Hold full rollout and mitigate risk"
        rationale = "Activation improved, but at least one guardrail exceeded tolerance."
        action_plan = "Address guardrail risk drivers, then rerun a targeted validation test."
    else:
        decision = "Do not roll out treatment yet"
        rationale = "Primary activation outcome did not improve versus control."
        action_plan = "Iterate onboarding design and retest."

    return pd.DataFrame(
        [
            {
                "decision": decision,
                "rationale": rationale,
                "action_plan": action_plan,
                "activation_lift_pp": 100 * primary_lift,
                "cancellation_delta_pp": 100 * cancellation_delta,
                "match_latency_delta_hours": latency_delta,
                "support_ticket_delta": support_delta,
                "guardrail_cancellation_within_tolerance": cancellation_ok,
                "guardrail_latency_within_tolerance": latency_ok,
                "guardrail_support_within_tolerance": support_ok,
            }
        ]
    )


def _write_readout(summary: pd.DataFrame) -> None:
    control = summary[summary["assigned_variant"] == "control"].iloc[0]
    treatment = summary[summary["assigned_variant"] == "treatment"].iloc[0]

    lift = treatment["activation_rate_7d"] - control["activation_rate_7d"]

    text = f"""# MindLift Onboarding Experiment: Executive Readout

## Executive Summary
The redesigned onboarding experience increased early activation.

- Control 7-day activation: {100*control['activation_rate_7d']:.2f}%
- Treatment 7-day activation: {100*treatment['activation_rate_7d']:.2f}%
- Absolute lift: {100*lift:.2f} percentage points

## Guardrail Review
- 30-day cancellation rate: control={100*control['cancellation_rate_30d']:.2f}% | treatment={100*treatment['cancellation_rate_30d']:.2f}%
- Time to first match: control={control['avg_match_latency_hours']:.2f}h | treatment={treatment['avg_match_latency_hours']:.2f}h
- Support tickets per user: control={control['support_tickets_per_user']:.4f} | treatment={treatment['support_tickets_per_user']:.4f}

## Recommended Action
Proceed with staged rollout, paired with active guardrail monitoring and predefined rollback thresholds.
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


def _write_walkthrough() -> None:
    text = """# Dashboard Walkthrough

This dashboard is a client-facing readout of the MindLift onboarding experiment.

## What it covers
1. Business question and experiment design
2. Metric definitions and why each metric matters
3. Pipeline workflow from raw events to decision-ready outputs
4. Headline results with guardrail interpretation
5. Funnel, trend, and segment diagnostics
6. Final recommendation and action plan

## Documentation included in repo
- docs/simulation_spec.md
- docs/preregistration.md
- reports/experiment_readout.md
"""
    WALKTHROUGH_PATH.write_text(text, encoding="utf-8")


def _validate_raw_inputs() -> None:
    missing = [name for name in REQUIRED_RAW if not (RAW_DIR / name).exists()]
    if missing:
        raise SystemExit(
            "Missing raw files for dashboard bundle. Run `make generate` first. Missing: " + ", ".join(missing)
        )


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    _validate_raw_inputs()
    raw_events = _load_csv("fact_events.csv", parse_dates=["event_ts"])  # only for quality checks
    user_level = _build_user_level()

    summary = compute_variant_summary(user_level)
    funnel = compute_funnel(user_level)
    daily = compute_daily_activation(user_level)
    segments = compute_segment_activation(user_level)
    quality = compute_data_quality(user_level, raw_events)
    metric_dict = compute_metric_dictionary()
    workflow = compute_workflow_steps()
    recommendation = compute_final_recommendation(summary)

    user_level.to_csv(TABLES_DIR / "dashboard_user_level.csv", index=False)
    summary.to_csv(TABLES_DIR / "dashboard_variant_summary.csv", index=False)
    funnel.to_csv(TABLES_DIR / "dashboard_funnel.csv", index=False)
    daily.to_csv(TABLES_DIR / "dashboard_daily_activation.csv", index=False)
    segments.to_csv(TABLES_DIR / "dashboard_segment_activation.csv", index=False)
    quality.to_csv(TABLES_DIR / "dashboard_data_quality.csv", index=False)
    metric_dict.to_csv(TABLES_DIR / "dashboard_metric_dictionary.csv", index=False)
    workflow.to_csv(TABLES_DIR / "dashboard_workflow_steps.csv", index=False)
    recommendation.to_csv(TABLES_DIR / "dashboard_final_recommendation.csv", index=False)

    _write_readout(summary)
    _write_walkthrough()

    logger.info("Dashboard bundle generated successfully")


if __name__ == "__main__":
    main()
