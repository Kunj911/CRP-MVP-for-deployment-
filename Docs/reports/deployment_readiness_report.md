# Deployment Readiness Report

## Project Overview
- **Project Name:** Client Relationship Portal (CRP) / Live-Trace
- **Description:** B2B Spice Export Order Tracking Platform
- **Repository:** Client Relationship Portal (MVP)

---

## Frontend Audit

| Property | Value |
|----------|-------|
| Framework | React 18.3 |
| Build Tool | Vite 7 |
| Language | JavaScript (JSX) |
| Styling | Tailwind CSS 3.4 |
| State Management | Zustand 4.5 + TanStack React Query 5 |
| Routing | React Router v6 (lazy loaded) |
| HTTP Client | Axios 1.7 |
| Icons | Lucide React |
| Bundled Size (dist) | ~500KB gzipped |

### Frontend Dependencies
- `react`, `react-dom` ^18.3.1
- `react-router-dom` ^6.23.1
- `axios` ^1.7.2
- `zustand` ^4.5.2
- `@tanstack/react-query` ^5.28.9
- `dayjs` ^1.11.11
- `js-cookie` ^3.0.5
- `lucide-react` ^0.379.0
- `sonner` ^1.4.41

### Frontend Build Process
```bash
npm ci
npm run build  # Outputs to dist/
```

### Frontend Docker Configuration
- Multi-stage Docker build
- Stage 1: Node 20 Alpine - `npm ci` + `npm run build`
- Stage 2: Nginx Alpine - serves `dist/` from `/usr/share/nginx/html`
- Uses `nginx/railway.conf` template with envsubst for `$PORT`
- Frontend Dockerfile expects build context = repo root

---

## Backend Audit

| Property | Value |
|----------|-------|
| Framework | FastAPI 0.111 |
| Python | 3.11 |
| ORM | SQLAlchemy 2.0 |
| Migration | Alembic 1.13 |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt + TOTP MFA |
| Async Tasks | Celery 5.3 (Redis broker) |
| Rate Limiting | slowapi 0.1.9 |
| File Uploads | Pillow, python-magic |

### Backend Dependencies (base.txt)
- `fastapi==0.111.0`, `uvicorn[standard]==0.29.0`
- `sqlalchemy>=2.0.35`, `pymysql>=1.1.1`, `alembic==1.13.1`
- `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`
- `slowapi==0.1.9`, `redis==5.0.3`
- `pydantic>=2.9.2`, `pydantic-settings==2.2.1`
- `celery>=5.3.6`, `sentry-sdk>=2.0.0`
- `boto3==1.34.100`, `cloudinary==1.40.0`

### Backend Startup
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Backend Docker Configuration
- Multi-stage build
- Stage 1: `python:3.11-slim` as builder, installs deps from `Docs/requirements.txt`
- Stage 2: `python:3.11-slim` runtime, copies app code
- Expects build context = repo root
- Uses `$PORT` environment variable (default 8000)

---

## Database Audit

| Property | Value |
|----------|-------|
| Engine | MySQL 8.0 |
| Driver | pymysql |
| Connection Pool | SQLAlchemy (pool_size=10, max_overflow=20) |
| URL Pattern | `mysql+pymysql://user:pass@host:port/db?charset=utf8mb4` |
| Migration Tool | Alembic |
| Migration Location | `backend/alembic/` |
| Schema Auto-init | On startup via `Base.metadata.create_all` |

### Tables (11)
customers, users, orders, milestones, media_files, documents, notifications, order_document_requirements, order_events, audit_logs, login_sessions

---

## Redis Audit

| Property | Value |
|----------|-------|
| Usage | Celery broker, token blacklist, rate limiting, session store, caching |
| Connection | `REDIS_URL` env var |
| Graceful Degradation | Yes (LazyRedis + SafeRedis wrapper) |
| Required | Configurable via `REDIS_REQUIRED` |

---

## Background Workers

| Worker | Command | Queue |
|--------|---------|-------|
| Celery Worker | `celery -A app.core.celery_app.celery_app worker --loglevel=info` | default, notifications, emails, scheduled |
| Celery Beat | `celery -A app.core.celery_app.celery_app beat --loglevel=info` | Scheduled tasks |

