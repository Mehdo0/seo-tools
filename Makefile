# SEO Tools — Makefile

PYTHON := python3
APP := backend.main:app

install:
	cd backend && pip install -q -r requirements.txt

run: install
	cd backend && $(PYTHON) -m uvicorn $(APP) --host 0.0.0.0 --port 8000 --reload

test:
	curl -s http://localhost:8000/api/health | python3 -m json.tool

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf backend/*.db

docker-up:
	docker compose -f docker/docker-compose.yml up --build -d

docker-down:
	docker compose -f docker/docker-compose.yml down
