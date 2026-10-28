# Mac-friendly shortcuts. Run from the repo root.
PY := .venv/bin/python

.PHONY: setup dev test e2e lint audit docker-build docker-up docker-down

setup:
	python3 -m venv .venv && $(PY) -m pip install -r backend/requirements-dev.txt

dev:
	$(PY) -m uvicorn backend.main:app --reload

test:
	$(PY) -m pytest tests --ignore=tests/e2e

e2e:
	$(PY) -m pytest tests/e2e -m e2e

lint:
	$(PY) -m ruff check backend tests

audit:
	$(PY) -m pip_audit -r backend/requirements.txt

docker-build:
	docker build -t parcelly .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
