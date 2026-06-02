from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "auth_api",
    broker=settings.BROKER_URL,
    include=["app.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
)

# celery -A app.core.celery_app worker --loglevel=info
