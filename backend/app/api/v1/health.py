from fastapi import APIRouter, Depends
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.connection import check_db_connection, get_db
from app.core.redis_client import redis_client

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check() -> dict[str, Any]:
    """Check connectivity to downstream dependencies (MySQL and Redis)."""
    db_ok = check_db_connection()
    redis_ok = redis_client.ping()
    
    if db_ok and redis_ok:
        status = "healthy"
    else:
        status = "unhealthy"
        
    return {
        "status": status,
        "database": "connected" if db_ok else "unreachable",
        "redis": "connected" if redis_ok else "unreachable"
    }

@router.get("/users-list", tags=["System"])
def list_all_users(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT user_id, email, full_name, role, is_active FROM users ORDER BY user_id")).fetchall()
    return [dict(r._mapping) for r in rows]
