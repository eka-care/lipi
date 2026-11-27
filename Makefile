ENV := --env-file ../.env
RUN := cd server && uv run $(ENV)

.PHONY: dev migrate test lint demo

dev:
	$(RUN) uvicorn lipi.main:app --reload --port 8100

# yoyo talks to Postgres through psycopg, so the URL scheme is rewritten for it.
migrate:
	$(RUN) bash -c 'yoyo apply --batch --database "$${LIPI_DATABASE_URL/postgresql:/postgresql+psycopg:}" lipi/migrations'

test:
	$(RUN) pytest

demo:
	./scripts/demo.sh

lint:
	cd server && uv run ruff check . && uv run ruff format --check .