---

## Environment Variable Requirements

### Required Variables
| Variable | Source | Current Value |
|----------|--------|---------------|
| APP_ENV | config.py | production |
| DEBUG | config.py | false |
| DB_HOST | config.py | **hardcoded defaults** |
| DB_PORT | config.py | **hardcoded defaults** |
| DB_NAME | config.py | **hardcoded defaults** |
| DB_USER | config.py | **hardcoded defaults** |
| DB_PASSWORD | config.py | **hardcoded defaults** |
| REDIS_URL | config.py | redis://localhost:6379/0 |
| JWT_SECRET_KEY | config.py | **placeholder** |
| MFA_ENCRYPTION_KEY | config.py | **placeholder** |
| ALLOWED_ORIGINS | config.py | localhost defaults |
| SMTP_HOST | config.py | smtp.gmail.com |
| SMTP_PORT | config.py | 587 |
| SMTP_USERNAME | config.py | empty |
| SMTP_PASSWORD | config.py | empty |
| SMTP_FROM_EMAIL | config.py | empty |

### Frontend Variables
| Variable | Source | Current Value |
|----------|--------|---------------|
| VITE_API_BASE_URL | .env.production | http://localhost:8000/api/v1 |

---

## Docker Configuration Issues

### Issue 1: Dockerfile references `Docs/requirements.txt`
- **File:** `backend/Dockerfile` line 14
- **Problem:** References `Docs/requirements.txt` which is a flattened copy of `backend/requirements/base.txt`
- **Status:** File exists, should work with repo-root build context

### Issue 2: Frontend Dockerfile build context
- **File:** `frontend/Dockerfile`
- **Problem:** References `frontend/package*.json` and `frontend/` relative to build context
- **Status:** Requires repo-root as build context

### Issue 3: No production `railway.json` for multi-service
- **Problem:** Current `railway.json` only configures a single backend service
- **Status:** Needs to be replaced with per-service configuration or CLI-based service creation

---

## Railway Configuration Issues

### Issue 1: Single service in railway.json
- Current config only defines backend; no frontend, DB, or Redis
- **Fix:** Use `railway service create` CLI to create multiple services

### Issue 2: Health check path
- `/health` endpoint works, but expects DB + Redis to be up at startup
- Status: Acceptable for production

---

## Security Findings

### Finding 1: Hardcoded credentials in `.env.production`
- File: `.env.production`
- JWT_SECRET_KEY is placeholder: `change-this-primary-secret-key`
- JWT_SECRET_KEYS is placeholder
- DB_PASSWORD is hardcoded

### Finding 2: Weak JWT secret in backend/.env
- JWT_SECRET_KEY visible in `.env` file
- **Risk:** Low (development only)

### Finding 3: CORS origins too permissive in .env.production
- Includes `http://localhost` origins
- **Fix:** Restrict to actual Railway domains in production

### Finding 4: Frontend VITE_API_BASE_URL points to localhost
- File: `frontend/.env.production`
- Points to `http://localhost:8000/api/v1`
- **Fix:** Must be updated to Railway backend URL

### Finding 5: DEBUG not force-disabled
- Config validator force-disables DEBUG in production
- Status: Handled

---

## Deployment Blockers Summary

| Blocker | Severity | Status |
|---------|----------|--------|
| Frontend API URL points to localhost | Critical | **Unfixed** |
| JWT secrets are placeholders | Critical | **Unfixed** |
| CORS origins include localhost | Medium | **Unfixed** |
| No Railway multi-service config | Medium | **Unfixed** |
| Hardcoded DB credentials in .env files | High | **Unfixed** |
| MFA_ENCRYPTION_KEY placeholder | Critical | **Unfixed** |
| No SMTP credentials configured | High | **Unfixed** |

---

## Recommendations

1. Generate strong JWT_SECRET_KEY and MFA_ENCRYPTION_KEY
2. Update frontend VITE_API_BASE_URL to Railway backend domain
3. Restrict CORS origins to Railway frontend domain
4. Remove hardcoded credentials from all .env files
5. Create proper Railway multi-service setup
6. Configure SMTP2GO for email notifications
7. Disable ClamAV in production (or configure properly)
8. Set `REDIS_REQUIRED=True` in production
