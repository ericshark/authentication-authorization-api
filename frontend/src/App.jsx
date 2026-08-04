import { useMemo, useState } from "react";
import "./styles.css";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

const initialForms = {
  register: {
    username: "demo_user",
    name: "Demo User",
    email: "demo@example.com",
    password: "password123",
  },
  login: {
    username: "demo_user",
    password: "password123",
  },
  verifyEmail: {
    token: "",
  },
  magicLink: {
    email: "demo@example.com",
  },
  magicLinkVerify: {
    token: "",
  },
  updateMe: {
    username: "",
    name: "",
    email: "",
  },
  revokeSession: {
    id: "",
  },
  updatePassword: {
    old_password: "password123",
    new_password: "newpassword123",
  },
  forgotPassword: {
    email: "demo@example.com",
  },
  resetPassword: {
    token: "",
    new_password: "newpassword123",
  },
  twoFaConfirm: {
    secret_token: "",
  },
  twoFaVerify: {
    user_id: "",
    temp_token: "",
    code: "",
  },
  twoFaDisable: {
    secret_token: "",
  },
  adminChangeRole: {
    u_id: "",
    role: "user",
  },
  adminUnlock: {
    username: "",
  },
};

const statusLabels = {
  idle: "Not sent",
  loading: "Sending",
  success: "Success",
  error: "Error",
};

