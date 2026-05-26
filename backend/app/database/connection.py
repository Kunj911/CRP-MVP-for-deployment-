"""
app/database/connection.py

SQLAlchemy engine, session factory, and declarative Base.
Everything database-related flows through here.
"""

from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import get_settings

settings = get_settings()


# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Detect stale connections before using them
    pool_recycle=3600,        # Recycle connections after 1 hour
    pool_size=10,             # Number of connections kept open
    max_overflow=20,          # Extra connections allowed beyond pool_size
    echo=settings.DEBUG,      # Log SQL queries in dev only
)


# ── Session factory ───────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Declarative Base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    All SQLAlchemy models inherit from this Base.
    Import Base in every model file and import all models
    in app/models/__init__.py so Alembic can detect them.
    """
    pass


# ── Dependency ────────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session and ensures it is
    closed after the request, even if an exception is raised.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Health check helper ───────────────────────────────────────────────────────

def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
