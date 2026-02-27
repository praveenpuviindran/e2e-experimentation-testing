# MindLift Synthetic Data Simulation Specification

## Goal
Create realistic synthetic event data for a subscription mental health app A/B test while keeping runtime practical on a laptop.

## Core experiment
- Eligibility: new signups
- Randomization: 50/50 at signup (`assigned_variant`)
- Variants: `control` (old onboarding), `treatment` (redesigned onboarding)
- Exposure: imperfect rollout via `actually_exposed_variant`

## Data volumes (default)
- Users: 75,000
- Events: typically 500k+ (depends on random seed)

## Realism assumptions
1. Acquisition channel effects
- Channels: `organic`, `paid`, `referral`
- Different baseline activation/retention levels per channel.

2. Seasonality
- Signup timestamp spans 120 days.
- Weekend signups have lower activation/retention probabilities.

3. Noncompliance
- ~18% of treatment-assigned users do not see treatment.
- ~2% of control-assigned users are accidentally exposed to treatment.

4. Heterogeneous treatment effects
- Largest activation lift in `paid` channel.
- Smaller positive lifts in `organic` and `referral`.

5. Data quality noise
- Missing instrumentation: small fraction of `onboarding_completed`/`session_booked` events dropped.
- Missing fields: ~5% of events have `properties_json = null`, ~1% missing `session_id`.
- Duplicate logical events: ~1.2% duplicated with different `event_id`.

6. CUPED covariate
- `baseline_score` and `pre_treatment_sessions_30d` included in `dim_users` as pre-treatment predictors.

## Table outputs
Generator writes CSV files in `data/raw/`:
- `dim_users.csv`
- `fact_events.csv`
- `fact_sessions.csv`
- `fact_subscriptions.csv`
- `fact_cancellations.csv`
- `fact_support_tickets.csv`
- `fact_matches.csv`

## Guardrail behavior in simulation
- Match latency in treatment is modeled as neutral-to-slightly better (not worse).
- Support ticket volume and cancellation rates are similar across variants with small random drift.