const routes = [
  {
    id: "root",
    group: "System",
    title: "API root",
    method: "GET",
    path: "/",
    submitLabel: "Check API",
    underHood: [
      "The browser sends a simple HTTP GET request to the FastAPI app root.",
      "FastAPI matches the request to `root()` in `app/main.py`.",
      "The route returns `{ status: \"ok\" }`, which proves the API process is reachable.",
    ],
  },
  {
    id: "health",
    group: "System",
    title: "Auth health route",
    method: "GET",
    path: "/auth/health",
    submitLabel: "Check health",
    underHood: [
      "The browser sends an HTTP GET request to the auth router health endpoint.",
      "FastAPI reaches `get_health()`, but that function currently contains only `pass`.",
      "Because the function returns `None`, FastAPI serializes the response body as `null`.",
    ],
  },
  {
    id: "register",
    group: "Auth",
    title: "Register account",
    method: "POST",
    path: "/auth/register",
    submitLabel: "Register",
    fields: [
      { name: "username", label: "Username" },
      { name: "name", label: "Name" },
      { name: "email", label: "Email", type: "email" },
      { name: "password", label: "Password", type: "password" },
    ],
    body: (values) => values,
    afterSuccess: "fetchMe",
    underHood: [
      "The UI sends an HTTP POST request with a JSON body containing username, name, email, and password.",
      "FastAPI validates the body against `UserCreate`, including email format and the minimum password length.",
      "The route hashes the password with Argon2 before anything is stored, then inserts the user through SQLAlchemy.",
      "If the username or email already exists, the database raises an integrity error and the route returns HTTP 400.",
      "On success, the selected auth backend issues an HTTP-only cookie: either a JWT cookie, refresh-token cookie, or Redis-backed session cookie.",
    ],
  },
  {
    id: "login",
    group: "Auth",
    title: "Login",
    method: "POST",
    path: "/auth/login",
    submitLabel: "Login",
    formEncoded: true,
    fields: [
      { name: "username", label: "Username" },
      { name: "password", label: "Password", type: "password" },
    ],
    body: (values) => values,
    afterSuccess: "maybeStore2fa",
    underHood: [
      "The UI sends an HTTP POST request as `application/x-www-form-urlencoded` because FastAPI uses `OAuth2PasswordRequestForm` here.",
      "The route checks Redis for a failed-login lockout key before reading the user from the database.",
      "Argon2 verifies the submitted password against the stored password hash; the raw password is never compared directly.",
      "Failed username or password attempts increment a Redis counter and return a generic HTTP 400 error.",
      "If TOTP is enabled for the user, the route returns a temporary 2FA token instead of logging in fully.",
      "Otherwise, the auth backend creates the HTTP-only auth cookie and the browser stores it for later `credentials: include` requests.",
    ],
  },
  {
    id: "logout",
    group: "Auth",
    title: "Logout current session",
    method: "GET",
    path: "/auth/logout",
    submitLabel: "Logout",
    afterSuccess: "clearMe",
    underHood: [
      "The browser sends a credentialed HTTP GET request, so the current auth cookie is included automatically.",
      "The backend authenticates the current user from the JWT or session cookie before allowing logout.",
      "JWT mode deletes the access cookie and invalidates the current refresh token if refresh tokens are enabled.",
      "Session mode marks the current session invalid in the database and removes the Redis session cache entry.",
    ],
  },
  {
    id: "logoutAll",
    group: "Auth",
    title: "Logout all sessions",
    method: "GET",
    path: "/auth/logout-all",
    submitLabel: "Logout all",
    afterSuccess: "clearMe",
    underHood: [
      "The current auth cookie is sent with the HTTP GET request so the backend can identify the user.",
      "JWT mode invalidates every refresh token row for the user and deletes auth cookies from this browser.",
      "Session mode invalidates every session row for the user and deletes corresponding Redis session keys.",
      "This is stronger than normal logout because it revokes other browsers and devices too.",
    ],
  },
  {
    id: "refresh",
    group: "Auth",
    title: "Refresh JWT",
    method: "GET",
    path: "/auth/refresh",
    submitLabel: "Refresh",
    underHood: [
      "The browser sends the refresh-token cookie in a credentialed HTTP GET request.",
      "The route is available only when the backend is using JWT auth and refresh tokens are enabled.",
      "The raw refresh token is hashed, then matched against a valid database row that has not expired.",
      "The old refresh token is invalidated, a new refresh token is stored, and a new short-lived access JWT cookie is set.",
      "If a reused invalid refresh token is detected, the entire token family is invalidated as a theft-safety measure.",
    ],
  },
  {
    id: "verifyUser",
    group: "Email",
    title: "Send verification email",
    method: "GET",
    path: "/auth/verify-user",
    submitLabel: "Send verification",
    underHood: [
      "The browser sends the current auth cookie so the route can identify the logged-in user.",
      "The route refuses already verified accounts and uses Redis rate limiting to avoid email spam.",
      "A random verification token is stored in Redis for one hour and mapped to the user id.",
      "A Celery task is queued to render and send the verification email outside the request cycle.",
    ],
  },
  {
    id: "verifyEmail",
    group: "Email",
    title: "Verify email token",
    method: "GET",
    path: "/auth/verify-email",
    submitLabel: "Verify token",
    fields: [{ name: "token", label: "Token from email" }],
    query: (values) => ({ token: values.token }),
    underHood: [
      "The UI sends an HTTP GET request with the email token in the query string.",
      "The route looks up `verify:{token}` in Redis to find the user id created by the verification-email route.",
      "If the token is missing or expired, the route returns HTTP 400 instead of changing the database.",
      "A valid token flips `is_verified` to true, deletes the Redis token, and commits the user update.",
    ],
  },
  {
    id: "magicLink",
    group: "Email",
    title: "Request magic link",
    method: "POST",
    path: "/auth/magic-link",
    submitLabel: "Send magic link",
    fields: [{ name: "email", label: "Email", type: "email" }],
    body: (values) => values,
    underHood: [
      "The browser sends an HTTP POST request with a JSON body containing the email address.",
      "The route rate-limits the email address in Redis and then checks whether an active user exists.",
      "If an active account exists, a short-lived token is stored in Redis and an email task is queued.",
      "The response is intentionally generic whether the email exists or not, which avoids account enumeration.",
    ],
  },
  {
    id: "magicLinkVerify",
    group: "Email",
    title: "Verify magic link",
    method: "GET",
    path: "/auth/magic-link/verify",
    submitLabel: "Use magic link",
    fields: [{ name: "token", label: "Token from magic link" }],
    query: (values) => ({ token: values.token }),
    afterSuccess: "fetchMe",
    underHood: [
      "The UI sends the magic-link token as a query parameter over HTTP GET.",
      "The route reads `magic:{token}` from Redis, rejects expired or unknown tokens, and loads the user from the database.",
      "The token is deleted immediately so the link cannot be replayed.",
      "The normal auth backend then issues the same HTTP-only cookie that username/password login would issue.",
    ],
  },
  {
    id: "google",
    group: "OAuth",
    title: "Start Google OAuth",
    method: "GET",
    path: "/auth/google",
    submitLabel: "Open Google OAuth",
    externalNavigation: true,
    underHood: [
      "The UI navigates the browser to the backend route instead of using `fetch`, because OAuth needs full-page redirects.",
      "The backend uses Authlib to build a Google authorization redirect with client id, scope, and callback URI.",
      "Google handles login and consent, then sends the browser back to `/auth/google/callback` with OAuth state and code values.",
    ],
  },
  {
    id: "googleCallback",
    group: "OAuth",
    title: "Google OAuth callback",
    method: "GET",
    path: "/auth/google/callback",
    submitLabel: "Open callback route",
    externalNavigation: true,
    underHood: [
      "This route is normally called by Google after the user completes the OAuth screen.",
      "The backend exchanges the OAuth code for tokens, extracts Google user info, and requires a Google id plus email.",
      "It either finds an existing linked social account, links Google to an existing email user, or creates a new user.",
      "After linking, the normal auth backend issues the HTTP-only auth cookie.",
      "Opening this route manually will usually fail because the OAuth provider did not supply the required state and code.",
    ],
  },
  {
    id: "github",
    group: "OAuth",
    title: "Start GitHub OAuth",
    method: "GET",
    path: "/auth/github",
    submitLabel: "Open GitHub OAuth",
    externalNavigation: true,
    underHood: [
      "The UI navigates to the backend route so GitHub can run its redirect-based OAuth flow.",
      "The backend asks GitHub for `user:email` scope and redirects the browser to GitHub authorization.",
      "GitHub later returns the browser to `/auth/github/callback` with the temporary OAuth code.",
    ],
  },
  {
    id: "githubCallback",
    group: "OAuth",
    title: "GitHub OAuth callback",
    method: "GET",
    path: "/auth/github/callback",
    submitLabel: "Open callback route",
    externalNavigation: true,
    underHood: [
      "This route is normally called by GitHub after authorization, not directly by the React app.",
      "The backend exchanges the temporary OAuth code for an access token and requests the GitHub user profile.",
      "If the profile has no public email, the backend calls GitHub's emails API and selects the primary email.",
      "The social account is found, linked, or created, then the auth backend sets the normal HTTP-only cookie.",
      "Opening this route manually will usually fail because GitHub did not supply the required OAuth callback parameters.",
    ],
  },
  {
    id: "me",
    group: "Users",
    title: "Current profile",
    method: "GET",
    path: "/users/me",
    submitLabel: "Load me",
    afterSuccess: "storeMe",
    underHood: [
      "The browser sends an HTTP GET request with the auth cookie included.",
      "The dependency `get_current_user` validates the JWT or session cookie and loads the user from the database.",
      "The route returns a `UserOut` projection, so sensitive fields like password hash and TOTP secret are not serialized.",
    ],
  },
  {
    id: "updateMe",
    group: "Users",
    title: "Update profile",
    method: "PATCH",
    path: "/users/update-me",
    submitLabel: "Update me",
    fields: [
      { name: "username", label: "New username" },
      { name: "name", label: "New name" },
      { name: "email", label: "New email", type: "email" },
    ],
    body: (values) => omitEmpty(values),
    afterSuccess: "fetchMe",
    underHood: [
      "The UI sends a credentialed HTTP PATCH request with only the fields you filled in.",
      "The backend authenticates the current user before applying any profile change.",
      "Pydantic validates optional username, name, and email fields, then SQLAlchemy updates the matching user row.",
      "If the new username or email collides with another account, the database rejects it and the API returns HTTP 400.",
    ],
  },
  {
    id: "deleteMe",
    group: "Users",
    title: "Soft-delete account",
    method: "DELETE",
    path: "/users/me/delete",
    submitLabel: "Delete my account",
    dangerous: true,
    afterSuccess: "clearMe",
    underHood: [
      "The browser sends a credentialed HTTP DELETE request, so the backend knows which account is being deleted.",
      "The backend does a soft delete by setting `is_active` to false rather than removing the user row.",
      "Active JWT refresh tokens or Redis sessions are invalidated so the account cannot keep using old cookies.",
      "The response deletes auth cookies from this browser after the database transaction commits.",
    ],
  },
  {
    id: "sessions",
    group: "Users",
    title: "List sessions",
    method: "GET",
    path: "/users/me/sessions",
    submitLabel: "Load sessions",
    underHood: [
      "The browser sends an HTTP GET request with the auth cookie included.",
      "JWT mode lists valid, unexpired refresh-token rows; session mode lists valid, unexpired session rows.",
      "The response model exposes device name, IP address, expiration, and user id.",
      "The current response schema does not expose the revocation id, so individual revocation needs a manually supplied id.",
    ],
  },
  {
    id: "revokeSession",
    group: "Users",
    title: "Revoke one session",
    method: "DELETE",
    path: "/users/me/sessions/{id}",
    submitLabel: "Revoke session",
    fields: [{ name: "id", label: "Session id or hashed refresh token" }],
    resolvePath: (values) => `/users/me/sessions/${encodeURIComponent(values.id)}`,
    underHood: [
      "The browser sends a credentialed HTTP DELETE request with the target id in the URL path.",
      "JWT mode treats that id as a hashed refresh token and marks the matching row invalid.",
      "Session mode treats that id as a session id, marks the row invalid, and deletes the Redis cache key.",
      "The backend commits even if no row matched, so check the response and session list after revoking.",
    ],
  },
  {
    id: "revokeOtherSessions",
    group: "Users",
    title: "Revoke other sessions",
    method: "DELETE",
    path: "/users/me/sessions",
    submitLabel: "Revoke other sessions",
    underHood: [
      "The browser sends the current auth cookie with an HTTP DELETE request.",
      "JWT mode reads the current refresh token cookie, hashes it, and invalidates every other valid refresh token for the user.",
      "Session mode reads the current session id cookie and invalidates every other session row and Redis key.",
      "This keeps the current browser logged in while removing access from other devices.",
    ],
  },
  {
    id: "updatePassword",
    group: "Password",
    title: "Change password",
    method: "PATCH",
    path: "/auth/password",
    submitLabel: "Change password",
    fields: [
      { name: "old_password", label: "Old password", type: "password" },
      { name: "new_password", label: "New password", type: "password" },
    ],
    body: (values) => values,
    afterSuccess: "clearMe",
    underHood: [
      "The UI sends a credentialed HTTP PATCH request with old and new passwords in a JSON body.",
      "The backend authenticates the current cookie and verifies the old password with Argon2.",
      "If the old password is wrong, the route returns HTTP 400 and does not change the stored hash.",
      "A valid new password is hashed, saved, and then all sessions/tokens are revoked to force fresh login everywhere.",
    ],
  },
  {
    id: "forgotPassword",
    group: "Password",
    title: "Request password reset",
    method: "POST",
    path: "/auth/forgot-password",
    submitLabel: "Send reset link",
    fields: [{ name: "email", label: "Email", type: "email" }],
    body: (values) => values,
    underHood: [
      "The browser sends an HTTP POST request with a JSON body containing the email address.",
      "If an active user exists, the route rate-limits the email in Redis and stores a reset token for 15 minutes.",
      "A Celery email job is queued with the reset token link.",
      "The response stays generic whether the account exists or not, which prevents email enumeration.",
    ],
  },
  {
    id: "resetPassword",
    group: "Password",
    title: "Reset password",
    method: "POST",
    path: "/auth/reset-password",
    submitLabel: "Reset password",
    fields: [
      { name: "token", label: "Reset token" },
      { name: "new_password", label: "New password", type: "password" },
    ],
    body: (values) => values,
    underHood: [
      "The UI sends an HTTP POST request with the reset token and new password in JSON.",
      "The backend looks up `reset:{token}` in Redis and rejects expired or unknown tokens.",
      "A valid token identifies the user, the new password is hashed, and the Redis reset token is deleted.",
      "This route does not require the user to be logged in because the reset token is the proof.",
    ],
  },
  {
    id: "twoFaSetup",
    group: "2FA",
    title: "Set up 2FA",
    method: "POST",
    path: "/auth/2fa/setup",
    submitLabel: "Generate QR",
    underHood: [
      "The browser sends a credentialed HTTP POST request; only the logged-in user can set up 2FA.",
      "The backend generates a random TOTP secret and encrypts it before saving it on the user row.",
      "A provisioning URI is generated for authenticator apps, then converted into a base64 PNG QR code.",
      "The response includes both QR code and manual-entry secret so the UI can show either setup path.",
    ],
  },
  {
    id: "twoFaConfirm",
    group: "2FA",
    title: "Confirm 2FA",
    method: "POST",
    path: "/auth/2fa/confirm",
    submitLabel: "Confirm code",
    fields: [{ name: "secret_token", label: "6-digit authenticator code" }],
    body: (values) => values,
    underHood: [
      "The UI sends the six-digit authenticator code in a credentialed HTTP POST request.",
      "The backend decrypts the saved TOTP secret and verifies the code with a small time-window allowance.",
      "If valid, `totp_enabled` is set to true and ten one-time backup codes are generated.",
      "Only hashed backup codes are stored; the plain backup codes are returned once for the user to save.",
    ],
  },
  {
    id: "twoFaVerify",
    group: "2FA",
    title: "Verify 2FA login",
    method: "POST",
    path: "/auth/2fa/verify",
    submitLabel: "Complete 2FA login",
    fields: [
      { name: "user_id", label: "User id", type: "number" },
      { name: "temp_token", label: "Temporary token" },
      { name: "code", label: "Authenticator or backup code" },
    ],
    body: (values) => ({ ...values, user_id: Number(values.user_id) }),
    afterSuccess: "fetchMe",
    underHood: [
      "This request is used after `/auth/login` says `requires_2fa: true`.",
      "The route checks Redis for the temporary login token tied to the user id.",
      "It accepts either a current six-digit TOTP code or a valid backup code.",
      "Failed attempts are rate-limited in Redis; successful verification deletes the temporary token.",
      "After verification, the normal auth backend issues the HTTP-only cookie and the login becomes complete.",
    ],
  },
  {
    id: "twoFaDisable",
    group: "2FA",
    title: "Disable 2FA",
    method: "POST",
    path: "/auth/2fa/disable",
    submitLabel: "Disable 2FA",
    fields: [{ name: "secret_token", label: "6-digit authenticator code" }],
    body: (values) => values,
    underHood: [
      "The browser sends a credentialed HTTP POST request with a fresh authenticator code.",
      "The backend first confirms the user is authenticated and already has TOTP enabled.",
      "The saved TOTP secret is decrypted and the submitted code is verified.",
      "A valid code clears `totp_enabled`, removes the encrypted secret, removes backup codes, and commits the update.",
    ],
  },
  {
    id: "adminUsers",
    group: "Admin",
    title: "List all users",
    method: "GET",
    path: "/admin/users",
    submitLabel: "List users",
    underHood: [
      "The browser sends a credentialed HTTP GET request with the current auth cookie.",
      "The `RoleChecker` dependency allows only users whose role is `admin`.",
      "The route selects every user from the database and serializes each one through `UserOut`.",
      "Non-admin users get HTTP 403 before any user list query is returned.",
    ],
  },
  {
    id: "adminChangeRole",
    group: "Admin",
    title: "Change user role",
    method: "PATCH",
    path: "/admin/{u_id}/role",
    submitLabel: "Change role",
    fields: [
      { name: "u_id", label: "User id", type: "number" },
      {
        name: "role",
        label: "New role",
        type: "select",
        options: ["user", "moderator", "admin"],
      },
    ],
    resolvePath: (values) => `/admin/${encodeURIComponent(values.u_id)}/role`,
    body: (values) => ({ role: values.role }),
    underHood: [
      "The UI sends a credentialed HTTP PATCH request with the target user id in the URL.",
      "The admin role dependency runs first, so ordinary users cannot change roles.",
      "The body is validated against `RoleUpdate`, then the target user row is loaded from the database.",
      "If the user exists, their role enum is updated and committed; unknown ids return HTTP 404.",
    ],
  },
  {
    id: "adminUnlock",
    group: "Admin",
    title: "Unlock account",
    method: "POST",
    path: "/admin/unlock/{username}",
    submitLabel: "Unlock",
    fields: [{ name: "username", label: "Username to unlock" }],
    resolvePath: (values) => `/admin/unlock/${encodeURIComponent(values.username)}`,
    underHood: [
      "The browser sends a credentialed HTTP POST request with the username in the URL.",
      "The admin role dependency blocks non-admin users before the Redis lockout reset happens.",
      "The route deletes or resets the failed-login tracking keys for that username in Redis.",
      "After this, the affected user can attempt normal password login again.",
    ],
  },
];

