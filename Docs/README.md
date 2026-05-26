# Live-Trace Backend

> FastAPI · MySQL · SQLAlchemy · JWT  
> B2B Supply Chain Transparency Platform for Agricultural Commodity Exporters

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- MySQL 8.0+
- (Optional) AWS S3 or Cloudinary account for file storage

### 2. Clone and set up environment

```bash
git clone https://github.com/your-org/live-trace-backend.git
cd live-trace-backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Open .env and fill in your values
```

Minimum required for local development:
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=livetrace
DB_USER=root
DB_PASSWORD=your_password
JWT_SECRET_KEY=any-random-string-for-dev
STORAGE_BACKEND=local
```

### 4. Create the database

```sql
CREATE DATABASE livetrace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the server

```bash
# Development (auto-reload)
uvicorn main:app --reload

# Custom port
uvicorn main:app --reload --port 8080
```

Server starts at: `http://localhost:8000`  
API docs (dev only): `http://localhost:8000/docs`  
Health check: `http://localhost:8000/health`

---

## Project Structure

```
live-trace-backend/
├── main.py                     # App entry point
├── requirements.txt
├── .env.example
│
├── config/
│   └── settings.py             # All environment config (Pydantic BaseSettings)
│
└── app/
    ├── api/
    │   ├── deps.py             # Shared FastAPI dependencies
    │   └── v1/                 # All v1 route handlers (thin — no logic)
    │       ├── __init__.py     # Master router
    │       ├── auth.py
    │       ├── orders.py
    │       ├── milestones.py
    │       ├── uploads.py
    │       ├── documents.py
    │       ├── qa.py
    │       ├── notifications.py
    │       └── customers.py
    │
    ├── services/               # All business logic (to be built in phases)
    ├── models/                 # SQLAlchemy ORM models
    ├── schemas/                # Pydantic request/response schemas
    │   └── common.py           # Shared envelopes, pagination
    ├── middleware/
    │   └── logging_middleware.py
    ├── core/
    │   ├── security.py         # JWT + password hashing
    │   ├── permissions.py      # RBAC role/permission maps
    │   ├── exceptions.py       # Custom exception hierarchy
    │   └── events.py           # Startup / shutdown lifecycle
    ├── database/
    │   └── connection.py       # Engine, SessionLocal, Base
    ├── storage/                # File storage abstraction (S3/Cloudinary/local)
    └── utils/
        └── constants.py        # All enums: roles, stages, file types
```

---

## API Overview

All routes are prefixed with `/api/v1`.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/login` | Login | Public |
| POST | `/auth/logout` | Logout | Required |
| POST | `/auth/refresh` | Refresh token | Required |
| GET | `/orders` | List orders | Staff + Customer |
| POST | `/orders` | Create order | Admin |
| GET | `/orders/{id}` | Order detail | Staff + Customer |
| PATCH | `/orders/{id}` | Update order | Admin |
| GET | `/orders/{id}/timeline` | Full timeline | All |
| GET | `/orders/{id}/milestones` | List milestones | All |
| POST | `/orders/{id}/milestones` | Create milestone | Staff |
| PATCH | `/milestones/{id}` | Update milestone | Staff |
| POST | `/upload/photo` | Upload photo | Staff |
| POST | `/upload/document` | Upload document | Admin + Docs |
| GET | `/orders/{id}/qa` | Get QA report | All |
| POST | `/orders/{id}/qa` | Create QA report | Admin + QA |
| GET | `/notifications` | User notifications | All |
| GET | `/customers` | List customers | Admin |

### Standard Response Format

```json
// Success
{ "success": true, "data": { ... }, "message": "..." }

// Paginated
{ "success": true, "data": [ ... ], "meta": { "total": 100, "page": 1, "per_page": 20, "pages": 5 } }

// Error
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Order not found" } }
```

---

## User Roles

| Role | Access Level |
|------|-------------|
| `admin` | Full access |
| `warehouse` | Read orders, upload photos, update milestones |
| `qa` | Read orders, upload QA photos, manage QA reports |
| `docs` | Read orders, upload/manage documents |
| `customer` | Read own orders only, download documents |

---

## Development

### Code style

```bash
black .          # Format
isort .          # Sort imports
flake8 .         # Lint
```

### Database migrations (Alembic)

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "add_orders_table"

# Apply migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

### Storage backends

Set `STORAGE_BACKEND` in `.env`:

| Value | When to use |
|-------|-------------|
| `local` | Local development |
| `s3` | Production (AWS S3) |
| `cloudinary` | Alternative production storage |

---

## Deployment (Render)

1. Create a new **Web Service** on Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env.example`
5. Connect to AWS RDS MySQL instance

Health check path: `/health`

---

## Build Phases

| Phase | What gets built |
|-------|----------------|
| ✅ Phase 1 (now) | App init, config, DB connection, auth skeleton, RBAC, middleware |
| Phase 2 | Order + customer + milestone models, services, full CRUD |
| Phase 3 | Storage abstraction, photo + document upload pipeline |
| Phase 4 | QA reports, notification engine (email + WhatsApp) |
| Phase 5 | Audit logging, image compression, pagination, production deploy |
