from __future__ import annotations

from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from src.utils.logging import get_logger


logger = get_logger(__name__)

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed/tableau")


def _load_csv(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing required raw input: {path}")
    return pd.read_csv(path, parse_dates=parse_dates)


def _build_user_level_dataset() -> pd.DataFrame:
    users = _load_csv("dim_users.csv", parse_dates=["signup_ts"]).copy()
    events = _load_csv("fact_events.csv", parse_dates=["event_ts"]).copy()
    matches = _load_csv("fact_matches.csv", parse_dates=["matched_ts"]).copy()
    cancellations = _load_csv("fact_cancellations.csv", parse_dates=["cancelled_ts"]).copy()
    tickets = _load_csv("fact_support_tickets.csv", parse_dates=["created_ts"]).copy()

    logger.info("Loaded raw files | users=%s events=%s", len(users), len(events))

    events = events.drop_duplicates(subset=["user_id", "event_name", "event_ts"], keep="first")
    logger.info("Deduped events | rows=%s", len(events))

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

    for ts_col in ["onboarding_started_ts", "onboarding_completed_ts", "session_booked_ts"]:
        if ts_col not in df.columns:
            df[ts_col] = pd.NaT

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
    ticket_counts = (
        tickets_df.groupby("user_id")["within_30d"].sum().rename("support_tickets_30d").astype(int).reset_index()
    )
    df = df.merge(ticket_counts, on="user_id", how="left")
    df["support_tickets_30d"] = df["support_tickets_30d"].fillna(0).astype(int)

    df["saw_treatment"] = (df["actually_exposed_variant"] == "treatment").astype(int)
    df["signup_date"] = pd.to_datetime(df["signup_ts"]).dt.date
    df["signup_week"] = pd.to_datetime(df["signup_ts"]).dt.to_period("W").astype(str)

    keep_cols = [
        "user_id",
        "signup_ts",
        "signup_date",
        "signup_week",
        "country",
        "device",
        "acquisition_channel",
        "age_bucket",
        "baseline_score",
        "pre_treatment_sessions_30d",
        "assigned_variant",
        "actually_exposed_variant",
        "saw_treatment",
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
    out = df[keep_cols].copy()
    return out


def _build_variant_summary(user_level: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    grouped = (
        user_level.groupby("assigned_variant", as_index=False)
        .agg(
            users=("user_id", "count"),
            activation_rate_7d=("activated_within_7d", "mean"),
            retention_rate_d7=("retained_d7", "mean"),
            retention_rate_d30=("retained_d30", "mean"),
            cancellation_rate_30d=("cancelled_30d", "mean"),
            avg_time_to_first_match_hours=("time_to_first_match_hours", "mean"),
            support_tickets_per_user_30d=("support_tickets_30d", "mean"),
        )
        .sort_values("assigned_variant")
    )

    control = grouped[grouped["assigned_variant"] == "control"].iloc[0]
    treatment = grouped[grouped["assigned_variant"] == "treatment"].iloc[0]

    metrics = [
        "activation_rate_7d",
        "retention_rate_d7",
        "retention_rate_d30",
        "cancellation_rate_30d",
        "avg_time_to_first_match_hours",
        "support_tickets_per_user_30d",
    ]

    lift_rows = []
    for metric in metrics:
        c = float(control[metric])
        t = float(treatment[metric])
        lift_rows.append(
            {
                "metric": metric,
                "control_value": c,
                "treatment_value": t,
                "absolute_lift": t - c,
                "relative_lift": (t - c) / c if c != 0 else np.nan,
            }
        )

    return grouped, pd.DataFrame(lift_rows)


def _build_funnel(user_level: pd.DataFrame) -> pd.DataFrame:
    rows = []
    steps = [
        (1, "signup", np.ones(len(user_level), dtype=int)),
        (2, "onboarding_started", user_level["onboarding_started"].to_numpy()),
        (3, "onboarding_completed", user_level["onboarding_completed"].to_numpy()),
        (4, "session_booked", user_level["session_booked"].to_numpy()),
        (5, "activated_within_7d", user_level["activated_within_7d"].to_numpy()),
    ]

    for variant, vdf in user_level.groupby("assigned_variant"):
        n = len(vdf)
        for step_order, step_name, _ in steps:
            if step_name == "signup":
                step_users = n
            else:
                step_users = int(vdf[step_name].sum())
            rows.append(
                {
                    "assigned_variant": variant,
                    "step_order": step_order,
                    "step_name": step_name,
                    "users": step_users,
                    "rate_from_signup": step_users / n if n else np.nan,
                }
            )

    return pd.DataFrame(rows)


def _build_daily_timeseries(user_level: pd.DataFrame) -> pd.DataFrame:
    ts = (
        user_level.groupby(["signup_date", "assigned_variant"], as_index=False)
        .agg(
            users=("user_id", "count"),
            activation_rate_7d=("activated_within_7d", "mean"),
            retention_rate_d7=("retained_d7", "mean"),
            retention_rate_d30=("retained_d30", "mean"),
            cancellation_rate_30d=("cancelled_30d", "mean"),
            avg_time_to_first_match_hours=("time_to_first_match_hours", "mean"),
            support_tickets_per_user_30d=("support_tickets_30d", "mean"),
        )
        .sort_values(["signup_date", "assigned_variant"])
    )
    return ts


def _build_segment_metrics(user_level: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metric_cols = [
        "activated_within_7d",
        "retained_d7",
        "retained_d30",
        "cancelled_30d",
        "support_tickets_30d",
        "time_to_first_match_hours",
    ]

    for segment_col in ["acquisition_channel", "device", "age_bucket", "country"]:
        for (segment_value, variant), sdf in user_level.groupby([segment_col, "assigned_variant"]):
            row = {
                "segment_dimension": segment_col,
                "segment_value": segment_value,
                "assigned_variant": variant,
                "users": len(sdf),
            }
            for metric in metric_cols:
                row[metric] = float(sdf[metric].mean())
            rows.append(row)

    return pd.DataFrame(rows)


def _build_dashboard_manifest() -> str:
    return """# Tableau Dashboard Build Manifest (MindLift)

## Upload-first file (single source)
Use `mindlift_tableau_user_level.csv` for all sheets.

## Recommended worksheets (9)
1. KPI Cards
2. Funnel by Variant
3. Daily Activation Trend
4. Retention Comparison (D7 vs D30)
5. Guardrail Comparison
6. Segment Lift by Acquisition Channel
7. Segment Lift by Device
8. Segment Lift by Age Bucket
9. Noncompliance Snapshot (Assigned vs Exposed)

## Required calculated fields in Tableau
1. `Activation Rate 7D` = AVG([activated_within_7d])
2. `D7 Retention Rate` = AVG([retained_d7])
3. `D30 Retention Rate` = AVG([retained_d30])
4. `Cancellation Rate 30D` = AVG([cancelled_30d])
5. `Support Tickets per User` = AVG([support_tickets_30d])
6. `Treatment Users` = SUM(IIF([assigned_variant]="treatment",1,0))
7. `Control Users` = SUM(IIF([assigned_variant]="control",1,0))
8. `Exposed to Treatment Rate` = AVG([saw_treatment])
9. `Activated Users` = SUM([activated_within_7d])
10. `Activation Lift vs Control` =
   (WINDOW_AVG(IF [assigned_variant]="treatment" THEN [Activation Rate 7D] END)
   - WINDOW_AVG(IF [assigned_variant]="control" THEN [Activation Rate 7D] END))

## Dashboard filters (global)
- signup_date (range)
- acquisition_channel
- device
- age_bucket
- country
"""


def export_tableau_assets() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    user_level = _build_user_level_dataset()
    summary_by_variant, lift_summary = _build_variant_summary(user_level)
    funnel = _build_funnel(user_level)
    daily = _build_daily_timeseries(user_level)
    segment = _build_segment_metrics(user_level)

    outputs = {
        "mindlift_tableau_user_level.csv": user_level,
        "mindlift_variant_summary.csv": summary_by_variant,
        "mindlift_lift_summary.csv": lift_summary,
        "mindlift_funnel_summary.csv": funnel,
        "mindlift_daily_metrics.csv": daily,
        "mindlift_segment_metrics.csv": segment,
    }

    for filename, frame in outputs.items():
        path = OUT_DIR / filename
        frame.to_csv(path, index=False)
        logger.info("Wrote %s (%s rows)", path, len(frame))

    manifest_path = OUT_DIR / "tableau_manifest.md"
    manifest_path.write_text(_build_dashboard_manifest(), encoding="utf-8")
    logger.info("Wrote %s", manifest_path)

    zip_path = OUT_DIR / "mindlift_tableau_upload_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename in outputs:
            zf.write(OUT_DIR / filename, arcname=filename)
        zf.write(manifest_path, arcname="tableau_manifest.md")
    logger.info("Wrote %s", zip_path)


def main() -> None:
    export_tableau_assets()


if __name__ == "__main__":
    main()
