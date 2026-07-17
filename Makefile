.PHONY: dev test build clean

dev:
	docker compose up --build

test:
	cd backend && pytest -q
	cd frontend && npm ci && npm run build

build:
	docker compose build

clean:
	docker compose down -v
