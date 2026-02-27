-- Slice 4: funnel and activation metrics

CREATE OR REPLACE VIEW vw_events_deduped AS
WITH ranked AS (
    SELECT
        event_id,
        user_id,
        event_ts,
        event_name,
        session_id,
        properties_json,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, event_name, event_ts
            ORDER BY event_id
        ) AS rn
    FROM fact_events
)
SELECT
    event_id,
    user_id,
    event_ts,
    event_name,
    session_id,
    properties_json
FROM ranked
WHERE rn = 1;

CREATE OR REPLACE VIEW vw_activation_user_level AS
WITH event_firsts AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_name = 'onboarding_started' THEN event_ts END) AS onboarding_started_ts,
        MIN(CASE WHEN event_name = 'onboarding_completed' THEN event_ts END) AS onboarding_completed_ts,
        MIN(CASE WHEN event_name = 'session_booked' THEN event_ts END) AS first_booking_ts
    FROM vw_events_deduped
    GROUP BY user_id
)
SELECT
    u.user_id,
    u.signup_ts,
    u.assigned_variant,
    u.actually_exposed_variant,
    u.acquisition_channel,
    ef.onboarding_started_ts,
    ef.onboarding_completed_ts,
    ef.first_booking_ts,
    CASE
        WHEN ef.onboarding_completed_ts IS NOT NULL
         AND ef.first_booking_ts IS NOT NULL
         AND ef.onboarding_completed_ts <= u.signup_ts + INTERVAL '7 day'
         AND ef.first_booking_ts <= u.signup_ts + INTERVAL '7 day'
        THEN 1 ELSE 0
    END AS activated_within_7d
FROM dim_users u
LEFT JOIN event_firsts ef
    ON u.user_id = ef.user_id;

CREATE OR REPLACE VIEW vw_funnel_step_rates AS
SELECT
    assigned_variant,
    COUNT(*) AS users,
    SUM(CASE WHEN onboarding_started_ts IS NOT NULL THEN 1 ELSE 0 END) AS users_started_onboarding,
    SUM(CASE WHEN onboarding_completed_ts IS NOT NULL THEN 1 ELSE 0 END) AS users_completed_onboarding,
    SUM(CASE WHEN first_booking_ts IS NOT NULL THEN 1 ELSE 0 END) AS users_booked_session,
    AVG(CASE WHEN onboarding_started_ts IS NOT NULL THEN 1.0 ELSE 0.0 END) AS rate_started_onboarding,
    AVG(CASE WHEN onboarding_completed_ts IS NOT NULL THEN 1.0 ELSE 0.0 END) AS rate_completed_onboarding,
    AVG(CASE WHEN first_booking_ts IS NOT NULL THEN 1.0 ELSE 0.0 END) AS rate_booked_session,
    AVG(activated_within_7d::DOUBLE PRECISION) AS activation_rate_7d
FROM vw_activation_user_level
GROUP BY assigned_variant;
