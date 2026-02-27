from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class SimulationConfig:
    n_users: int = 75000
    seed: int = 42
    output_dir: Path = Path("data/raw")
    signup_start_date: str = "2025-01-01"
    signup_days: int = 120


def _clip_prob(values: np.ndarray, lower: float = 0.01, upper: float = 0.99) -> np.ndarray:
    return np.clip(values, lower, upper)


def _build_user_frame(cfg: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    n_users = cfg.n_users

    signup_start = np.datetime64(cfg.signup_start_date)
    signup_offsets = rng.integers(0, cfg.signup_days, n_users)
    signup_seconds = rng.integers(0, 24 * 60 * 60, n_users)
    signup_ts = (
        signup_start
        + signup_offsets.astype("timedelta64[D]")
        + signup_seconds.astype("timedelta64[s]")
    )

    channels = rng.choice(["organic", "paid", "referral"], size=n_users, p=[0.50, 0.35, 0.15])
    baseline_by_channel = {"organic": 2.4, "paid": 1.8, "referral": 2.7}
    pre_sessions = np.array([rng.poisson(baseline_by_channel[ch]) for ch in channels])

    assigned_variant = np.where(rng.random(n_users) < 0.5, "control", "treatment")

    # Noncompliance / imperfect rollout
    exposed_variant = assigned_variant.copy()
    treat_idx = assigned_variant == "treatment"
    control_idx = ~treat_idx
    exposed_variant[treat_idx & (rng.random(n_users) < 0.18)] = "control"
    exposed_variant[control_idx & (rng.random(n_users) < 0.02)] = "treatment"

    users = pd.DataFrame(
        {
            "user_id": np.arange(1, n_users + 1, dtype=np.int64),
            "signup_ts": pd.to_datetime(signup_ts),
            "country": rng.choice(["US", "CA", "GB", "IN", "AU"], size=n_users, p=[0.56, 0.14, 0.11, 0.13, 0.06]),
            "device": rng.choice(["ios", "android", "web"], size=n_users, p=[0.46, 0.44, 0.10]),
            "acquisition_channel": channels,
            "age_bucket": rng.choice(["18-24", "25-34", "35-44", "45+"], size=n_users, p=[0.20, 0.40, 0.25, 0.15]),
            "baseline_score": rng.beta(2.2, 1.9, size=n_users).round(6),
            "assigned_variant": assigned_variant,
            "actually_exposed_variant": exposed_variant,
            "pre_treatment_sessions_30d": pre_sessions,
        }
    )
    return users


def _derive_experiment_outcomes(
    users: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    df = users[["user_id", "signup_ts", "acquisition_channel", "baseline_score", "actually_exposed_variant"]].copy()
    weekend = df["signup_ts"].dt.weekday >= 5

    channel_activation = {"organic": 0.36, "paid": 0.30, "referral": 0.41}
    channel_d7 = {"organic": 0.33, "paid": 0.27, "referral": 0.37}
    channel_d30 = {"organic": 0.23, "paid": 0.17, "referral": 0.26}
    channel_subscribe = {"organic": 0.54, "paid": 0.49, "referral": 0.58}

    activation_prob = df["acquisition_channel"].map(channel_activation).to_numpy(dtype=float)
    activation_prob += 0.12 * (df["baseline_score"].to_numpy() - 0.5)
    activation_prob -= np.where(weekend.to_numpy(), 0.03, 0.0)

    hetero_lift = np.where(
        df["acquisition_channel"].to_numpy() == "paid",
        0.045,
        np.where(df["acquisition_channel"].to_numpy() == "organic", 0.015, 0.025),
    )
    exposed_treat = df["actually_exposed_variant"].to_numpy() == "treatment"
    activation_prob += np.where(exposed_treat, hetero_lift, 0.0)
    activation_prob = _clip_prob(activation_prob, 0.03, 0.92)
    activated = rng.random(len(df)) < activation_prob

    d7_prob = df["acquisition_channel"].map(channel_d7).to_numpy(dtype=float)
    d7_prob += 0.08 * (df["baseline_score"].to_numpy() - 0.5)
    d7_prob -= np.where(weekend.to_numpy(), 0.02, 0.0)
    d7_prob += np.where(exposed_treat, np.where(df["acquisition_channel"].to_numpy() == "paid", 0.015, 0.007), 0.0)
    d7_prob = _clip_prob(d7_prob, 0.02, 0.85)
    retained_d7 = activated & (rng.random(len(df)) < d7_prob)

    d30_prob = df["acquisition_channel"].map(channel_d30).to_numpy(dtype=float)
    d30_prob += 0.06 * (df["baseline_score"].to_numpy() - 0.5)
    d30_prob -= np.where(weekend.to_numpy(), 0.015, 0.0)
    d30_prob += np.where(exposed_treat, np.where(df["acquisition_channel"].to_numpy() == "paid", 0.012, 0.005), 0.0)
    d30_prob = _clip_prob(d30_prob, 0.01, 0.75)
    retained_d30 = activated & (rng.random(len(df)) < d30_prob)

    subscribe_prob = df["acquisition_channel"].map(channel_subscribe).to_numpy(dtype=float)
    subscribe_prob += 0.06 * (df["baseline_score"].to_numpy() - 0.5)
    subscribe_prob = _clip_prob(subscribe_prob, 0.05, 0.9)
    subscribed = activated & (rng.random(len(df)) < subscribe_prob)

    cancellation_prob = np.where(df["acquisition_channel"].to_numpy() == "paid", 0.14, 0.11)
    cancellation_prob += np.where(exposed_treat, 0.002, 0.0)
    cancellation_prob = _clip_prob(cancellation_prob, 0.02, 0.5)
    cancelled = subscribed & (rng.random(len(df)) < cancellation_prob)

    onboarding_delay_minutes = rng.integers(15, 72 * 60, len(df))
    onboarding_completed_ts = pd.to_datetime(df["signup_ts"]) + pd.to_timedelta(onboarding_delay_minutes, unit="m")
    onboarding_completed_ts = pd.Series(onboarding_completed_ts).where(activated)

    match_latency_hours = np.clip(rng.lognormal(mean=2.1, sigma=0.45, size=len(df)), 0.2, 72)
    # Guardrail behavior: treatment should not worsen latency.
    match_latency_hours *= np.where(exposed_treat, 0.96, 1.00)
    matched_ts = onboarding_completed_ts + pd.to_timedelta(match_latency_hours, unit="h")
    matched = activated & (rng.random(len(df)) < 0.985)
    matched_ts = pd.Series(matched_ts).where(matched)

    booking_delay_hours = rng.integers(1, 48, len(df))
    booked_ts = matched_ts + pd.to_timedelta(booking_delay_hours, unit="h")
    booked = activated & matched

    subscribed_delay_hours = rng.integers(1, 96, len(df))
    subscribed_ts = booked_ts + pd.to_timedelta(subscribed_delay_hours, unit="h")
    subscribed_ts = pd.Series(subscribed_ts).where(subscribed)

    cancelled_delay_days = rng.integers(1, 31, len(df))
    cancelled_ts = subscribed_ts + pd.to_timedelta(cancelled_delay_days, unit="D")
    cancelled_ts = pd.Series(cancelled_ts).where(cancelled)

    ticket_lambda = 0.10 + 0.04 * (~activated).astype(float) + 0.03 * (df["acquisition_channel"].to_numpy() == "paid")
    ticket_counts = rng.poisson(ticket_lambda)

    state = pd.DataFrame(
        {
            "user_id": df["user_id"],
            "activated": activated,
            "retained_d7": retained_d7,
            "retained_d30": retained_d30,
            "booked": booked,
            "subscribed": subscribed,
            "cancelled": cancelled,
            "onboarding_completed_ts": onboarding_completed_ts,
            "matched_ts": matched_ts,
            "booked_ts": booked_ts,
            "subscribed_ts": subscribed_ts,
            "cancelled_ts": cancelled_ts,
            "ticket_count": ticket_counts,
        }
    )
    return state


def _build_event_rows(users: pd.DataFrame, state: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    users_idx = users.set_index("user_id")
    state_idx = state.set_index("user_id")

    rows: list[dict] = []
    event_counter = 1

    for user_id, u in users_idx.iterrows():
        signup_ts = np.datetime64(u["signup_ts"].to_datetime64())
        st = state_idx.loc[user_id]

        sid_base = int(user_id) * 1000

        def add_event(
            event_name: str,
            ts: np.datetime64,
            session_id: int | None,
            props: dict,
        ) -> None:
            nonlocal event_counter
            rows.append(
                {
                    "event_id": f"evt_{event_counter}",
                    "user_id": int(user_id),
                    "event_ts": pd.Timestamp(ts),
                    "event_name": event_name,
                    "session_id": session_id,
                    "properties_json": json.dumps(props),
                }
            )
            event_counter += 1

        add_event("signup_completed", signup_ts + np.timedelta64(3, "m"), sid_base + 1, {"source": "signup"})

        started = rng.random() < 0.93
        if started:
            add_event("onboarding_started", signup_ts + np.timedelta64(12, "m"), sid_base + 1, {"step": 1})

        if bool(st["activated"]):
            add_event(
                "onboarding_completed",
                np.datetime64(pd.Timestamp(st["onboarding_completed_ts"]).to_datetime64()),
                sid_base + 2,
                {"step": 4},
            )
            add_event(
                "match_completed",
                np.datetime64(pd.Timestamp(st["matched_ts"]).to_datetime64()),
                sid_base + 2,
                {"match_quality": float(np.round(rng.uniform(0.6, 0.98), 3))},
            )
            add_event(
                "session_booked",
                np.datetime64(pd.Timestamp(st["booked_ts"]).to_datetime64()),
                sid_base + 3,
                {"booking_channel": "in_app"},
            )

        # Baseline engagement + retention opens
        open_count = int(np.clip(rng.poisson(3.0 + 3.2 * u["baseline_score"]), 1, 16))
        for _ in range(open_count):
            hour_offset = int(rng.integers(2, 7 * 24 + 1))
            add_event(
                "app_open",
                signup_ts + np.timedelta64(hour_offset, "h"),
                sid_base + int(rng.integers(10, 300)),
                {"screen": rng.choice(["home", "browse", "chat"])},
            )

        if bool(st["retained_d7"]):
            hour_offset = int(rng.integers(8 * 24, 14 * 24))
            add_event(
                "app_open",
                signup_ts + np.timedelta64(hour_offset, "h"),
                sid_base + int(rng.integers(301, 500)),
                {"screen": "home"},
            )

        if bool(st["retained_d30"]):
            hour_offset = int(rng.integers(30 * 24, 45 * 24))
            add_event(
                "app_open",
                signup_ts + np.timedelta64(hour_offset, "h"),
                sid_base + int(rng.integers(501, 700)),
                {"screen": "home"},
            )

        if bool(st["subscribed"]):
            add_event(
                "subscription_started",
                np.datetime64(pd.Timestamp(st["subscribed_ts"]).to_datetime64()),
                sid_base + 4,
                {"plan": rng.choice(["standard", "plus"], p=[0.7, 0.3])},
            )

        if bool(st["cancelled"]):
            add_event(
                "subscription_cancelled",
                np.datetime64(pd.Timestamp(st["cancelled_ts"]).to_datetime64()),
                sid_base + 5,
                {"reason": rng.choice(["price", "not_helpful", "schedule", "other"], p=[0.36, 0.28, 0.22, 0.14])},
            )

    events = pd.DataFrame(rows)

    # Missingness in instrumentation for important events
    miss_mask = events["event_name"].isin(["onboarding_completed", "session_booked"]) & (rng.random(len(events)) < 0.02)
    events = events.loc[~miss_mask].copy()

    # Missing properties and session ids
    null_props_mask = rng.random(len(events)) < 0.05
    events.loc[null_props_mask, "properties_json"] = "null"
    null_session_mask = rng.random(len(events)) < 0.01
    events.loc[null_session_mask, "session_id"] = np.nan

    # Duplicate rows with distinct event IDs to force dedupe logic downstream
    dup_frac = 0.012
    dup_count = int(len(events) * dup_frac)
    if dup_count > 0:
        dup_rows = events.sample(n=dup_count, random_state=int(rng.integers(0, 1_000_000))).copy()
        dup_rows["event_id"] = [f"dup_evt_{i}" for i in range(1, dup_count + 1)]
        events = pd.concat([events, dup_rows], ignore_index=True)

    events = events.sort_values(["event_ts", "user_id", "event_name"]).reset_index(drop=True)
    events["session_id"] = events["session_id"].astype("Int64")
    return events


def _build_sessions(events: pd.DataFrame, users: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    session_events = events.dropna(subset=["session_id"]).copy()
    if session_events.empty:
        return pd.DataFrame(columns=["session_id", "user_id", "session_start_ts", "session_end_ts", "device"])

    grouped = (
        session_events.groupby(["session_id", "user_id"], as_index=False)
        .agg(session_start_ts=("event_ts", "min"), session_end_ts=("event_ts", "max"))
        .copy()
    )
    grouped["session_start_ts"] = grouped["session_start_ts"] - pd.to_timedelta(rng.integers(1, 8, len(grouped)), unit="m")
    grouped["session_end_ts"] = grouped["session_end_ts"] + pd.to_timedelta(rng.integers(5, 45, len(grouped)), unit="m")

    user_device = users[["user_id", "device"]]
    sessions = grouped.merge(user_device, on="user_id", how="left")
    sessions["session_id"] = sessions["session_id"].astype(np.int64)
    return sessions


def _build_matches(users: pd.DataFrame, state: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    matches = state.loc[state["matched_ts"].notna(), ["user_id", "matched_ts"]].copy()
    matches["therapist_id"] = rng.integers(1000, 3000, len(matches))
    return matches


def _build_subscriptions(users: pd.DataFrame, state: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    subscriptions = state.loc[state["subscribed"], ["user_id", "subscribed_ts"]].copy()
    if subscriptions.empty:
        return pd.DataFrame(columns=["user_id", "subscribed_ts", "plan_type", "price_monthly"])

    plan_type = rng.choice(["standard", "plus"], size=len(subscriptions), p=[0.72, 0.28])
    price = np.where(plan_type == "standard", 79.0, 119.0)

    subscriptions["plan_type"] = plan_type
    subscriptions["price_monthly"] = price
    return subscriptions


def _build_cancellations(state: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    cancellations = state.loc[state["cancelled"], ["user_id", "cancelled_ts"]].copy()
    if cancellations.empty:
        return pd.DataFrame(columns=["user_id", "cancelled_ts", "reason"])

    cancellations["reason"] = rng.choice(
        ["price", "not_helpful", "schedule", "technical", "other"],
        size=len(cancellations),
        p=[0.34, 0.24, 0.18, 0.12, 0.12],
    )
    return cancellations


def _build_support_tickets(users: pd.DataFrame, state: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict] = []
    ticket_id = 1

    user_lookup = users.set_index("user_id")
    for row in state.itertuples(index=False):
        count = int(row.ticket_count)
        if count <= 0:
            continue

        signup_ts = pd.Timestamp(user_lookup.loc[row.user_id, "signup_ts"])
        for _ in range(count):
            created_ts = signup_ts + pd.to_timedelta(int(rng.integers(1, 30 * 24 + 1)), unit="h")
            rows.append(
                {
                    "ticket_id": ticket_id,
                    "user_id": int(row.user_id),
                    "created_ts": created_ts,
                    "category": rng.choice(
                        ["billing", "matching", "app_bug", "account", "other"],
                        p=[0.28, 0.26, 0.22, 0.14, 0.10],
                    ),
                }
            )
            ticket_id += 1

    return pd.DataFrame(rows)


def simulate_data(cfg: SimulationConfig) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(cfg.seed)

    users = _build_user_frame(cfg, rng)
    state = _derive_experiment_outcomes(users, rng)
    events = _build_event_rows(users, state, rng)
    sessions = _build_sessions(events, users, rng)
    matches = _build_matches(users, state, rng)
    subscriptions = _build_subscriptions(users, state, rng)
    cancellations = _build_cancellations(state, rng)
    support_tickets = _build_support_tickets(users, state, rng)

    return {
        "dim_users": users,
        "fact_events": events,
        "fact_sessions": sessions,
        "fact_subscriptions": subscriptions,
        "fact_cancellations": cancellations,
        "fact_support_tickets": support_tickets,
        "fact_matches": matches,
    }


def _safe_overwrite_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic MindLift data")
    parser.add_argument("--n-users", type=int, default=SimulationConfig.n_users)
    parser.add_argument("--seed", type=int, default=SimulationConfig.seed)
    parser.add_argument("--output-dir", type=Path, default=SimulationConfig.output_dir)
    args = parser.parse_args()

    cfg = SimulationConfig(n_users=args.n_users, seed=args.seed, output_dir=args.output_dir)
    logger.info("Generating synthetic data | users=%s seed=%s", cfg.n_users, cfg.seed)

    frames = simulate_data(cfg)
    for table_name, df in frames.items():
        path = cfg.output_dir / f"{table_name}.csv"
        _safe_overwrite_csv(df, path)
        logger.info("Wrote %s (%s rows)", path, len(df))

    logger.info("Synthetic data generation complete")


if __name__ == "__main__":
    main()
