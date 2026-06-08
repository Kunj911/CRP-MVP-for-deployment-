# ── Stage 1: Build dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (libmagic1 for python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list and compile
# NOTE: Build context is the REPO ROOT (not backend/)
COPY Docs/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Production image ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (libmagic1 for python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed pip packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code (paths relative to repo root)
COPY backend/app ./app
COPY backend/templates ./templates
COPY backend/main.py .
COPY backend/alembic.ini .
COPY backend/alembic ./alembic

# Create uploads directory (ephemeral on Railway)
RUN mkdir -p /app/uploads

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Railway injects PORT dynamically — default to 8000
ENV PORT=8000
EXPOSE ${PORT}

# Health check for Railway
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start with shell form so ${PORT} is expanded at runtime
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
