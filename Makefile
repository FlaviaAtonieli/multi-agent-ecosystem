.PHONY: up down logs test-backend lint-backend

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test-backend:
	cd backend && pytest

lint-backend:
	cd backend && ruff check .
