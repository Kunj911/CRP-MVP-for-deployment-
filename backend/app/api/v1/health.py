from fastapi import APIRouter
from typing import Any
from app.database.connection import check_db_connection
from app.core.redis_client import redis_client

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check() -> dict[str, Any]:
    """Check connectivity to downstream dependencies (PostgreSQL and Redis)."""
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
