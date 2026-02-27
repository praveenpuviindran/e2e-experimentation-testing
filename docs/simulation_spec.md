# MindLift Synthetic Data Simulation Specification

## Objective
Generate realistic synthetic product analytics data for a subscription mental health app experiment (MindLift), while remaining reproducible on a laptop.

## Slice 2 scope (current)
- Generate `dim_users` and `fact_events` CSV files under `data/raw/`.
- Users are randomized 50/50 into control/treatment.
- Events include signup, onboarding progression, booking, and app opens.
- Treatment has a small uplift on onboarding completion and booking.

## Upcoming Slice 3 realism additions
- Channel-specific base rates (`organic`, `paid`, `referral`)
- Weekday/weekend seasonality
- Missingness and duplicate events
- Noncompliance (assigned treatment but not exposed)
- Heterogeneous treatment effects by segment
- Additional fact tables: sessions, subscriptions, cancellations, support tickets, matches
