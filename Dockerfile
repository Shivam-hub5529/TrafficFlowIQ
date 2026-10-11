# Build from the REPO ROOT:  docker build -t trafficflowiq-api .
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY src ./src
COPY backend ./backend
COPY models ./models
COPY data/serving ./data/serving
ENV PYTHONPATH=/app/src:/app/backend PORT=8000 ALLOWED_ORIGINS=http://localhost:3000
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
