# CRP Railway Deployment Startup Fix Audit & Remediation Report

This report documents the investigation, root cause, and remediation steps taken to fix the Railway startup crash on the B2B Supply Chain Client Relationship Portal (CRP) backend.

---

## 1. Root Cause Analysis

### The Port Parsing Failure
The primary error causing the deployment crash was:
`Error: Invalid value for '--port': '$PORT' is not a valid integer.`

This occurred because the `startCommand` in [railway.json](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/railway.json) was configured as:
`uvicorn main:app --host 0.0.0.0 --port $PORT`

When Railway deploys services using a custom `startCommand` directive inside `railway.json`, its runner executes the command directly without wrapping it in a shell. Because no shell (like `bash` or `sh`) is invoked, environment variables like `$PORT` are not expanded. Uvicorn receives the literal string `"$PORT"` as the argument to `--port`, tries to cast it to an integer, and fails.

### Duplication of Startup Commands
The startup configuration was duplicated and conflicted across three locations:
1. **[railway.json](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/railway.json)**: `deploy.startCommand` overrode other entrypoints.
2. **[Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile)**: `CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}` was defined using the Docker shell form.
3. **[Procfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/Procfile)**: `web: uvicorn main:app --host 0.0.0.0 --port $PORT` acted as a third potential entrypoint.

### Dockerfile Path Validity Issue
The previous [Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile) copied its dependencies using:
`COPY Docs/requirements.txt .`

While this path is valid when the build context is set to the repository root, it introduces two major issues:
1. **Build Context Sensitivity**: If the docker image is built from the `backend/` directory (e.g., `cd backend && docker build .`), the build context is restricted to the subfolder. The `Docs/` directory is outside the context, resulting in a build failure: `stat Docs/requirements.txt: no such file or directory`.
2. **Configuration Drift**: Keeping production package lists inside a `Docs/` folder rather than the code package `backend/requirements/` risks synchronization lag. If developers update packages in `backend/requirements/base.txt` but forget to update `Docs/requirements.txt`, the deployed production app will miss required dependencies, leading to runtime import failures.

---

## 2. Remediation Actions (Changes Applied)

We implemented the **Preferred Fix** to eliminate startup duplication, establish proper shell-expansion for the port, and streamline the Dockerfile configuration.

### A. Removed `startCommand` from [railway.json](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/railway.json)
By removing the `startCommand` property, we delegate startup control back to the [Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile). Docker executes commands defined in `CMD` via shell execution by default, which ensures `${PORT}` is resolved correctly.

### B. Cleaned up [Procfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/Procfile)
We commented out the command in the Procfile to prevent it from interfering with Railway's containerized build process.

### C. Refactored Dependency Copying in [Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile)
We changed the build stage to copy the `backend/requirements/` directory and install dependencies from the canonical `requirements/production.txt` file (which includes `base.txt` internally). This ensures the build relies on code-controlled package sheets rather than documentation directories.

---

## 3. Files Modified

1. **[railway.json](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/railway.json)**
2. **[backend/Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile)**
3. **[Procfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/Procfile)**

---

## 4. Before/After Diffs

### [railway.json](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/railway.json)

```diff
 {
   "$schema": "https://railway.com/railway.schema.json",
   "build": {
     "builder": "DOCKERFILE",
     "dockerfilePath": "backend/Dockerfile"
   },
   "deploy": {
-    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
     "healthcheckPath": "/health",
     "healthcheckTimeout": 30,
     "restartPolicyType": "ON_FAILURE",
     "restartPolicyMaxRetries": 3
   }
 }
```

### [backend/Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile)

```diff
 # Copy dependencies list and compile
 # NOTE: Build context is the REPO ROOT (not backend/)
-COPY Docs/requirements.txt .
-RUN pip install --no-cache-dir --user -r requirements.txt
+COPY backend/requirements ./requirements
+RUN pip install --no-cache-dir --user -r requirements/production.txt
```

### [Procfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/Procfile)

```diff
-web: uvicorn main:app --host 0.0.0.0 --port $PORT
+# Procfile disabled in favor of railway.json and Dockerfile
```

---

## 5. Final Configuration Files

### [railway.json](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/railway.json)

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### [backend/Dockerfile](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/Dockerfile)

```dockerfile
# ── Stage 1: Build dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (libpq-dev for psycopg2, libmagic1 for python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list and compile
# NOTE: Build context is the REPO ROOT (not backend/)
COPY backend/requirements ./requirements
RUN pip install --no-cache-dir --user -r requirements/production.txt

# ── Stage 2: Production image ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (libpq5 for psycopg2, libmagic1 for python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
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
```

---

## 6. Simulation & Validation Results

### Startup and Port Binding Resolution
1. **No Duplicated Overrides**: Removing the `startCommand` from `railway.json` stops Railway from injecting the raw shell-less command.
2. **Container Command Execution**: Docker runs `CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}`. Since this is in shell form, Docker launches `/bin/sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT}"`.
3. **Shell Expansion**: The shell expands `${PORT}` to the runtime port number dynamically assigned by Railway (e.g. `8080`).
4. **Successful Binding**: Uvicorn receives an integer value (e.g. `8080`) instead of the literal `"$PORT"`, resolving the parsing error.

### Health Endpoint Check
* **FastAPI Endpoint**: The endpoint `/health` is verified to be exposed in [main.py](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/main.py#L272-L291) under `_register_routes(app)`.
* **Database & Redis Check**: It uses `check_db_connection()` and `_check_redis_health()`.
* **Healthy Status Validation**: If database or Redis fails to connect, the endpoint degrades to status `"degraded"` or `"unhealthy"` but still returns a `200 OK` JSON body. This prevents the server from returning `500 Internal Server Error` during startup checks, ensuring Railway registers the deploy as healthy and completes the rollout.

---

## 7. Remaining Risks

1. **Database Schema Migrations**: The database schemas must be migrated before or during deployment. While `lifespan` event handler contains logic to run `Base.metadata.create_all` if the `users` table is missing, it is recommended to run migrations via Alembic. Ensure Railway env variables for PostgreSQL are configured correctly.
2. **Redis Dependency**: The lifespan check in [app/core/events.py](file:///c:/Users/Kunj%20Mistry/Desktop/studies/Fittree/Relation%20Portal/Client%20Relationship%20Portal%20(MVP)/backend/app/core/events.py#L133-L138) will fail if `REDIS_REQUIRED` is set to `True` but Redis is unreachable. If Redis is deployed, verify that `REDIS_URL` matches the Railway-assigned Redis service url.
3. **Docker Build Context**: If a developer changes `railway.json` build root settings to `/backend`, the `Dockerfile` COPY paths must be updated (by removing the `backend/` prefix from `COPY backend/app ./app` etc.).
