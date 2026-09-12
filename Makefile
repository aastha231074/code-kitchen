.PHONY: up down seed logs test

up:
	docker compose up --build -d postgres pubsub pubsub-bootstrap pubsub-relay process-worker ai-api referral-api app-api web

down:
	docker compose down

seed:
	docker compose run --rm ingest-indeed

logs:
	docker compose logs -f

test:
	PYTHONPATH=. python3 -m pytest tests/ -v
