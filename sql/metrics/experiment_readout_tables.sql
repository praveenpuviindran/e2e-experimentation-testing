-- Slice 4: final readout-ready experiment tables

CREATE OR REPLACE VIEW vw_experiment_user_metrics AS
SELECT
    u.user_id,
    u.signup_ts,
    u.country,
    u.device,
    u.acquisition_channel,
    u.age_bucket,
    u.baseline_score,
    u.pre_treatment_sessions_30d,
    u.assigned_variant,
    u.actually_exposed_variant,
    a.activated_within_7d,
    r.retained_d7,
    r.retained_d30,
    g.cancelled_30d,
    g.time_to_first_match_hours,
    g.support_tickets_30d
FROM dim_users u
LEFT JOIN vw_activation_user_level a
    ON u.user_id = a.user_id
LEFT JOIN vw_retention_user_level r
    ON u.user_id = r.user_id
LEFT JOIN vw_guardrails_user_level g
    ON u.user_id = g.user_id;

CREATE OR REPLACE VIEW vw_experiment_variant_summary AS
SELECT
    assigned_variant,
    COUNT(*) AS users,
    AVG(activated_within_7d::DOUBLE PRECISION) AS activation_rate_7d,
    AVG(retained_d7::DOUBLE PRECISION) AS retention_rate_d7,
    AVG(retained_d30::DOUBLE PRECISION) AS retention_rate_d30,
    AVG(cancelled_30d::DOUBLE PRECISION) AS cancellation_rate_30d,
    AVG(time_to_first_match_hours) AS avg_time_to_first_match_hours,
    AVG(support_tickets_30d::DOUBLE PRECISION) AS support_tickets_per_user_30d
FROM vw_experiment_user_metrics
GROUP BY assigned_variant;

CREATE OR REPLACE VIEW vw_experiment_segment_summary AS
SELECT
    assigned_variant,
    acquisition_channel,
    device,
    COUNT(*) AS users,
    AVG(activated_within_7d::DOUBLE PRECISION) AS activation_rate_7d,
    AVG(retained_d30::DOUBLE PRECISION) AS retention_rate_d30,
    AVG(cancelled_30d::DOUBLE PRECISION) AS cancellation_rate_30d
FROM vw_experiment_user_metrics
GROUP BY assigned_variant, acquisition_channel, device;
