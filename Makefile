PYTHON ?= python

.PHONY: setup test-db schema generate load qa metrics analyze report pipeline all bootstrap s3-upload s3-download dashboard dashboard-data final-deliverable

setup:
	test -d .venv || $(PYTHON) -m venv .venv
	. .venv/bin/activate && $(PYTHON) -m pip install -r requirements.txt

test-db:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.test_postgres_connection

schema:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.apply_schema

generate:
	. .venv/bin/activate && $(PYTHON) -m src.data_gen.generate_data

load:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.load_to_postgres

qa:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.data_quality_checks

metrics:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.build_metrics

analyze:
	. .venv/bin/activate && $(PYTHON) -m src.analysis.run_analysis

report:
	. .venv/bin/activate && $(PYTHON) -m src.analysis.build_report

pipeline: generate load qa metrics analyze report

all: pipeline

bootstrap: setup test-db pipeline

s3-upload:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.s3_sync upload

s3-download:
	. .venv/bin/activate && $(PYTHON) -m src.pipeline.s3_sync download

dashboard:
	. .venv/bin/activate && streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501

dashboard-data:
	. .venv/bin/activate && $(PYTHON) -m src.analysis.build_dashboard_bundle

final-deliverable: setup generate dashboard-data dashboard
