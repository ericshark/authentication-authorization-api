# AuthCore

A production-grade authentication and authorization API built with FastAPI. Designed as a reusable identity layer — drop it into any project that needs users and auth is solved from day one.

---

## What it does

AuthCore handles the full user lifecycle: registration, login, session management, role-based access control, brute force protection, and account management. Every security decision has an explicit reason behind it.

---

## Tech Stack

- **FastAPI** — async framework, dependency injection, automatic OpenAPI docs
- **PostgreSQL** — primary data store via asyncpg async driver
- **SQLAlchemy 2.0** — async ORM with Alembic migrations
- **Redis** — session storage, account lockout counters
- **PyJWT** — token signing and validation
- **bcrypt via passlib** — password hashing
- **Pytest + HTTPX** — async integration tests with isolated database state per test

---

## Architecture

app/
├── main.py # App entry point, middleware, startup
├── core/
│ ├── config.py # Settings loaded from environment
│ ├── security.py # Hashing, JWT, token utilities
│ ├── redis.py # Async Redis connection factory
│ └── dependencies.py # get_current_user, require_role
├── db/
│ ├── session.py # Async engine and session factory
│ └── base.py # Base model — imported by Alembic and models
├── models/ # SQLAlchemy table definitions
├── schemas/ # Pydantic request and response models
├── crud/ # Database operations, no business logic
├── auth/
│ ├── backends/
│ │ ├── base.py # AuthBackend abstract interface
│ │ ├── jwt_backend.py # Stateless JWT implementation
│ │ └── session_backend.py # Redis-backed session implementation
│ └── cookies.py # set_session_cookie, clear_session_cookie
├── routes/ # FastAPI routers grouped by feature
└── tests/ # Integration tests

Routes never touch the database directly. CRUD never contains business logic. Schemas are the contract between the outside world and the internals. Each layer has one job.

---

## Features

### Pluggable Auth Strategy

JWT and Redis-backed session strategies share a common `AuthBackend` interface. Switch between them with a single environment variable — no route handler changes required.

```bash
AUTH_STRATEGY=jwt      # stateless, scales horizontally
AUTH_STRATEGY=session  # stateful, real logout, Redis-backed
```

### Role-Based Access Control

Roles (admin, user, moderator) enforced at the dependency injection layer. Route handlers contain zero access control logic.

```python
@router.get("/admin/users", dependencies=[Depends(require_role(["admin"]))])
async def list_users():
    ...
```

### JWT with Refresh Tokens

Short-lived access tokens (15 min) paired with long-lived refresh tokens stored as hashed values in Postgres. Explicit revocation on logout compensates for stateless token irrevocability.

### Brute Force Protection

Redis-backed account lockout using atomic INCR/EXPIRE pipelines. Accounts lock for 15 minutes after 5 failed attempts. Lock check runs before any Postgres query.

### User Enumeration Prevention

Identical error responses and timing for wrong password and unknown email. No information leaked about account existence.

### Account Management

Full user lifecycle endpoints — change email, change password, delete account. Email changes invalidate all existing sessions immediately. Account deletion soft-deletes and revokes all tokens.

---

## Endpoints

### Auth

| Method | Route            | Description                                 |
| ------ | ---------------- | ------------------------------------------- |
| POST   | `/auth/register` | Create account                              |
| POST   | `/auth/login`    | Login, returns token or sets cookie         |
| POST   | `/auth/logout`   | Revoke session or refresh token             |
| POST   | `/auth/refresh`  | Exchange refresh token for new access token |

### Account

| Method | Route          | Description                                    |
| ------ | -------------- | ---------------------------------------------- |
| GET    | `/me`          | Current user profile                           |
| PATCH  | `/me/email`    | Change email, invalidates sessions             |
| PATCH  | `/me/password` | Change password, requires current password     |
| DELETE | `/me`          | Delete account, requires password confirmation |

### Admin

| Method | Route                    | Description           |
| ------ | ------------------------ | --------------------- |
| GET    | `/admin/users`           | List all users        |
| PATCH  | `/admin/users/{id}/role` | Change user role      |
| DELETE | `/admin/users/{id}`      | Delete user account   |
| POST   | `/admin/unlock/{email}`  | Clear account lockout |

---

## Running Locally

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis

### Setup

```bash
git clone https://github.com/ericshark/authentication-authorization-api.git
cd authcore

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# fill in your values

alembic upgrade head

uvicorn app.main:app --reload
```

API available at `http://localhost:8000`  
Docs at `http://localhost:8000/docs`

---

## Environment Variables

| Variable                      | Description                                | Example                                             |
| ----------------------------- | ------------------------------------------ | --------------------------------------------------- |
| `DATABASE_URL`                | Async Postgres connection string           | `postgresql+asyncpg://user:pass@localhost/authcore` |
| `REDIS_URL`                   | Redis connection string                    | `redis://localhost:6379`                            |
| `SECRET_KEY`                  | JWT signing key — use a long random string | `openssl rand -hex 32`                              |
| `AUTH_STRATEGY`               | Auth backend to use                        | `jwt` or `session`                                  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime                      | `15`                                                |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | Refresh token lifetime                     | `7`                                                 |
| `MAX_LOGIN_ATTEMPTS`          | Attempts before lockout                    | `5`                                                 |
| `LOCKOUT_DURATION`            | Lockout duration in seconds                | `900`                                               |

---

## Testing

```bash
pytest tests/ -v
```

40+ integration tests with isolated database state per test. Covers registration, login, token validation, protected routes, role enforcement, lockout behavior, refresh token flow, and intentional failure cases.

---

## Design Decisions

**Why identical errors for wrong password and unknown email**  
Different responses let attackers enumerate which emails are registered. Both cases return the same message and take the same processing time.

**Why refresh tokens are stored in Postgres**  
JWTs are stateless — once issued they cannot be revoked before expiry. Storing refresh tokens in the database makes real revocation possible. When a user logs out or changes their password, the refresh token is marked revoked and no new access tokens can be issued.

**Why the auth backend is a swappable interface**  
JWT and session auth make different tradeoffs. JWT scales horizontally without shared state but cannot truly revoke tokens. Sessions are revocable and simpler to reason about but require Redis on every request. Neither is universally better — the right choice depends on the application. Building both behind a shared interface means the decision can change without touching the rest of the codebase.

**Why authorization lives in the dependency layer**  
Putting role checks inside route handlers couples access control to business logic. A composable `require_role()` dependency keeps routes clean and makes access control auditable in one place.

---

## Roadmap

- Refresh token rotation with reuse detection
- Device and session management
- OAuth2 social login (Google, GitHub)
- TOTP two-factor authentication
- Magic link passwordless login
- Audit log
- API key authentication
- Rate limiting per endpoint
- Docker Compose
