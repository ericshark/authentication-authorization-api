import logging
import secrets

import pyotp
from fastapi import APIRouter, HTTPException, Request, Response

from app.auth.lockout import increment_limit, is_limit_reached
from app.auth.tokens import hash_token
from app.auth.totp import (
    create_qr_code,
    decrypt_secret,
    encrypt_secret,
    verify_backup_code,
)
from app.core.dependencies import (
    check_2fa_dep,
    db_dep,
    get_auth_backend,
    get_user_dep,
    redis_dep,
)
from app.models import User
from app.schemas import SecretToken, Verify2fa

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/2fa/setup")
def get_2fa(
    db: db_dep,
    user: get_user_dep,
    _: check_2fa_dep,
):
    secret = pyotp.random_base32()
    user.totp_secret = encrypt_secret(secret)
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=user.email,  # identifies the account in the app
        issuer_name="Auth Api",  # shows as the app name in authenticator
    )

    db.commit()
    qr_base64 = create_qr_code(uri)
    logger.info("2FA setup initiated for user %s", user.id)
    return {
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "secret": secret,  # for manual entry if they can't scan
    }


@router.post("/2fa/confirm")
def confirm_2fa(
    db: db_dep, user: get_user_dep, _: check_2fa_dep, secret_token: SecretToken
):
    secret = decrypt_secret(user.totp_secret)
    totp = pyotp.TOTP(secret)

    if totp.verify(secret_token.secret_token, valid_window=1):
        user.totp_enabled = True
        backup_codes = [
            f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for x in range(10)
        ]
        hashed_codes = [hash_token(backup_codes[x]) for x in range(10)]
        user.backup_codes = hashed_codes
        db.commit()
        logger.info("2FA enabled for user %s", user.id)
        return {"message": "successful 2fa", "backup_codes": backup_codes}
    else:
        logger.warning("2FA confirmation failed (invalid code): user %s", user.id)
        raise HTTPException(status_code=401, detail="Invalid Code")


@router.post("/2fa/verify")
def verify_2fa(
    request: Request,
    response: Response,
    db: db_dep,
    redis: redis_dep,
    user_data: Verify2fa,
    _: check_2fa_dep,
):
    user_id = user_data.user_id
    key = f"2faAttempts:{user_id}"
    is_limit_reached(key, redis)
    stored_secret = redis.get(f"2faTempToken:{user_id}")
    if stored_secret != user_data.temp_token:
        logger.warning("2FA verify with invalid temp token: user %s", user_id)
        increment_limit(key, redis)
        raise HTTPException(status_code=401, detail="Invalid")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        logger.warning("2FA verify for missing/inactive user %s", user_id)
        increment_limit(key, redis)
        raise HTTPException(status_code=401, detail="Invalid")
    valid = False
    used_backup_code = False
    if len(user_data.code) == 6:
        secret = decrypt_secret(user.totp_secret)
        totp = pyotp.TOTP(secret)
        if totp.verify(user_data.code, valid_window=1):
            valid = True
    elif "-" in user_data.code and verify_backup_code(user_data.code, user):
        valid = True
        used_backup_code = True
        db.commit()
    if not valid:
        logger.warning("2FA verify failed (invalid code): user %s", user_id)
        increment_limit(key, redis)
        raise HTTPException(status_code=401, detail="Invalid Code")
    redis.delete(f"2faTempToken:{user_id}")
    logger.info(
        "2FA verification succeeded for user %s (backup_code=%s)",
        user_id,
        used_backup_code,
    )
    return get_auth_backend().registered(db, user, response, redis, request)


@router.post("/2fa/disable")
def disable_2fa(
    db: db_dep, user: get_user_dep, _: check_2fa_dep, secret_token: SecretToken
):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    secret = decrypt_secret(user.totp_secret)
    totp = pyotp.TOTP(secret)
    if not totp.verify(secret_token.secret_token, valid_window=1):
        logger.warning("2FA disable failed (invalid code): user %s", user.id)
        raise HTTPException(status_code=401, detail="Invalid Code")
    user.totp_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    db.commit()
    logger.info("2FA disabled for user %s", user.id)
    return {"message": "2FA disabled"}
