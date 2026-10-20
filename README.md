# AuthCore

**An open-source authentication and authorization API built with FastAPI.**

Password, OAuth, and magic-link sign-in, TOTP two-factor authentication, swappable
JWT or Redis-backed session auth, refresh-token rotation with reuse detection, and
role-based access control, backed by 135 pytest tests across 29 endpoints.

```
             ┌──────────────────────────────┐
client ────► │ FastAPI  (routes → services) │ ──► PostgreSQL   users, roles, refresh tokens
 (cookies)   │   AuthBackend: JWT | Session │ ──► Redis        sessions, lockout counters, one-time tokens
             └──────────────┬───────────────┘
                            │ enqueue email
                            ▼
                     Celery worker ──► Resend   verification, password reset, magic links
```

## Features

- **Sign-in:** password (Argon2), Google and GitHub OAuth (accounts created or linked
  automatically), and passwordless magic links
- **Two-factor auth:** TOTP setup with a QR code, encrypted secrets, and hashed
  single-use backup codes
- **Swappable auth strategy:** short-lived JWTs or Redis-backed server-side sessions,
  both in HTTP-only cookies, chosen with one environment variable (`AUTH_STRATEGY`)
- **Refresh tokens:** rotated on every use and stored hashed with device metadata;
  token families revoke every descendant when a stolen token is reused
- **Session control:** list active sessions per device, revoke one, or log out everywhere;
  changing a password revokes existing sessions
- **Abuse protection:** Redis-backed login lockout with atomic counters, plus rate limits
  on email verification, password reset, magic links, and 2FA verification
- **Accounts and roles:** registration, profile updates, soft delete, and admin user
  management with `admin`, `moderator`, and `user` roles
- **Async email:** Celery workers send Jinja2-templated emails through Resend

## Design decisions

| Decision | Why |
| --- | --- |
| One `AuthBackend` interface with JWT and session implementations (Strategy pattern) | Routes stay independent of the auth mechanism, and the tradeoff is easy to compare: stateless JWTs scale without a session store but are hard to revoke, while server-side sessions give true logout and logout-all but need Redis. |
| Short-lived access tokens with rotating refresh-token families | A leaked access token expires in 30 minutes, and reuse of a stolen refresh token is detected immediately. |
| Hash every sensitive token at rest | Refresh tokens, reset and magic-link tokens, and backup codes are stored hashed, so a database leak exposes no usable credentials. |
| Redis for lockout counters and one-time tokens | Built-in TTLs fit expiring data, and atomic `INCR` + `EXPIRE` prevents races under concurrent login attempts. |
| Celery for email | Sending outside the request keeps responses fast and lets failed sends retry. |
| Layered routes → services → backends with dependency injection | Each layer can be tested on its own. |

## Stack

**Backend:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, Authlib,
PyOTP, python-jose, Argon2, Jinja2, Resend
**Testing:** pytest, HTTPX
**Infrastructure:** Docker, Docker Compose

## Repository layout

| Path | Contents |
| --- | --- |
| [`backend/`](backend/) | The FastAPI service, Alembic migrations, Celery tasks, email templates, and tests. Its [README](backend/README.md) lists every route and environment variable. |
| [`frontend/`](frontend/) | A Next.js documentation console with an architecture guide and a request playground for every route. See its [README](frontend/README.md). |

## Quick start

Create `backend/.env` with the variables listed in the
[backend README](backend/README.md#environment), then:

```bash
cd backend
docker compose up --build        # API, Celery worker, PostgreSQL, Redis
docker compose exec api alembic upgrade head
```

Interactive API docs: <http://localhost:8000/docs>

## Tests

```bash
cd backend
pytest
```

135 tests cover registration and login, lockout, roles, sessions, refresh tokens,
OAuth, magic links, password reset, email verification, 2FA, and account deletion.

## Status

Built as a learning project to understand production-grade authentication and
running my own infrastructure end to end. It was previously deployed on a
DigitalOcean VPS behind Nginx with DNS, TLS, and Cloudflare, and is no longer hosted.
