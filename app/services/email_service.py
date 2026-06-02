import resend

from app.core.config import settings
from app.services.template_service import render_template

resend.api_key = settings.RESEND_KEY


def send_verification_email(email: str, username: str, token: str) -> None:
    verification_link = f"{settings.APP_BASE_URL}/auth/verify-email?token={token}"
    html = render_template(
        "emails/verify_email.html",
        username=username,
        verification_link=verification_link,
    )
    resend.Emails.send(
        {
            "from": settings.SENDER_EMAIL,
            "to": email,
            "subject": "Verify your email address",
            "html": html,
        }
    )


def send_password_reset_email(email: str, username: str, token: str) -> None:
    reset_link = f"{settings.APP_BASE_URL}/auth/reset-password?token={token}"
    html = render_template(
        "emails/reset_password.html",
        username=username,
        reset_link=reset_link,
    )
    resend.Emails.send(
        {
            "from": settings.SENDER_EMAIL,
            "to": email,
            "subject": "Reset your password",
            "html": html,
        }
    )


def send_magic_link_email(email: str, username: str, token: str) -> None:
    magic_link = f"{settings.APP_BASE_URL}/auth/magic-link/verify?token={token}"
    html = render_template(
        "emails/magic_link.html",
        username=username,
        magic_link=magic_link,
    )
    resend.Emails.send(
        {
            "from": settings.SENDER_EMAIL,
            "to": email,
            "subject": "Your magic login link",
            "html": html,
        }
    )
