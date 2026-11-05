.PHONY: up down logs test-backend test-frontend lint-backend

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test-backend:
	cd backend && pytest -m "not llm"

test-frontend:
	cd frontend && npm run coverage

lint-backend:
	cd backend && ruff check .
