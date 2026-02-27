-- MindLift warehouse schema (Slice 1)
-- Idempotent DDL for local PostgreSQL

CREATE TABLE IF NOT EXISTS dim_users (
    user_id BIGINT PRIMARY KEY,
    signup_ts TIMESTAMP NOT NULL,
    country TEXT NOT NULL,
    device TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL CHECK (acquisition_channel IN ('organic', 'paid', 'referral')),
    age_bucket TEXT NOT NULL,
    baseline_score DOUBLE PRECISION NOT NULL,
    assigned_variant TEXT NOT NULL CHECK (assigned_variant IN ('control', 'treatment')),
    actually_exposed_variant TEXT NOT NULL CHECK (actually_exposed_variant IN ('control', 'treatment')),
    pre_treatment_sessions_30d INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_sessions (
    session_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES dim_users(user_id),
    session_start_ts TIMESTAMP NOT NULL,
    session_end_ts TIMESTAMP,
    device TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_events (
    event_id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES dim_users(user_id),
    event_ts TIMESTAMP NOT NULL,
    event_name TEXT NOT NULL,
    session_id BIGINT,
    properties_json JSONB
);

CREATE TABLE IF NOT EXISTS fact_subscriptions (
    user_id BIGINT PRIMARY KEY REFERENCES dim_users(user_id),
    subscribed_ts TIMESTAMP NOT NULL,
    plan_type TEXT NOT NULL,
    price_monthly NUMERIC(10, 2) NOT NULL CHECK (price_monthly > 0)
);

CREATE TABLE IF NOT EXISTS fact_cancellations (
    user_id BIGINT PRIMARY KEY REFERENCES fact_subscriptions(user_id),
    cancelled_ts TIMESTAMP NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_support_tickets (
    ticket_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES dim_users(user_id),
    created_ts TIMESTAMP NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_matches (
    user_id BIGINT PRIMARY KEY REFERENCES dim_users(user_id),
    matched_ts TIMESTAMP NOT NULL,
    therapist_id BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_users_signup_ts ON dim_users(signup_ts);
CREATE INDEX IF NOT EXISTS idx_dim_users_variant ON dim_users(assigned_variant, actually_exposed_variant);
CREATE INDEX IF NOT EXISTS idx_fact_events_user_ts ON fact_events(user_id, event_ts);
CREATE INDEX IF NOT EXISTS idx_fact_events_name_ts ON fact_events(event_name, event_ts);
CREATE INDEX IF NOT EXISTS idx_fact_sessions_user_start ON fact_sessions(user_id, session_start_ts);
CREATE INDEX IF NOT EXISTS idx_fact_support_tickets_user_ts ON fact_support_tickets(user_id, created_ts);
