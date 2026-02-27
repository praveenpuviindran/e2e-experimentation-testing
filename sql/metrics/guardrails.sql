-- Slice 4: guardrail metrics

CREATE OR REPLACE VIEW vw_guardrails_user_level AS
WITH support AS (
    SELECT
        u.user_id,
        COUNT(*) FILTER (
            WHERE t.created_ts >= u.signup_ts
              AND t.created_ts < u.signup_ts + INTERVAL '30 day'
        ) AS support_tickets_30d
    FROM dim_users u
    LEFT JOIN fact_support_tickets t
        ON u.user_id = t.user_id
    GROUP BY u.user_id
),
cancellation AS (
    SELECT
        u.user_id,
        CASE
            WHEN c.cancelled_ts IS NOT NULL
             AND c.cancelled_ts < u.signup_ts + INTERVAL '30 day'
            THEN 1 ELSE 0
        END AS cancelled_30d
    FROM dim_users u
    LEFT JOIN fact_cancellations c
        ON u.user_id = c.user_id
),
match_latency AS (
    SELECT
        u.user_id,
        EXTRACT(EPOCH FROM (m.matched_ts - u.signup_ts)) / 3600.0 AS time_to_first_match_hours
    FROM dim_users u
    LEFT JOIN fact_matches m
        ON u.user_id = m.user_id
)
SELECT
    u.user_id,
    u.assigned_variant,
    u.actually_exposed_variant,
    u.acquisition_channel,
    COALESCE(c.cancelled_30d, 0) AS cancelled_30d,
    ml.time_to_first_match_hours,
    COALESCE(s.support_tickets_30d, 0) AS support_tickets_30d
FROM dim_users u
LEFT JOIN cancellation c
    ON u.user_id = c.user_id
LEFT JOIN match_latency ml
    ON u.user_id = ml.user_id
LEFT JOIN support s
    ON u.user_id = s.user_id;

CREATE OR REPLACE VIEW vw_guardrail_rates AS
SELECT
    assigned_variant,
    COUNT(*) AS users,
    AVG(cancelled_30d::DOUBLE PRECISION) AS cancellation_rate_30d,
    AVG(time_to_first_match_hours) AS avg_time_to_first_match_hours,
    AVG(support_tickets_30d::DOUBLE PRECISION) AS support_tickets_per_user_30d
FROM vw_guardrails_user_level
GROUP BY assigned_variant;
