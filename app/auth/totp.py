import base64
import io

import qrcode
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.auth.tokens import hash_token
from app.core.config import settings
from app.models import User


def check_enabled_2fa():
    if not settings.TOTP:
        raise HTTPException(status_code=404, detail="Not Found")


def create_qr_code(uri: str):
    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def encrypt_secret(secret: str) -> str:
    key = settings.TOTP_SECRET
    f = Fernet(key.encode())
    return f.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret: str | None) -> str:
    if not encrypted_secret:
        raise HTTPException(status_code=401, detail="2FA setup required")

    key = settings.TOTP_SECRET
    f = Fernet(key.encode())
    try:
        return f.decrypt(encrypted_secret.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=401, detail="Invalid 2FA setup") from exc


def verify_backup_code(input_code: str, user: User):
    hashed_code = hash_token(input_code)
    if hashed_code in user.backup_codes:
        user.backup_codes = [code for code in user.backup_codes if code != hashed_code]
        return True
    return False
