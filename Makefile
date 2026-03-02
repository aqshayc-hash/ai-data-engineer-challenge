.PHONY: help install up down logs clean test lint format

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make up            - Start Docker Compose services"
	@echo "  make down          - Stop Docker Compose services"
	@echo "  make logs          - View Docker logs"
	@echo "  make clean         - Remove Docker containers and volumes"
	@echo "  make test          - Run pytest tests"
	@echo "  make lint          - Run code linting (ruff)"
	@echo "  make format        - Format code with black"
	@echo "  make dagster-ui    - Open Dagster UI in browser"

install:
	uv venv
	uv sync

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
	pytest -v tests/

lint:
	ruff check src/ tests/

format:
	black src/ tests/

dagster-ui:
	start http://localhost:3000 || open http://localhost:3000 || echo "Visit http://localhost:3000"
