# This package contains Celery task workers for the Sworn RPG backend
# The main Celery app is defined in celery_app.py
from workers.celery_app import app as celery_app

__all__ = ['celery_app']