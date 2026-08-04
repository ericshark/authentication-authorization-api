export const docsOrder = [
  "quickstart",
  "architecture",
  "authentication",
  "sessions",
  "security",
  "operations",
];

export const docs = {
  quickstart: {
    eyebrow: "Start here",
    title: "Run the complete auth platform locally",
    description:
      "Bring up FastAPI, PostgreSQL, Redis, Celery, and the Next.js documentation console, then create your first authenticated session.",
    readingTime: "7 min",
    sections: [
      {
        id: "what-you-run",
        title: "What you are running",
        body: [
          "Aegis is an authentication reference platform, not a hosted identity provider. You own the API, database, session state, email delivery, and frontend. The repository demonstrates the complete boundary between an untrusted browser and trusted server-side identity code.",
          "FastAPI exposes the authentication routes. PostgreSQL stores durable identity and session records. Redis holds short-lived challenges, rate limits, and activity. Celery sends email outside the request cycle. Next.js is both the documentation site and a real client of the API.",
        ],
        bullets: [
          "FastAPI + Pydantic for HTTP routing and input validation",
          "SQLAlchemy + Alembic for durable identity data",
          "Redis for lockouts, one-time tokens, sessions, and activity",
          "Argon2, Fernet, JWT, and TOTP for cryptographic controls",
          "Next.js for documentation, examples, and the live request workbench",
        ],
      },
      {
        id: "configure",
        title: "1. Configure the backend",
        body: [
          "Copy the backend environment template or edit backend/.env. The authentication strategy is selected at server startup. JWT mode creates a short-lived access cookie and can rotate database-backed refresh tokens. SESSION mode uses an opaque cookie whose server-side state is cached in Redis and persisted in PostgreSQL.",
        ],
        code: {
          label: "backend/.env",
          language: "env",
          content: `DATABASE_URL=postgresql://postgres:postgres@db:5432/auth_api
REDIS_HOST=redis
REDIS_PORT=6379
AUTH_STRATEGY=JWT
REFRESH_TOKENS_ENABLED=true
TOTP=true
CORS_ORIGINS=["http://localhost:3000"]
APP_BASE_URL=http://localhost:8000`,
        },
        note: {
          tone: "warning",
          title: "Protect server secrets",
          text: "SECRET_KEY, TOTP_SECRET, OAuth client secrets, and email provider keys belong only on the server. Never expose them through NEXT_PUBLIC_* variables or browser bundles.",
        },
      },
      {
        id: "start-services",
        title: "2. Start infrastructure and migrate",
        body: [
          "Docker Compose starts the API, worker, PostgreSQL, and Redis on one network. Alembic applies the schema history before the application begins handling identity traffic.",
        ],
        code: {
          label: "Terminal",
          language: "bash",
          content: `cd backend
docker compose up -d db redis
alembic upgrade head
docker compose up api celery`,
        },
        note: {
          tone: "info",
          title: "Why migrations are explicit",
          text: "Authentication data is durable security state. Explicit migrations make schema changes reviewable and reversible instead of silently changing production tables at startup.",
        },
      },
      {
        id: "start-docs",
        title: "3. Start the Next.js client",
        body: [
          "The frontend uses a same-origin rewrite. Browser requests go to /api/backend/* on Next.js and are forwarded to FastAPI. This keeps credentialed requests simple and mirrors a production reverse-proxy deployment.",
        ],
        code: {
          label: "Terminal",
          language: "bash",
          content: `cd frontend
npm install
API_URL=http://localhost:8000 npm run dev`,
        },
      },
      {
        id: "first-session",
        title: "4. Create the first session",
        body: [
          "Registration accepts JSON. Login intentionally accepts form-encoded fields because the route uses FastAPI's OAuth2PasswordRequestForm. Both routes return safe JSON while authentication itself is carried in HTTP-only cookies.",
        ],
        code: {
          label: "Register with curl",
          language: "bash",
          content: `curl -i -c cookies.txt \\
  -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "ada",
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "password": "a-strong-password"
  }'

curl -i -b cookies.txt http://localhost:8000/users/me`,
        },
        note: {
          tone: "success",
          title: "Try it interactively",
          text: "Open the API workbench, select Create account, and inspect the outgoing request, response, and server execution trace together.",
          href: "/playground",
          linkLabel: "Open API workbench",
        },
      },
    ],
  },
  architecture: {
    eyebrow: "Core design",
    title: "Understand the trust boundaries",
    description:
      "Follow one request from an untrusted browser through validation, authentication policy, durable storage, ephemeral state, and the final HTTP-only cookie.",
    readingTime: "9 min",
    sections: [
      {
        id: "system-map",
        title: "System map",
        body: [
          "The browser is never trusted with credential state. It can submit passwords and one-time codes, but it cannot read the authentication cookie after the server sets it. FastAPI is the policy boundary: every protected route resolves the current user before application code runs.",
        ],
        flow: [
          { label: "Next.js client", detail: "Forms, docs, credentialed fetch" },
          { label: "FastAPI boundary", detail: "Routing, Pydantic, dependencies" },
          { label: "Auth backend", detail: "JWT or server session strategy" },
          { label: "PostgreSQL", detail: "Users, providers, tokens, sessions" },
          { label: "Redis", detail: "Challenges, lockouts, cache, activity" },
        ],
      },
      {
        id: "request-lifecycle",
        title: "The protected request lifecycle",
        body: [
          "FastAPI dependencies make authentication composable. A protected route declares get_user_dep. Before the handler receives control, get_current_user selects the configured backend and asks it to authenticate the request.",
        ],
        steps: [
          { title: "1. HTTP request arrives", text: "The browser automatically includes matching HTTP-only cookies because fetch uses credentials: include." },
          { title: "2. FastAPI matches the route", text: "Path, method, query, form, and JSON inputs are parsed before the handler executes." },
          { title: "3. Pydantic validates input", text: "Malformed emails, short passwords, invalid role values, and missing fields fail with structured errors." },
          { title: "4. Authentication dependency runs", text: "JWT mode verifies the signed access token. Session mode resolves the opaque id through Redis and the database." },
          { title: "5. Authorization policy runs", text: "RoleChecker can require user, moderator, or admin privileges independently of authentication." },
          { title: "6. Handler mutates state", text: "SQLAlchemy transactions update durable records; Redis stores short-lived security state." },
          { title: "7. Response sets or clears cookies", text: "The backend controls cookie lifetime, HTTP-only protection, secure transport, and revocation." },
        ],
      },
      {
        id: "backend-interface",
        title: "One interface, two auth strategies",
        body: [
          "JWTBackend and SessionBackend implement the same AuthBackend contract. Routes call registered, authenticate_request, logout, logout_all, and delete_user without knowing how credentials are represented.",
          "This separation keeps policy at the route layer and credential mechanics at the backend layer. Changing AUTH_STRATEGY switches the implementation at startup instead of duplicating every protected route.",
        ],
        table: {
          headers: ["Concern", "JWT strategy", "Session strategy"],
          rows: [
            ["Browser credential", "Signed access token cookie", "Opaque random session id cookie"],
            ["Server lookup", "User by verified JWT subject", "Redis cache, then session row"],
            ["Long-lived access", "Rotating refresh-token row", "Expiring server session row"],
            ["Immediate revocation", "Invalidate refresh tokens", "Invalidate row and delete Redis key"],
            ["Best fit", "Distributed APIs", "Centralized web applications"],
          ],
        },
      },
      {
        id: "data-ownership",
        title: "Durable versus ephemeral state",
        body: [
          "PostgreSQL is the source of truth for identity. Redis accelerates or expires temporary security workflows, but a cache loss must not expose credentials or silently grant access.",
        ],
        bullets: [
          "PostgreSQL: users, password hashes, roles, OAuth links, refresh tokens, sessions",
          "Redis: login failure counters, TOTP login challenges, verification tokens, magic links, reset tokens",
          "Redis: server-session cache and throttled last-active markers",
          "Redis: bounded activity timelines that degrade safely if unavailable",
        ],
      },
    ],
  },
  authentication: {
    eyebrow: "Core concepts",
    title: "Authentication flows, step by step",
    description:
      "See how registration, password login, OAuth, magic links, email verification, and two-factor challenges establish identity.",
    readingTime: "11 min",
    sections: [
      {
        id: "registration",
        title: "Registration",
        body: [
          "POST /auth/register is a JSON endpoint. UserCreate validates the public profile and enforces the minimum password length. The route hashes the password with Argon2 before constructing the SQLAlchemy user model.",
          "A database uniqueness violation becomes a generic HTTP 400, avoiding implementation details. After commit, the configured backend immediately starts an authenticated session and records account.registered in Redis.",
        ],
        code: {
          label: "Request",
          language: "http",
          content: `POST /auth/register HTTP/1.1
Content-Type: application/json

{
  "username": "ada",
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "a-strong-password"
}`,
        },
      },
      {
        id: "password-login",
        title: "Password login",
        body: [
          "POST /auth/login uses form encoding. Before reading the user, the route checks failed:{username} in Redis. Argon2 verifies the password hash, and failures increment the lockout counter while returning the same generic message for a bad username or password.",
          "If TOTP is enabled, password verification is only the first factor. Redis stores a random five-minute challenge and the response contains requires_2fa, temp_token, and user_id. No authenticated cookie exists until /auth/2fa/verify succeeds.",
        ],
        flow: [
          { label: "Form credentials", detail: "username + password" },
          { label: "Redis lockout", detail: "reject excessive failures" },
          { label: "Argon2 verify", detail: "constant-time hash check" },
          { label: "Optional TOTP", detail: "temporary Redis challenge" },
          { label: "Issue cookies", detail: "JWT or session backend" },
        ],
      },
      {
        id: "oauth",
        title: "Google and GitHub OAuth",
        body: [
          "OAuth start routes redirect the browser to the provider. Authlib stores and validates state so an attacker cannot substitute their own callback. The provider callback exchanges the authorization code server-side and retrieves the provider identity.",
          "SocialAccount stores provider plus provider_id and links it to a local user. If no link exists, the callback can match an existing email or create an account. After linking, OAuth uses the same JWT or session backend as password login.",
        ],
        note: {
          tone: "info",
          title: "Provider callbacks are not ordinary API calls",
          text: "The callback requires provider-issued state and an authorization code. The workbench documents these routes but deliberately does not execute them manually.",
        },
      },
      {
        id: "passwordless",
        title: "Magic links and email verification",
        body: [
          "Magic links and email verification use namespaced Redis keys with explicit expirations. The email contains a random token, not a user id. Consuming the token deletes it, making the flow one-time use.",
          "Magic-link requests always return the same response whether an email exists. This prevents account enumeration. Celery sends messages asynchronously so email provider latency does not hold the API request open.",
        ],
        table: {
          headers: ["Flow", "Redis key", "Lifetime", "Result"],
          rows: [
            ["Email verification", "verify:{token}", "1 hour", "Set is_verified"],
            ["Magic link", "magic:{token}", "15 minutes", "Issue auth cookies"],
            ["Password reset", "reset:{token}", "15 minutes", "Store new Argon2 hash"],
            ["2FA login", "2faTempToken:{user_id}", "5 minutes", "Allow second factor"],
          ],
        },
      },
    ],
  },
  sessions: {
    eyebrow: "Core concepts",
    title: "Cookies, sessions, and refresh rotation",
    description:
      "Understand credential transport, access lifetime, token families, device metadata, and revocation across JWT and server-session modes.",
    readingTime: "10 min",
    sections: [
      {
        id: "cookie-boundary",
        title: "The HTTP-only cookie boundary",
        body: [
          "The browser stores authentication cookies but application JavaScript cannot read them. This reduces the value of many cross-site scripting attacks because the credential cannot be copied with document.cookie.",
          "HTTP-only does not replace CSRF controls, secure transport, or output encoding. Production cookies should also use Secure, an intentional SameSite policy, a narrow path, and appropriate domain scope.",
        ],
        bullets: [
          "access_token: short-lived signed JWT in JWT mode",
          "refresh_token: random long-lived credential when refresh is enabled",
          "session_id: random opaque identifier in SESSION mode",
          "OAuth session cookie: temporary Starlette state for provider redirects",
        ],
      },
      {
        id: "jwt-mode",
        title: "JWT access and rotating refresh tokens",
        body: [
          "The access JWT contains a signed user id and expires quickly. Protected requests verify its signature and load the current user, which means account deactivation still takes effect even before token expiry.",
          "Refresh tokens are random values. Only their hashes are stored. On refresh, the current row is invalidated and replaced. Every replacement stays in one family so reuse of an invalidated ancestor can revoke the whole family as a theft response.",
        ],
        flow: [
          { label: "Refresh cookie", detail: "raw random secret" },
          { label: "Hash token", detail: "database-safe lookup" },
          { label: "Validate row", detail: "valid, unexpired, active user" },
          { label: "Invalidate old", detail: "single-use rotation" },
          { label: "Issue new pair", detail: "same token family" },
        ],
        note: {
          tone: "warning",
          title: "Refresh-token reuse is a security signal",
          text: "If an already invalid token appears again, another party may possess a copied token. The backend invalidates the entire family instead of treating it as an ordinary expired request.",
        },
      },
      {
        id: "session-mode",
        title: "Server-side session mode",
        body: [
          "SessionBackend creates a 256-bit random session id, writes the user mapping to Redis with an expiry, and stores a durable UserSession row with IP address, user agent, device name, last activity, and expiration.",
          "Authentication checks Redis first. On a miss, it validates the database row and repopulates state. Last-active writes are throttled with a five-minute Redis marker so routine page loads do not create excessive database writes.",
        ],
      },
      {
        id: "device-control",
        title: "Device visibility and revocation",
        body: [
          "GET /users/me/sessions normalizes refresh-token rows and server-session rows into one safe device response. The frontend does not need separate logic for the configured strategy.",
          "DELETE /users/me/sessions/{id} scopes revocation to the authenticated user. DELETE /users/me/sessions revokes every other device while preserving the session making the request. Logout-all invalidates every device, including the current one.",
        ],
        code: {
          label: "Normalized session response",
          language: "json",
          content: `{
  "id": "opaque-revocation-id",
  "user_id": 42,
  "ip_address": "203.0.113.10",
  "device_name": "Chrome on macOS",
  "current": true,
  "last_active": "2026-08-04T18:30:00Z",
  "expires_at": "2026-09-03T18:30:00Z"
}`,
        },
      },
    ],
  },
  security: {
    eyebrow: "Core concepts",
    title: "Security controls and account recovery",
    description:
      "Learn what each control protects, where its state lives, how one-time recovery works, and which guarantees still depend on deployment configuration.",
    readingTime: "12 min",
    sections: [
      {
        id: "password-storage",
        title: "Password storage with Argon2",
        body: [
          "Passwords are transformed with Argon2 before persistence. Argon2 is intentionally memory- and CPU-intensive, making large offline guessing attacks expensive. Each hash includes its own random salt and cost parameters.",
          "Login verifies the supplied password against the encoded hash. The API never decrypts passwords because there is nothing to decrypt. Password changes and resets always create a new hash.",
        ],
        note: {
          tone: "success",
          title: "What the database contains",
          text: "A compromise exposes salted password hashes, not plaintext passwords. Strong user passwords and appropriately tuned Argon2 costs still matter because hashes can be guessed offline.",
        },
      },
      {
        id: "lockout",
        title: "Online guessing protection",
        body: [
          "Failed login attempts increment a Redis counter keyed by username. Before password verification, the route checks whether the configured threshold has been reached. Successful authentication deletes the counter.",
          "Error responses do not distinguish an unknown username from a wrong password. Administrators can clear the lockout key through a role-protected endpoint after verifying the account owner through an independent channel.",
        ],
      },
      {
        id: "totp",
        title: "Authenticator-app two-factor authentication",
        body: [
          "Setup creates a random TOTP secret and provisioning URI. The secret is encrypted with Fernet before database storage. The user must submit one valid rotating code before totp_enabled becomes true.",
          "Confirmation generates ten recovery codes. Plaintext codes are shown once; only hashes are stored. Using a backup code removes its hash, and rotation invalidates the entire previous set.",
        ],
        steps: [
          { title: "POST /auth/2fa/setup", text: "Create encrypted secret and QR code without enabling the factor." },
          { title: "POST /auth/2fa/confirm", text: "Verify one TOTP window, enable 2FA, and return backup codes once." },
          { title: "POST /auth/2fa/verify", text: "Complete a password login challenge with TOTP or one backup code." },
          { title: "POST /users/me/backup-codes/regenerate", text: "Require a current TOTP code, then replace every recovery code." },
          { title: "POST /auth/2fa/disable", text: "Require a current TOTP code before removing the secret and recovery hashes." },
        ],
      },
      {
        id: "recovery",
        title: "Password reset and recovery",
        body: [
          "Password reset tokens are random, short-lived, namespaced, and one-time use. The request route gives the same response for every email address. This prevents the reset form from becoming a user directory.",
          "A successful reset stores a new Argon2 hash and deletes the Redis token. In a production hardening pass, reset should also revoke every existing refresh token and server session so a previously compromised device cannot remain authenticated.",
        ],
        note: {
          tone: "warning",
          title: "Recommended hardening",
          text: "Treat password reset as an account takeover boundary: revoke all sessions, notify the user, rate-limit by account and IP, and monitor repeated recovery attempts.",
        },
      },
      {
        id: "security-score",
        title: "Transparent account security score",
        body: [
          "The overview endpoint calculates a simple score from explicit controls. It is an educational posture indicator, not a risk engine. Every point maps to an action the account owner can understand and complete.",
        ],
        table: {
          headers: ["Control", "Points", "Why it matters"],
          rows: [
            ["Verified email", "25", "Establishes a tested recovery channel"],
            ["Two-factor authentication", "35", "Stops password-only takeover"],
            ["Password available", "20", "Maintains a direct sign-in credential"],
            ["Three or fewer sessions", "10", "Limits forgotten device exposure"],
            ["OAuth recovery provider", "10", "Adds an alternate identity path"],
          ],
        },
      },
    ],
  },
  operations: {
    eyebrow: "Production guide",
    title: "Operate and extend the platform",
    description:
      "Use health probes, background workers, role policy, observability, tests, and deployment controls to run the reference implementation safely.",
    readingTime: "8 min",
    sections: [
      {
        id: "health",
        title: "Liveness and readiness",
        body: [
          "GET /health/live proves the Python process and router can answer without touching dependencies. Container orchestration can restart the process if this route fails.",
          "GET /health/ready executes SELECT 1 and Redis PING. It returns HTTP 503 with component-level status when the instance should temporarily stop receiving traffic.",
        ],
        code: {
          label: "Readiness response",
          language: "json",
          content: `{
  "status": "ready",
  "components": {
    "database": "ok",
    "redis": "ok"
  },
  "timestamp": "2026-08-04T19:51:45Z"
}`,
        },
      },
      {
        id: "email-workers",
        title: "Email outside the request cycle",
        body: [
          "Verification, magic-link, and password-reset handlers create tokens synchronously but delegate delivery to Celery. The API can respond after the job is accepted instead of waiting on the email provider.",
          "Production operations should monitor queue depth, task failure rates, provider rejection rates, and token request volume. A successful API response means the task was queued, not necessarily delivered.",
        ],
      },
      {
        id: "roles",
        title: "Role-based administration",
        body: [
          "RoleChecker is a dependency that accepts an explicit list of RoleEnum values. Admin routes compose it before executing database queries or Redis mutations. Authentication and authorization remain separate decisions.",
        ],
        bullets: [
          "ADMIN can list users, view aggregate stats, change roles, and clear lockouts",
          "MODERATOR is modeled and can be granted to future staff-only routes",
          "USER is the default role assigned at registration",
          "Role changes are durable database mutations and should be added to a persistent audit log in production",
        ],
      },
      {
        id: "deployment",
        title: "Production deployment checklist",
        body: [
          "The repository demonstrates the identity mechanics, but production security is also an infrastructure discipline. Review every boundary before exposing the API to public traffic.",
        ],
        steps: [
          { title: "Terminate TLS", text: "Use HTTPS everywhere and mark authentication cookies Secure." },
          { title: "Set cookie policy", text: "Choose SameSite, domain, path, and lifetime for your actual frontend/API topology." },
          { title: "Rotate secrets", text: "Use independent high-entropy values for signing, encryption, OAuth, email, and infrastructure credentials." },
          { title: "Restrict CORS", text: "Allow only known production origins and preserve allow_credentials intentionally." },
          { title: "Protect Redis and PostgreSQL", text: "Keep both on private networks with authentication, encryption, backups, and least-privilege users." },
          { title: "Add durable audit logging", text: "Ship security events to append-only storage or a SIEM rather than relying only on bounded Redis activity." },
          { title: "Monitor and alert", text: "Track lockouts, refresh reuse, reset volume, worker failures, 5xx responses, and readiness changes." },
          { title: "Run the test suite", text: "Exercise both JWT and session strategies before each release." },
        ],
      },
      {
        id: "extension-points",
        title: "Where to extend next",
        body: [
          "The backend interface and route dependency design leave clear extension points. Add features at the narrowest layer that owns the policy instead of mixing credential mechanics into every route.",
        ],
        table: {
          headers: ["Feature", "Best extension point"],
          rows: [
            ["Passkeys / WebAuthn", "New credential models and auth routes; keep cookie backend"],
            ["Organizations", "Membership models plus organization-scoped authorization dependency"],
            ["API keys", "Separate hashed credential model and request authentication backend"],
            ["Persistent audit log", "Activity service backed by append-only database or event stream"],
            ["Fine-grained permissions", "Policy dependency layered after get_current_user"],
            ["OIDC provider mode", "Dedicated authorization server library and consent model"],
          ],
        },
      },
    ],
  },
};

export function getAdjacentDocs(slug) {
  const index = docsOrder.indexOf(slug);
  return {
    previous: index > 0 ? { slug: docsOrder[index - 1], ...docs[docsOrder[index - 1]] } : null,
    next:
      index < docsOrder.length - 1
        ? { slug: docsOrder[index + 1], ...docs[docsOrder[index + 1]] }
        : null,
  };
}
