from src.data_gen.generate_data import _build_events, _build_users


def test_generate_users_and_events_shapes() -> None:
    users = _build_users(n_users=500, seed=123)
    events = _build_events(users=users, seed=123)

    assert len(users) == 500
    assert users["user_id"].is_unique
    assert set(users["assigned_variant"].unique()) <= {"control", "treatment"}

    assert len(events) > 500
    assert events["event_id"].is_unique
    assert {"signup_completed", "app_open"}.issubset(set(events["event_name"].unique()))
