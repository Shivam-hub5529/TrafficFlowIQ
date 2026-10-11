PY ?= python3
export PYTHONPATH := src:backend

.PHONY: all train export test api web docker
all: train export test
train:
	$(PY) scripts/train_queue.py
	$(PY) scripts/train_recon.py
export:
	$(PY) scripts/export_serving.py
test:
	$(PY) -m pytest -q
api:
	cd backend && $(PY) -m uvicorn app.main:app --reload --port 8000
web:
	cd frontend && npm install && npm run dev
docker:
	docker build -t trafficflowiq-api .