function omitEmpty(values) {
  return Object.fromEntries(
    Object.entries(values).filter(([, value]) => value !== "" && value !== null),
  );
}

function buildUrl(path, query) {
  const url = new URL(`${API_BASE_URL}${path}`);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      url.searchParams.set(key, value);
    }
  });
  return url.toString();
}

function formatJson(value) {
  if (value === undefined) {
    return "";
  }
  return JSON.stringify(value, null, 2);
}

function getStatusKind(status) {
  if (!status) {
    return "idle";
  }
  if (status.loading) {
    return "loading";
  }
  if (status.error || (status.httpStatus && status.httpStatus >= 400)) {
    return "error";
  }
  return "success";
}

export default function App() {
  const [forms, setForms] = useState(initialForms);
  const [results, setResults] = useState({});
  const [currentUser, setCurrentUser] = useState(null);
  const [latestTwoFa, setLatestTwoFa] = useState(null);
  const [activity, setActivity] = useState([]);

  const groupedRoutes = useMemo(
    () =>
      routes.reduce((groups, route) => {
        groups[route.group] = [...(groups[route.group] || []), route];
        return groups;
      }, {}),
    [],
  );

  function updateField(routeId, fieldName, value) {
    setForms((current) => ({
      ...current,
      [routeId]: {
        ...(current[routeId] || {}),
        [fieldName]: value,
      },
    }));
  }

  function setRouteResult(routeId, result) {
    setResults((current) => ({
      ...current,
      [routeId]: result,
    }));
  }

  function appendActivity(entry) {
    setActivity((current) => [entry, ...current].slice(0, 8));
  }

  async function fetchCurrentUser() {
    try {
      const response = await fetch(buildUrl("/users/me"), {
        credentials: "include",
      });
      if (!response.ok) {
        setCurrentUser(null);
        return;
      }
      setCurrentUser(await response.json());
    } catch {
      setCurrentUser(null);
    }
  }

  async function submitRoute(route) {
    if (route.externalNavigation) {
      window.location.assign(buildUrl(route.path));
      return;
    }

    if (route.dangerous && !window.confirm("This will change account state. Continue?")) {
      return;
    }

    const startedAt = performance.now();
    const values = forms[route.id] || {};
    const path = route.resolvePath ? route.resolvePath(values) : route.path;
    const url = buildUrl(path, route.query?.(values));
    const bodyPayload = route.body?.(values);
    const requestInit = {
      method: route.method,
      credentials: "include",
      headers: {},
    };

    if (bodyPayload !== undefined && route.method !== "GET") {
      if (route.formEncoded) {
        requestInit.body = new URLSearchParams(bodyPayload);
        requestInit.headers["Content-Type"] = "application/x-www-form-urlencoded";
      } else {
        requestInit.body = JSON.stringify(bodyPayload);
        requestInit.headers["Content-Type"] = "application/json";
      }
    }

    setRouteResult(route.id, {
      loading: true,
      request: {
        method: route.method,
        url,
        body: bodyPayload,
        contentType: requestInit.headers["Content-Type"] || "none",
        credentials: "include",
      },
    });

    try {
      const response = await fetch(url, requestInit);
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();
      const elapsedMs = Math.round(performance.now() - startedAt);
      const nextResult = {
        loading: false,
        httpStatus: response.status,
        ok: response.ok,
        elapsedMs,
        request: {
          method: route.method,
          url,
          body: bodyPayload,
          contentType: requestInit.headers["Content-Type"] || "none",
          credentials: "include",
        },
        response: payload,
      };

      setRouteResult(route.id, nextResult);
      appendActivity({
        id: `${route.id}-${Date.now()}`,
        method: route.method,
        path,
        status: response.status,
        ok: response.ok,
      });

      if (response.ok) {
        if (route.afterSuccess === "storeMe") {
          setCurrentUser(payload);
        }
        if (route.afterSuccess === "fetchMe") {
          await fetchCurrentUser();
        }
        if (route.afterSuccess === "clearMe") {
          setCurrentUser(null);
        }
        if (route.afterSuccess === "maybeStore2fa") {
          if (payload?.requires_2fa) {
            setLatestTwoFa(payload);
            setForms((current) => ({
              ...current,
              twoFaVerify: {
                ...(current.twoFaVerify || {}),
                user_id: String(payload.user_id || ""),
                temp_token: payload.temp_token || "",
              },
            }));
          } else {
            await fetchCurrentUser();
          }
        }
      }
    } catch (error) {
      setRouteResult(route.id, {
        loading: false,
        error: error.message,
        request: {
          method: route.method,
          url,
          body: bodyPayload,
          contentType: requestInit.headers["Content-Type"] || "none",
          credentials: "include",
        },
      });
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">AuthCore React Frontend</p>
          <h1>Route-by-route API console</h1>
          <p className="hero-copy">
            This frontend calls every backend route from `VITE_API_URL` and explains
            what the request does inside FastAPI, SQLAlchemy, Redis, Celery, cookies,
            OAuth, and TOTP.
          </p>
        </div>
        <aside className="session-panel">
          <h2>Browser auth state</h2>
          <p>
            Auth cookies are HTTP-only, so React cannot read them directly. The reliable
            check is calling <code>GET /users/me</code> with <code>credentials: include</code>.
          </p>
          <button type="button" onClick={fetchCurrentUser}>
            Refresh current user
          </button>
          <pre>{currentUser ? formatJson(currentUser) : "No authenticated user loaded."}</pre>
          {latestTwoFa && (
            <div className="notice">
              Login returned a temporary 2FA token. The 2FA verification form was
              prefilled with `user_id` and `temp_token`.
            </div>
          )}
        </aside>
      </section>

      {activity.length > 0 && (
        <section className="activity-strip" aria-label="Recent requests">
          {activity.map((entry) => (
            <span key={entry.id} className={entry.ok ? "activity-ok" : "activity-error"}>
              {entry.method} {entry.path} → {entry.status}
            </span>
          ))}
        </section>
      )}

      {Object.entries(groupedRoutes).map(([group, groupRoutes]) => (
        <section className="route-group" key={group}>
          <h2>{group}</h2>
          <div className="route-grid">
            {groupRoutes.map((route) => (
              <RouteCard
                key={route.id}
                route={route}
                values={forms[route.id] || {}}
                result={results[route.id]}
                onFieldChange={updateField}
                onSubmit={submitRoute}
              />
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}

function RouteCard({ route, values, result, onFieldChange, onSubmit }) {
  const statusKind = getStatusKind(result);

  return (
    <article className={`route-card route-card-${statusKind}`}>
      <header className="route-header">
        <div>
          <span className={`method method-${route.method.toLowerCase()}`}>
            {route.method}
          </span>
          <code>{route.path}</code>
        </div>
        <span className="status-pill">{statusLabels[statusKind]}</span>
      </header>

      <h3>{route.title}</h3>

      {route.fields?.length > 0 && (
        <form className="field-stack" onSubmit={(event) => event.preventDefault()}>
          {route.fields.map((field) => (
            <label key={field.name}>
              <span>{field.label}</span>
              {field.type === "select" ? (
                <select
                  value={values[field.name] || ""}
                  onChange={(event) =>
                    onFieldChange(route.id, field.name, event.target.value)
                  }
                >
                  {field.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type || "text"}
                  value={values[field.name] || ""}
                  onChange={(event) =>
                    onFieldChange(route.id, field.name, event.target.value)
                  }
                  placeholder={field.placeholder || field.label}
                />
              )}
            </label>
          ))}
        </form>
      )}

      <button
        className={route.dangerous ? "danger-button" : ""}
        type="button"
        disabled={result?.loading}
        onClick={() => onSubmit(route)}
      >
        {result?.loading ? "Sending..." : route.submitLabel || "Send request"}
      </button>

      <details open>
        <summary>Under the hood</summary>
        <ul>
          {route.underHood.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
      </details>

      {result && (
        <section className="result-panel">
          <div className="result-meta">
            {result.httpStatus && <span>HTTP {result.httpStatus}</span>}
            {result.elapsedMs !== undefined && <span>{result.elapsedMs} ms</span>}
            {result.error && <span>{result.error}</span>}
          </div>
          <div className="request-response-grid">
            <div>
              <h4>Request sent</h4>
              <pre>{formatJson(result.request)}</pre>
            </div>
            <div>
              <h4>Response received</h4>
              <pre>
                {result.error
                  ? result.error
                  : result.response !== undefined
                    ? formatJson(result.response)
                    : "Waiting for response..."}
              </pre>
            </div>
          </div>
        </section>
      )}
    </article>
  );
}
