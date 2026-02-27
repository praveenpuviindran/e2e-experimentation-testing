# MindLift Experiment Workflow Project

Live Streamlit dashboard: https://e2e-experimentation-testing.streamlit.app/

This repository is my end-to-end product analytics and experimentation workflow.
I built it to demonstrate how I can move from raw event data to a clear experiment decision with reproducible engineering.

## What This Project Does
I simulate and analyze an onboarding A/B experiment for **MindLift**, a subscription mental health app.

- `control`: original onboarding flow
- `treatment`: redesigned onboarding flow
- randomization: 50/50 at signup
- primary outcome: activation within 7 days
- secondary outcomes: D7 and D30 retention
- guardrails: 30-day cancellation, match latency, support tickets

## Important Data Note (Synthetic Data)
All data in this project is synthetic.

I intentionally generated synthetic product events so this repo can be public, reproducible, and safe (no real patient/user records). The generator includes realistic patterns:
- acquisition-channel differences
- weekday/weekend seasonality
- event duplicates and missing fields
- treatment noncompliance
- heterogeneous treatment effects by segment

## Why Onboarding?
Onboarding is the first high-impact product moment. If it improves, activation and retention can improve. If it degrades UX, guardrails should catch that early. This makes onboarding a practical surface for experimentation.

## One-Command Final Deliverable
Run this from a fresh clone:

```bash
make final-deliverable
```

What it does:
1. Creates/updates `.venv` and installs dependencies
2. Generates synthetic raw data (`data/raw/*.csv`)
3. Builds dashboard data tables/readout (`reports/tables/*.csv`, markdown reports)
4. Launches Streamlit (`http://127.0.0.1:8501`)

## Repository Layout
```text
experimentation-platform/
  README.md
  Makefile
  requirements.txt
  .env.example
  /src
    /data_gen        # synthetic generator + realism knobs
    /pipeline        # schema apply, load, QA, metrics build, S3 sync
    /analysis        # experiment analysis + dashboard bundle build
    /utils           # config + logging helpers
  /sql
    /schema          # DDL
    /metrics         # funnels, retention, guardrails, readout SQL
  /dashboard         # Streamlit final deliverable
  /data
    /raw
    /processed
  /reports
    /figures
    /tables
  /docs
    simulation_spec.md
  /tests
```

## End-to-End Workflow
### 1) Generate realistic raw events (Python)
- module: `src/data_gen/generate_data.py`
- outputs: `dim_users`, `fact_events`, `fact_sessions`, subscriptions, cancellations, support, matches

### 2) Load and model warehouse tables (PostgreSQL + SQL)
- schema: `sql/schema/schema.sql`
- loader: `src/pipeline/load_to_postgres.py`
- supports idempotent upserts and staging-table load pattern

### 3) Build analytics metrics layer (SQL)
- `sql/metrics/funnels.sql`
- `sql/metrics/retention.sql`
- `sql/metrics/guardrails.sql`
- `sql/metrics/experiment_readout_tables.sql`

### 4) Run experiment analysis (Python)
- module: `src/analysis/run_analysis.py`
- includes effect estimation, CIs, CUPED, power/MDE, multiple-metric correction, segment cuts

### 5) Produce project readout + dashboard assets
- report markdown in `reports/`
- dashboard tables in `reports/tables/`
- Streamlit app in `dashboard/app.py`

## Commands
### Core deliverable
- `make final-deliverable`: fastest path to the finished project walkthrough dashboard

### Full warehouse + analysis pipeline
- `make setup`: create `.venv`, install deps
- `make test-db`: test/create target Postgres DB
- `make schema`: apply DDL
- `make generate`: create synthetic raw CSVs
- `make load`: load CSVs into Postgres
- `make qa`: data quality checks
- `make metrics`: create SQL metrics layer
- `make analyze`: run statistical analysis
- `make report`: build markdown outputs
- `make pipeline`: `generate -> load -> qa -> metrics -> analyze -> report`
- `make bootstrap`: `setup -> test-db -> pipeline`

### Optional utilities
- `make s3-upload`: upload raw data to S3
- `make s3-download`: pull raw data from S3
- `make dashboard-data`: rebuild dashboard tables/readout only
- `make dashboard`: run Streamlit app

## Tech Stack and Skillsets Demonstrated
### Languages
- Python 3.10+
- SQL (PostgreSQL dialect)

### Core libraries and frameworks
- Data/compute: `pandas`, `numpy`, `scipy`
- Statistical analysis: `statsmodels`, `scikit-learn`
- Database + loading: `sqlalchemy`, `psycopg2-binary`
- Visualization/reporting: `matplotlib`, `streamlit`
- Config/testing: `python-dotenv`, `pytest`
- Optional cloud sync: `boto3`

### Engineering skills shown in this repo
- analytics SQL modeling (funnel, retention, guardrails)
- experiment design and interpretation (primary metric vs guardrails)
- robust ETL/load patterns (staging + upsert, idempotency)
- statistical workflow automation (CUPED, MDE/power, corrections)
- reproducible project structure (repo-first, Make targets, tests)
- stakeholder communication artifacts (readout + interactive dashboard)

## Outputs
- final dashboard: `dashboard/app.py` (served by Streamlit)
- experiment readout: `reports/experiment_readout.md`
- dashboard walkthrough notes: `reports/dashboard_walkthrough.md`
- tables: `reports/tables/*.csv`
- figures: `reports/figures/*.png`

## Postgres Setup Notes
If you run warehouse commands, set `.env` using your local Postgres user.

If you get:
`FATAL: role "postgres" does not exist`

set:
```env
PGUSER=<your_local_postgres_user>
PGPASSWORD=<password_if_required>
PGHOST=localhost
PGPORT=5432
PGDATABASE=mindlift
```

## Documentation
- simulation assumptions and realism knobs: `docs/simulation_spec.md`
