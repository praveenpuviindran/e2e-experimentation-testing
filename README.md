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
1. Configure environment:
```bash
cp .env.example .env
# edit .env with your local Postgres credentials
```

2. One-command run (fresh clone path):
```bash
make bootstrap
```

This command performs setup + data generation + load + metrics + analysis + report.

## Standard commands
- `make setup` - create `.venv` and install dependencies
- `make test-db` - validate PostgreSQL connection
- `make schema` - apply SQL DDL
- `make generate` - generate synthetic raw data CSVs
- `make load` - load CSVs into PostgreSQL with upserts
- `make metrics` - build SQL metrics views
- `make analyze` - produce A/B tables and figures
- `make report` - generate readout markdown files
- `make qa` - run post-load data quality checks
- `make pipeline` - generate -> load -> qa -> metrics -> analyze -> report
- `make all` - alias for `make pipeline`
- `make bootstrap` - setup + full pipeline

## Outputs
Generated artifacts:
- Tables: `reports/tables/*.csv`
- Figures: `reports/figures/*.png`
- Readout: `reports/experiment_readout.md`
- Executive summary: `reports/executive_summary.md`

## Documentation
- Simulation assumptions: `docs/simulation_spec.md`
- Pre-registration plan: `docs/preregistration.md`
- Resume bullets: `docs/resume_bullets.md`

## PostgreSQL local setup options
- Postgres.app
- Docker example:
```bash
docker run --name mindlift-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mindlift -p 5432:5432 -d postgres:16
```

## Optional AWS extension
You can extend the raw data step by syncing `data/raw/` to S3 (e.g., `s3://<bucket>/mindlift/raw/`) and pulling it before `make load`.
