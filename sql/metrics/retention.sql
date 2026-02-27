-- Slice 4: retention metrics

CREATE OR REPLACE VIEW vw_retention_user_level AS
WITH opens AS (
    SELECT
        e.user_id,
        MIN(CASE WHEN e.event_name = 'app_open' AND e.event_ts >= u.signup_ts + INTERVAL '7 day' THEN e.event_ts END) AS first_open_after_d7,
        MIN(CASE WHEN e.event_name = 'app_open' AND e.event_ts >= u.signup_ts + INTERVAL '30 day' THEN e.event_ts END) AS first_open_after_d30
    FROM vw_events_deduped e
    JOIN dim_users u
        ON e.user_id = u.user_id
    GROUP BY e.user_id
)
SELECT
    u.user_id,
    u.assigned_variant,
    u.actually_exposed_variant,
    u.acquisition_channel,
    CASE WHEN o.first_open_after_d7 IS NOT NULL THEN 1 ELSE 0 END AS retained_d7,
    CASE WHEN o.first_open_after_d30 IS NOT NULL THEN 1 ELSE 0 END AS retained_d30
FROM dim_users u
LEFT JOIN opens o
    ON u.user_id = o.user_id;

CREATE OR REPLACE VIEW vw_retention_rates AS
SELECT
    assigned_variant,
    COUNT(*) AS users,
    AVG(retained_d7::DOUBLE PRECISION) AS retention_rate_d7,
    AVG(retained_d30::DOUBLE PRECISION) AS retention_rate_d30
FROM vw_retention_user_level
GROUP BY assigned_variant;
