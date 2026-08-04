# Aegis Auth Console

A Next.js 16 documentation frontend for the FastAPI authentication platform. It
explains the architecture, trust boundaries, authentication strategies,
security controls, operations, and every HTTP route alongside the running code.

## Requirements

- Node.js 20.9 or newer
- FastAPI running at `http://localhost:8000`

## Run locally

```sh
npm install
npm run dev
```

Open `http://localhost:3000`.

Next.js proxies `/api/backend/*` to the FastAPI server. Override the backend
target with `API_URL` when needed:

```sh
API_URL=http://localhost:8000 npm run dev
```

## Product surfaces

- `/` — open-source platform overview and guided learning path
- `/docs/*` — quickstart, architecture, authentication, sessions, security, and operations
- `/playground` — searchable request builder and under-the-hood reference for every route
- `/security` — live 2FA, recovery-code, session, and activity demonstration
- `/account` — live profile, password, export, and deactivation demonstration

## Validation

```sh
npm run lint
npm run build
```
