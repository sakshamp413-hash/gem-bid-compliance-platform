.PHONY: seed server web test build up

seed:            ## regenerate dataset + seed demo
	python data/generate.py
	cd backend && python -m app.seed

server:          ## run backend (SQLite)
	cd backend && uvicorn app.main:app --reload --port 8000

web:             ## run frontend dev server
	cd frontend && npm run dev

test:            ## backend + frontend tests
	cd backend && python -m pytest tests -q
	cd frontend && npm test

up:              ## docker compose (db + backend + frontend)
	docker compose up --build