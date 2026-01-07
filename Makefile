# Stock Analysis Tool - Development Makefile

.PHONY: help setup build up down logs test lint format clean install-deps

# Default target
help:
	@echo "Stock Analysis Tool - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup          - Set up development environment"
	@echo "  install-deps   - Install local development dependencies"
	@echo ""
	@echo "Docker Commands:"
	@echo "  build          - Build Docker images"
	@echo "  up             - Start all services"
	@echo "  down           - Stop all services"
	@echo "  logs           - View service logs"
	@echo "  restart        - Restart all services"
	@echo ""
	@echo "Development Commands:"
	@echo "  test           - Run all tests"
	@echo "  test-backend   - Run backend tests only"
	@echo "  test-frontend  - Run frontend tests only"
	@echo "  lint           - Run linting on all code"
	@echo "  format         - Format all code"
	@echo "  coverage       - Generate test coverage report"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean          - Clean up generated files"
	@echo "  shell-backend  - Open shell in backend container"
	@echo "  shell-frontend - Open shell in frontend container"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	@chmod +x scripts/setup-dev.sh
	@./scripts/setup-dev.sh

# Install local development dependencies
install-deps:
	@echo "Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt -r requirements-test.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Installing pre-commit hooks..."
	@cd backend && pre-commit install

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

# Testing commands
test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	docker-compose exec backend pytest -v

test-frontend:
	@echo "Running frontend tests..."
	docker-compose exec frontend npm test

# Code quality commands
lint:
	@echo "Running backend linting..."
	docker-compose exec backend flake8 app tests
	docker-compose exec backend mypy app
	@echo "Running frontend linting..."
	docker-compose exec frontend npm run lint

format:
	@echo "Formatting backend code..."
	docker-compose exec backend black app tests
	docker-compose exec backend isort app tests
	@echo "Formatting frontend code..."
	docker-compose exec frontend npm run format

# Coverage report
coverage:
	@echo "Generating test coverage report..."
	docker-compose exec backend pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in backend/htmlcov/"

# Utility commands
clean:
	@echo "Cleaning up generated files..."
	@rm -rf backend/htmlcov/
	@rm -rf backend/.coverage
	@rm -rf backend/coverage.xml
	@rm -rf backend/.pytest_cache/
	@rm -rf backend/__pycache__/
	@rm -rf frontend/.next/
	@rm -rf frontend/node_modules/.cache/
	@docker system prune -f

shell-backend:
	docker-compose exec backend /bin/bash

shell-frontend:
	docker-compose exec frontend /bin/sh

# Database commands
db-migrate:
	@echo "Running database migrations..."
	docker-compose exec backend python -m app.database.migrations

db-reset:
	@echo "Resetting database..."
	docker-compose exec backend rm -f /app/data/stock_analysis.db
	docker-compose restart backend

# Production build
build-prod:
	@echo "Building production images..."
	docker-compose -f docker-compose.prod.yml build

# Security scan
security-scan:
	@echo "Running security scan..."
	docker-compose exec backend bandit -r app/ -f json -o bandit-report.json
	docker-compose exec frontend npm audit