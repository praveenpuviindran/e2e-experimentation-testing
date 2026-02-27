from src.data_gen.generate_data import SimulationConfig, simulate_data


def test_simulation_outputs_and_realism_signals() -> None:
    cfg = SimulationConfig(n_users=2000, seed=123)
    frames = simulate_data(cfg)

    required = {
        "dim_users",
        "fact_events",
        "fact_sessions",
        "fact_subscriptions",
        "fact_cancellations",
        "fact_support_tickets",
        "fact_matches",
    }
    assert set(frames.keys()) == required

    users = frames["dim_users"]
    events = frames["fact_events"]

    assert len(users) == 2000
    assert users["user_id"].is_unique
    assert len(events) > 10000

    # Noncompliance should be visible in assigned vs exposed variants.
    noncompliance_rate = (users["assigned_variant"] != users["actually_exposed_variant"]).mean()
    assert noncompliance_rate > 0.05

    # Duplicate logical events should exist for downstream dedupe logic.
    logical_dups = events.duplicated(subset=["user_id", "event_ts", "event_name"], keep=False).sum()
    assert logical_dups > 0

    # Missingness in event properties should be present.
    missing_props = (events["properties_json"] == "null").sum()
    assert missing_props > 0

    # Channel heterogeneity signal should exist in onboarding conversion rates.
    onboard = events[events["event_name"] == "onboarding_completed"]
    by_channel = (
        users.merge(onboard[["user_id"]].drop_duplicates().assign(onboarded=1), on="user_id", how="left")
        .assign(onboarded=lambda d: d["onboarded"].fillna(0))
        .groupby("acquisition_channel")["onboarded"]
        .mean()
    )
    assert by_channel.max() - by_channel.min() > 0.03
