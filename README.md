# MindLift End-to-End Product Experimentation & Metrics Platform

Portfolio-grade analytics engineering and experimentation project that simulates a realistic product A/B test for a subscription mental health app.

## Why this matters
- Demonstrates full-stack product analytics: data generation, warehouse modeling, SQL metrics, statistical experimentation, and reporting.
- Mirrors real analytics constraints: imperfect rollout, noisy events, dedupe, guardrails, power/MDE, CUPED, and multiple-testing correction.
- Reproducible and repo-first: run from a fresh clone via Make targets.

## Experiment story
- Product: `MindLift` (subscription mental health app)
- Test: old onboarding (`control`) vs redesigned onboarding (`treatment`)
- Randomization: 50/50 at signup
- Primary metric (locked): `activated_within_7d`
- Secondary: `retained_d7`, `retained_d30`
- Guardrails: `cancelled_30d`, `time_to_first_match_hours`, `support_tickets_30d`

## Repository structure
```text
experimentation-platform/
  README.md
  Makefile
  requirements.txt
  .env.example
  /src
    /data_gen
    /pipeline
    /analysis
    /utils
  /sql
    /schema
    /metrics
  /data
    /raw
    /processed
  /reports
    /figures
    /tables
  /dashboard
  /tests
  /docs
```

## Quickstart
One-command final deliverable (no Postgres required):
```bash
make final-deliverable
```

`make final-deliverable` runs setup + synthetic data generation + dashboard artifact build + Streamlit launch.

Postgres and `.env` are only needed if you want the optional warehouse pipeline (`make bootstrap`, `make load`, `make metrics`, etc.).

## Standard commands
- `make setup` - create `.venv` and install dependencies
- `make test-db` - validate PostgreSQL connection and ensure target DB exists
- `make schema` - apply SQL DDL
- `make generate` - generate synthetic raw data CSVs
- `make load` - load CSVs into PostgreSQL with upserts
- `make qa` - run post-load data quality checks
- `make metrics` - build SQL metrics views
- `make analyze` - produce A/B tables and figures
- `make report` - generate readout markdown files
- `make pipeline` - generate -> load -> qa -> metrics -> analyze -> report
- `make all` - alias for `make pipeline`
- `make bootstrap` - setup + test-db + full pipeline
- `make s3-upload` - upload `data/raw` files to S3
- `make s3-download` - download raw files from S3 into `data/raw`
- `make dashboard` - launch Streamlit dashboard
- `make dashboard-data` - build dashboard tables/readout from raw CSVs (no Postgres)
- `make final-deliverable` - one-command final app launch (setup + generate + dashboard-data + dashboard)

## Outputs
Generated artifacts:
- Tables: `reports/tables/*.csv`
- Figures: `reports/figures/*.png`
- Readout: `reports/experiment_readout.md`
- Executive summary: `reports/executive_summary.md`

## Streamlit dashboard (Primary Deliverable)
Launch:
```bash
make final-deliverable
```

The app walks through:
- project context and hypothesis
- simulation/data quality checks
- core experiment results (funnel, trend, segment views)
- experiment readout summary
- simulation spec, pre-registration, and resume bullets

## Optional S3 data-lake sync
Set these in `.env` if using S3:
- `S3_BUCKET`
- `S3_PREFIX` (default `mindlift/raw`)
- `AWS_REGION` (optional)

Upload raw files:
```bash
make s3-upload
```

Download raw files:
```bash
make s3-download
```

## PostgreSQL local setup options
- Postgres.app
- Docker example:
```bash
docker run --name mindlift-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mindlift -p 5432:5432 -d postgres:16
```

## Troubleshooting
If you see `FATAL: role "postgres" does not exist`, your local Postgres user is not `postgres`.

Fix `.env` by setting:
```env
PGUSER=<your_local_postgres_user>
PGPASSWORD=<your_password_if_any>
```

On macOS Postgres.app/Homebrew, `PGUSER` is often your mac username.

## Documentation
- Simulation assumptions: `docs/simulation_spec.md`
- Pre-registration plan: `docs/preregistration.md`
- Resume bullets: `docs/resume_bullets.md`
