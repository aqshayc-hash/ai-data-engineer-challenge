.PHONY: help install up down logs clean test lint format typecheck build

help:
	@echo "Available commands:"
	@echo "  make install       - Install all dependencies with uv (including dev)"
	@echo "  make build         - Build the Docker image"
	@echo "  make up            - Start Docker Compose services (detached)"
	@echo "  make down          - Stop Docker Compose services"
	@echo "  make logs          - Tail Docker Compose logs"
	@echo "  make clean         - Remove Docker containers, volumes, and caches"
	@echo "  make test          - Run pytest with coverage"
	@echo "  make lint          - Lint with ruff"
	@echo "  make format        - Auto-format with black"
	@echo "  make typecheck     - Type-check with mypy"
	@echo "  make dagster-ui    - Open Dagster UI in browser"

install:
	uv venv
	uv sync --dev

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

format:
	uv run black src/ tests/

typecheck:
	uv run mypy src/mama_health/ --ignore-missing-imports

dagster-ui:
	start http://localhost:3000 || open http://localhost:3000 || echo "Visit http://localhost:3000"
