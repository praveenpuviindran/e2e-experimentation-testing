# End-to-End Product Experimentation & Metrics Platform (MindLift)

Portfolio-grade analytics engineering + experimentation project for a subscription mental health app scenario.

## Why this project matters
- Demonstrates end-to-end ownership: synthetic data generation, warehouse modeling, SQL metrics layer, statistical experiment analysis, and reporting.
- Mirrors real product analytics workflows with realistic data quality issues and experiment design constraints.
- Reproducible from a fresh clone with script-driven execution.

## Project status
This repository is being built in **Slices 0-10**. Slice 0 establishes environment, repo scaffolding, and PostgreSQL connectivity.

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

## Quickstart (Slice 0)
1. Create environment and install dependencies:
   ```bash
   make setup
   ```
2. Copy env file and update credentials:
   ```bash
   cp .env.example .env
   ```
3. Run DB connection test:
   ```bash
   make test-db
   ```
4. Apply warehouse schema:
   ```bash
   make schema
   ```

## Planned pipeline commands
These are scaffolded now and implemented incrementally through slices:
- `make schema`
- `make generate`
- `make load`
- `make metrics`
- `make analyze`
- `make report`
- `make all`

## Documentation roadmap
- Simulation assumptions: `docs/simulation_spec.md`
- Pre-registration: `docs/preregistration.md` (Slice 6)
- Final experiment readout: `reports/experiment_readout.md` (Slice 9)
