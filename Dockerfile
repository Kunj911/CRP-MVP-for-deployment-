FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libmagic1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements/ ./requirements/
RUN pip install --no-cache-dir --user -r requirements/production.txt

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl libmagic1 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /root/.local
COPY backend/app ./app
COPY backend/templates ./templates
COPY backend/main.py .
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
RUN mkdir -p /app/uploads
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD curl -f http://localhost:${PORT}/health || exit 1
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}