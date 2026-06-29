# AuthCore

FastAPI authentication API with cookie-based JWT or Redis-backed sessions, account management, OAuth login, email workflows, and role-based access control.

## Features

- Swappable auth backend: `AUTH_STRATEGY=JWT` or `AUTH_STRATEGY=SESSION`
- HTTP-only auth cookies with 30-minute access JWTs
- Optional refresh tokens with rotation, hashed storage, device metadata, and reuse-family invalidation
- Redis-backed sessions with real logout, logout-all, session listing, and per-session revocation
- Registration, login, logout, account update, password change, soft delete, and admin user management
- Brute-force login lockout plus rate limits for email verification, password reset, and magic links
- Email verification, password reset, and passwordless magic-link login
- Google and GitHub OAuth account creation/linking
- Role checks for `admin`, `moderator`, and `user`
- TOTP two-factor authentication with encrypted secrets, backup codes, and rate-limited verification
- Celery email jobs, Jinja email templates, and Resend delivery
- Docker Compose for API, Celery, Postgres, and Redis
- 128 pytest cases covering auth flows, login lockout, role-based access, sessions, refresh tokens, OAuth, magic links, password reset, email verification, 2FA, and user deletion

## Stack

FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, Authlib, PyOTP, python-jose, Argon2, Jinja, Resend, Pytest, HTTPX.

## API

### Auth

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Log in with username/password |
| `GET` | `/auth/logout` | Revoke current session/token |
| `GET` | `/auth/logout-all` | Revoke all sessions/tokens |
| `GET` | `/auth/refresh` | Rotate refresh token and issue a new access JWT |
| `GET` | `/auth/verify-user` | Send verification email |
| `GET` | `/auth/verify-email?token=...` | Verify email token |
| `POST` | `/auth/magic-link` | Send passwordless login link |
| `GET` | `/auth/magic-link/verify?token=...` | Log in from magic link |

### Password, OAuth, and 2FA

| Method | Route | Purpose |
| --- | --- | --- |
| `PATCH` | `/auth/password` | Change password and revoke sessions |
| `POST` | `/auth/forgot-password` | Send password reset link |
| `POST` | `/auth/reset-password` | Reset password with token |
| `GET` | `/auth/google` | Start Google OAuth |
| `GET` | `/auth/google/callback` | Google OAuth callback |
| `GET` | `/auth/github` | Start GitHub OAuth |
| `GET` | `/auth/github/callback` | GitHub OAuth callback |
| `POST` | `/auth/2fa/setup` | Generate TOTP secret and QR code |
| `POST` | `/auth/2fa/confirm` | Confirm TOTP code and receive backup codes |
| `POST` | `/auth/2fa/verify` | Verify TOTP or backup code after login |
| `POST` | `/auth/2fa/disable` | Disable 2FA after re-verifying a TOTP code |

### Users and Admin

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/users/me` | Current profile |
| `PATCH` | `/users/update-me` | Update profile fields |
| `DELETE` | `/users/me/delete` | Soft-delete account |
| `GET` | `/users/me/sessions` | List active sessions or refresh tokens |
| `DELETE` | `/users/me/sessions/{id}` | Revoke one session/token |
| `DELETE` | `/users/me/sessions` | Revoke all other sessions/tokens |
| `GET` | `/admin/users` | Admin: list users |
| `PATCH` | `/admin/{u_id}/role` | Admin: change role |
| `POST` | `/admin/unlock/{username}` | Admin: clear login lockout |

## Run Locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
uvicorn app.main:app --reload
```

Docs: `http://localhost:8000/docs`

With containers:

```bash
docker compose up --build
```

## Environment

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database URL |
| `SECRET_KEY` | JWT and session signing secret |
| `AUTH_STRATEGY` | `JWT` or `SESSION` |
| `REFRESH_TOKENS_ENABLED` | Enable JWT refresh-token flow |
| `REDIS_HOST`, `REDIS_PORT` | Redis connection |
| `BROKER_URL` | Celery broker URL |
| `RESEND_KEY`, `SENDER_EMAIL` | Email delivery |
| `APP_BASE_URL` | Base URL used in email links |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_CLIENT_URI` | Google OAuth |
| `GITHUB_CLIENT_ID`, `GITHUB_SECRET`, `GITHUB_CLIENT_URI` | GitHub OAuth |
| `TOTP` | Enable TOTP 2FA routes |
| `TOTP_SECRET` | Fernet key for encrypting TOTP secrets |
| `is_production` | Secure-cookie toggle |

## Test

```bash
pytest
```

