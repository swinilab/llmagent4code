.PHONY: install dev test test-smoke run docker-up docker-down docker-logs clean help

help:
	@echo "OMS Backend — available targets:"
	@echo "  install     Install dependencies via uv sync"
	@echo "  dev         Run server with auto-reload"
	@echo "  run         Run server in production mode"
	@echo "  test        Run the full test suite"
	@echo "  test-smoke  Run the smoke test"
	@echo "  docker-up   Build and start via Docker Compose"
	@echo "  docker-down Stop Docker containers"
	@echo "  docker-logs Follow Docker logs"
	@echo "  clean       Remove database and cache files"

install:
	uv sync

dev:
	uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --reload

run:
	uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000

test:
	uv run pytest tests/ -v --asyncio-mode=auto

test-smoke:
	uv run python test_smoke.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f oms

clean:
	rm -f oms.db oms.db-wal oms.db-shm test_oms.db test_oms.db-wal test_oms.db-shm
	rm -rf .pytest_cache __pycache__ tests/__pycache__ oms/**/__pycache__