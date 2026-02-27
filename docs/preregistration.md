# MindLift Experiment Pre-Registration (Slice 6)

## Experiment ID
mindlift-onboarding-redesign-2025q1

## Hypothesis
Redesigned onboarding increases 7-day activation without harming cancellations, matching latency, or support burden.

## Unit of randomization
User (new signup), 50/50 assignment at signup.

## Analysis population
1. Primary: Intent-to-Treat (ITT) using `assigned_variant`.
2. Secondary sensitivity: Per-Protocol (PP) using `actually_exposed_variant`.

## Primary metric (locked)
`activated_within_7d`:
User has both `onboarding_completed` and `session_booked` events within 7 days of signup.

## Secondary metrics (locked)
1. `retained_d7`: at least one `app_open` at or after signup + 7 days.
2. `retained_d30`: at least one `app_open` at or after signup + 30 days.

## Guardrails (locked)
1. `cancelled_30d`: cancellation within 30 days of signup.
2. `time_to_first_match_hours`: signup to first therapist match latency.
3. `support_tickets_30d`: support tickets per user in first 30 days.

## Success criteria
1. Primary metric: statistically significant positive ITT lift after multiple-testing adjustment policy (Slice 8).
2. Guardrails: no statistically significant degradation and practical deltas remain within operational tolerance.

## Pre-registered segments (locked)
1. `acquisition_channel` (`organic`, `paid`, `referral`)
2. `device` (`ios`, `android`, `web`)
3. `age_bucket` (`18-24`, `25-34`, `35-44`, `45+`)

## Multiple testing plan
Control FDR with Benjamini-Hochberg across secondary + guardrail families. Primary metric remains primary decision driver.

## Power and MDE plan
Estimate observed MDE using realized sample size and control baseline for the primary metric, with alpha=0.05 and power=0.80.
