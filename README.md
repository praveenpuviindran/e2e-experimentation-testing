# MindLift Experiment Workflow

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Live Dashboard](https://img.shields.io/badge/live%20app-streamlit-red)](https://e2e-experimentation-testing.streamlit.app/)

Live Streamlit dashboard: https://e2e-experimentation-testing.streamlit.app/

---

## Project Overview

This repository is an end-to-end **product experimentation platform** built around a simulated A/B test for **MindLift**, a subscription mental health app.

The platform covers the full experimentation lifecycle:
1. **Data generation** — realistic synthetic product events (users, sessions, funnel events, subscriptions, support tickets)
2. **Warehouse modeling** — PostgreSQL schema, idempotent ETL, and an analytics metrics layer (funnels, retention, guardrails)
3. **Statistical analysis** — effect estimation, bootstrap confidence intervals, CUPED variance reduction, power/MDE calculations, and Benjamini-Hochberg FDR correction
4. **Decision reporting** — machine-generated experiment readout, segment diagnostics, and a Streamlit dashboard

> **All data is synthetic.** No real patient or user records are included. The generator intentionally injects realistic noise: duplicate events, treatment noncompliance, acquisition-channel heterogeneity, and weekday/weekend seasonality.

### Experiment Design

| Attribute | Value |
|---|---|
| Product | MindLift (subscription mental health app) |
| Test surface | Onboarding flow |
| Variants | `control` (original) vs `treatment` (redesigned) |
| Randomization | 50/50 at signup |
| Primary metric | Activation within 7 days (session booked) |
| Secondary metrics | D7 retention, D30 retention |
| Guardrail metrics | 30-day cancellation rate, match latency, support ticket volume |

---

## Methodology

### Simulation Framework

The data generator (`src/data_gen/generate_data.py`) produces a full user cohort with configurable knobs:

- **n_users** — cohort size (default 75,000 for the live app)
- **seed** — reproducibility seed
- **Treatment effect** — activation lift is baked into the treatment assignment with a heterogeneous signal (channel and age-bucket modifiers)
- **Noncompliance** — a configurable fraction of users are exposed to the opposite variant
- **Noise injection** — duplicate event rows, missing `properties_json`, and realistic channel-specific conversion differences

The generator outputs 7 tables mirroring the PostgreSQL warehouse schema: `dim_users`, `fact_events`, `fact_sessions`, `fact_subscriptions`, `fact_cancellations`, `fact_support_tickets`, `fact_matches`.

### CUPED Variance Reduction

CUPED (Controlled-experiment Using Pre-Experiment Data) reduces the variance of the treatment effect estimate by regressing out a correlated pre-experiment covariate:

```
y_adjusted = y − θ × (x − mean(x))
```

where `θ = Cov(y, x) / Var(x)`. This shrinks the standard error of the estimate without touching the expected value, improving statistical power at fixed sample size. The `pre_treatment_sessions_30d` column in `dim_users` serves as the covariate.

### FDR Correction (Benjamini-Hochberg)

When testing multiple metrics simultaneously (activation, D7 retention, D30 retention, cancellation, match latency, support tickets), the family-wise false-discovery rate inflates. The platform applies the **Benjamini-Hochberg procedure** to adjust p-values:

```
q_i = p_(i) × m / i    (corrected to be monotone, capped at 1.0)
```

where p-values are sorted ascending and m is the total number of tests. This controls the expected proportion of false discoveries at a specified FDR level (default 5%).

---

## PostgreSQL Schema

The warehouse schema is defined in `sql/schema/schema.sql` (idempotent DDL).

| Table | Description |
|---|---|
| `dim_users` | One row per user; holds signup timestamp, acquisition channel, device, age bucket, assigned variant, actually-exposed variant, baseline pre-treatment session count |
| `fact_events` | Raw product events (signup, onboarding_started, onboarding_completed, session_booked, etc.) with JSONB properties |
| `fact_sessions` | Session-level records with start/end timestamps |
| `fact_subscriptions` | Subscription records per user (plan type and price) |
| `fact_cancellations` | Cancellation events with reason; linked to subscriptions |
| `fact_support_tickets` | Support ticket records with category and created timestamp |
| `fact_matches` | Therapist-match records with match timestamp per user |

Key indexes are created on `signup_ts`, `(assigned_variant, actually_exposed_variant)`, and `(user_id, event_ts)` for efficient funnel and retention queries.

---

## Setup: Running the Full Pipeline Locally

### Prerequisites

- Python 3.10+
- PostgreSQL (only required for the full warehouse pipeline; the Streamlit app runs without it)

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Fastest path — run the Streamlit dashboard

```bash
make final-deliverable
```

This single command creates the venv, generates synthetic data, builds all dashboard artifacts, and launches the app at `http://127.0.0.1:8501`.

### Full warehouse pipeline (requires PostgreSQL)

1. Configure your local Postgres credentials in `.env` (copy from `.env.example`):

```env
PGUSER=<your_local_postgres_user>
PGPASSWORD=<password_if_required>
PGHOST=localhost
PGPORT=5432
PGDATABASE=mindlift
```

2. Run the pipeline end-to-end:

```bash
make bootstrap   # setup → test-db → generate → load → qa → metrics → analyze → report
```

Or step by step:

```bash
make setup       # create .venv, install deps
make test-db     # create target Postgres database
make schema      # apply DDL
make generate    # generate synthetic CSVs to data/raw/
make load        # load CSVs into Postgres
make qa          # data quality checks
make metrics     # build SQL metrics layer
make analyze     # run statistical analysis
make report      # produce markdown readout
make dashboard   # launch Streamlit app
```

### Run tests

```bash
pytest tests/
```

---

## Repository Layout

```text
e2e-experimentation-testing/
  README.md
  Makefile
  requirements.txt
  .env.example
  src/
    data_gen/
      generate_data.py        # synthetic data generator with realism knobs
    pipeline/
      apply_schema.py         # apply DDL to Postgres
      load_to_postgres.py     # idempotent upsert loader
      build_metrics.py        # SQL metrics layer builder
      data_quality_checks.py  # QA assertions
      s3_sync.py              # optional S3 upload/download
    analysis/
      run_analysis.py         # orchestrate full statistical analysis
      cuped.py                # CUPED variance reduction
      multiple_testing.py     # Benjamini-Hochberg FDR correction
      stats_utils.py          # bootstrap CI, effect estimation
      power.py                # MDE and required sample size calculations
      build_report.py         # generate experiment readout
      build_dashboard_bundle.py
    utils/
      config.py
      logging.py
  sql/
    schema/schema.sql         # PostgreSQL DDL (idempotent)
    metrics/
      funnels.sql
      retention.sql
      guardrails.sql
      experiment_readout_tables.sql
  dashboard/
    app.py                    # Streamlit final deliverable
  data/
    raw/                      # generated CSVs
    processed/
  reports/
    figures/
    tables/
  docs/
    simulation_spec.md
  tests/
```

---

## Key Outputs

| Artifact | Path |
|---|---|
| Streamlit dashboard | `dashboard/app.py` (served by `make dashboard`) |
| Experiment readout | `reports/experiment_readout.md` |
| Dashboard walkthrough | `reports/dashboard_walkthrough.md` |
| Summary tables | `reports/tables/*.csv` |
| Figures | `reports/figures/*.png` |
| Simulation spec | `docs/simulation_spec.md` |
