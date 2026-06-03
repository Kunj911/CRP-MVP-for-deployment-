"""
app/celery_app.py

Celery worker and beat CLI entrypoint.
Import this via: celery -A app.celery_app worker --loglevel=info
"""

from app.core.celery_app import celery_app

__all__ = ["celery_app"]
