PYTHON ?= python

.PHONY: setup test-db schema generate load metrics analyze report all

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && $(PYTHON) -m pip install --upgrade pip
	. .venv/bin/activate && $(PYTHON) -m pip install -r requirements.txt

test-db:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.test_postgres_connection

schema:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.apply_schema

generate:
	. .venv/bin/activate && $(PYTHON) -m src.data_gen.generate_data

load:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.load_to_postgres

metrics:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.build_metrics

analyze:
	. .venv/bin/activate && $(PYTHON) -m src.analysis.run_analysis

report:
	. .venv/bin/activate && $(PYTHON) -m src.analysis.build_report

all: generate load metrics analyze report
