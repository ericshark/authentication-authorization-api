from app.core.celery_app import celery_app
from app.services.email_service import (
    send_magic_link_email,
    send_password_reset_email,
    send_verification_email,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, email: str, username: str, token: str) -> None:
    try:
        send_verification_email(email, username, token)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_task(self, email: str, username: str, token: str) -> None:
    try:
        send_password_reset_email(email, username, token)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_magic_link_task(self, email: str, username: str, token: str) -> None:
    try:
        send_magic_link_email(email, username, token)
    except Exception as exc:
        raise self.retry(exc=exc)
