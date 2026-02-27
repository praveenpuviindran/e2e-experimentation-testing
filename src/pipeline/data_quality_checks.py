from __future__ import annotations

from sqlalchemy import create_engine, text

from src.utils.config import get_database_url
from src.utils.logging import get_logger


logger = get_logger(__name__)


def _scalar(conn, sql: str) -> float:
    return float(conn.execute(text(sql)).scalar_one())


def main() -> None:
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        user_count = _scalar(conn, "SELECT COUNT(*) FROM dim_users")
        event_count = _scalar(conn, "SELECT COUNT(*) FROM fact_events")

        if user_count < 1000:
            raise SystemExit(f"Data quality check failed: dim_users too small ({user_count})")

        if event_count < user_count * 4:
            raise SystemExit(
                f"Data quality check failed: fact_events unexpectedly low ({event_count} vs users={user_count})"
            )

        null_variant = _scalar(conn, "SELECT COUNT(*) FROM dim_users WHERE assigned_variant IS NULL")
        if null_variant > 0:
            raise SystemExit("Data quality check failed: null assigned_variant values found")

        treatment_share = _scalar(
            conn,
            """
            SELECT AVG(CASE WHEN assigned_variant = 'treatment' THEN 1.0 ELSE 0.0 END)
            FROM dim_users
            """,
        )
        if not (0.40 <= treatment_share <= 0.60):
            raise SystemExit(
                f"Data quality check failed: treatment allocation imbalance ({treatment_share:.4f})"
            )

        activation_rate = _scalar(
            conn,
            """
            WITH event_firsts AS (
                SELECT
                    user_id,
                    MIN(CASE WHEN event_name = 'onboarding_completed' THEN event_ts END) AS onboarding_completed_ts,
                    MIN(CASE WHEN event_name = 'session_booked' THEN event_ts END) AS first_booking_ts
                FROM fact_events
                GROUP BY user_id
            )
            SELECT AVG(
                CASE
                    WHEN ef.onboarding_completed_ts IS NOT NULL
                     AND ef.first_booking_ts IS NOT NULL
                     AND ef.onboarding_completed_ts <= u.signup_ts + INTERVAL '7 day'
                     AND ef.first_booking_ts <= u.signup_ts + INTERVAL '7 day'
                    THEN 1.0 ELSE 0.0
                END
            )
            FROM dim_users u
            LEFT JOIN event_firsts ef
                ON u.user_id = ef.user_id
            """,
        )
        if not (0.05 <= activation_rate <= 0.80):
            raise SystemExit(f"Data quality check failed: activation rate out of expected bounds ({activation_rate:.4f})")

    logger.info("Data quality checks passed")


if __name__ == "__main__":
    main()
