from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logging import get_logger


logger = get_logger(__name__)


def _build_users(n_users: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    signup_start = np.datetime64("2025-01-01")
    signup_offsets = rng.integers(0, 60, n_users)
    signup_seconds = rng.integers(0, 24 * 60 * 60, n_users)

    signup_ts = (
        signup_start
        + signup_offsets.astype("timedelta64[D]")
        + signup_seconds.astype("timedelta64[s]")
    )

    assigned_variant = np.where(rng.random(n_users) < 0.5, "control", "treatment")

    users = pd.DataFrame(
        {
            "user_id": np.arange(1, n_users + 1, dtype=np.int64),
            "signup_ts": pd.to_datetime(signup_ts),
            "country": rng.choice(["US", "CA", "GB", "IN"], size=n_users, p=[0.62, 0.14, 0.14, 0.10]),
            "device": rng.choice(["ios", "android", "web"], size=n_users, p=[0.45, 0.45, 0.10]),
            "acquisition_channel": rng.choice(["organic", "paid", "referral"], size=n_users, p=[0.50, 0.35, 0.15]),
            "age_bucket": rng.choice(["18-24", "25-34", "35-44", "45+"], size=n_users, p=[0.22, 0.38, 0.25, 0.15]),
            "baseline_score": rng.beta(2.2, 2.0, size=n_users).round(6),
            "assigned_variant": assigned_variant,
            "actually_exposed_variant": assigned_variant,
            "pre_treatment_sessions_30d": rng.poisson(1.8, size=n_users),
        }
    )
    return users


def _build_events(users: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)

    n_users = len(users)
    user_ids = users["user_id"].to_numpy()
    signup_ts = users["signup_ts"].to_numpy(dtype="datetime64[s]")
    assigned = users["assigned_variant"].to_numpy()

    p_complete = np.where(assigned == "treatment", 0.64, 0.60)
    p_book = np.where(assigned == "treatment", 0.54, 0.50)

    started = rng.random(n_users) < 0.90
    completed = started & (rng.random(n_users) < p_complete)
    booked = completed & (rng.random(n_users) < p_book)

    # Base per-user event list
    rows: list[dict] = []
    event_counter = 1

    for idx, user_id in enumerate(user_ids):
        base_ts = signup_ts[idx]
        session_base = int(user_id) * 1000

        rows.append(
            {
                "event_id": f"evt_{event_counter}",
                "user_id": int(user_id),
                "event_ts": str(base_ts + np.timedelta64(3, "m")),
                "event_name": "signup_completed",
                "session_id": session_base,
                "properties_json": json.dumps({"source": "signup"}),
            }
        )
        event_counter += 1

        if started[idx]:
            rows.append(
                {
                    "event_id": f"evt_{event_counter}",
                    "user_id": int(user_id),
                    "event_ts": str(base_ts + np.timedelta64(10, "m")),
                    "event_name": "onboarding_started",
                    "session_id": session_base + 1,
                    "properties_json": json.dumps({"step": 1}),
                }
            )
            event_counter += 1

        if completed[idx]:
            rows.append(
                {
                    "event_id": f"evt_{event_counter}",
                    "user_id": int(user_id),
                    "event_ts": str(base_ts + np.timedelta64(45, "m")),
                    "event_name": "onboarding_completed",
                    "session_id": session_base + 1,
                    "properties_json": json.dumps({"step": 4}),
                }
            )
            event_counter += 1

        if booked[idx]:
            rows.append(
                {
                    "event_id": f"evt_{event_counter}",
                    "user_id": int(user_id),
                    "event_ts": str(base_ts + np.timedelta64(90, "m")),
                    "event_name": "session_booked",
                    "session_id": session_base + 2,
                    "properties_json": json.dumps({"booking_channel": "in_app"}),
                }
            )
            event_counter += 1

        n_app_opens = rng.integers(0, 4)
        for _ in range(int(n_app_opens)):
            delay_hours = int(rng.integers(2, 24 * 10))
            rows.append(
                {
                    "event_id": f"evt_{event_counter}",
                    "user_id": int(user_id),
                    "event_ts": str(base_ts + np.timedelta64(delay_hours, "h")),
                    "event_name": "app_open",
                    "session_id": session_base + int(rng.integers(3, 100)),
                    "properties_json": json.dumps({"screen": "home"}),
                }
            )
            event_counter += 1

    events = pd.DataFrame(rows)
    events["event_ts"] = pd.to_datetime(events["event_ts"])
    return events


def _safe_overwrite_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic MindLift data")
    parser.add_argument("--n-users", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    logger.info("Generating synthetic data v1 | users=%s seed=%s", args.n_users, args.seed)

    users = _build_users(n_users=args.n_users, seed=args.seed)
    events = _build_events(users=users, seed=args.seed)

    users_path = args.output_dir / "dim_users.csv"
    events_path = args.output_dir / "fact_events.csv"
    _safe_overwrite_csv(users, users_path)
    _safe_overwrite_csv(events, events_path)

    logger.info("Wrote %s (%s rows)", users_path, len(users))
    logger.info("Wrote %s (%s rows)", events_path, len(events))


if __name__ == "__main__":
    main()
