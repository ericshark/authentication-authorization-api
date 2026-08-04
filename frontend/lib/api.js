export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/backend";

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers);
  let body = options.body;

  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }

  if (options.form !== undefined) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
    body = new URLSearchParams(options.form).toString();
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    body,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const error = new Error(data?.detail || data?.message || `Request failed (${response.status})`);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return { data, status: response.status, headers: response.headers };
}

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}
