/**
 * Thin fetch wrapper. All requests carry the session cookie (credentials:
 * "include"). Backend validation is authoritative; this client trusts the
 * server's error messages rather than duplicating validation logic.
 *
 * CSRF: the backend uses a double-submit cookie pattern. On login/register/
 * password-change it sets a readable `rso_csrf` cookie alongside the
 * HttpOnly session cookie; every mutating request must echo that value
 * back in the `X-CSRF-Token` header, or the backend rejects it with 403.
 * `getCsrfCookie()` reads the cookie fresh on every call (rather than
 * caching it) so a token rotated by a login/password-change always wins.
 */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/**
 * Local dev and the Docker/nginx build both proxy same-origin `/api/v1/...`
 * requests to the backend, so the empty default keeps that behaviour.
 * A standalone production deploy (frontend and backend on different
 * origins/hosts) sets VITE_API_BASE_URL at build time to the backend's
 * full URL, e.g. "https://rockstar-organics-api.onrender.com".
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

/** Prefix a server-returned API path (e.g. `download_url`, `image_url`) with the API origin. */
export function mediaUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/**
 * The double-submit CSRF cookie (`rso_csrf`) is set by the API's origin.
 * For a same-origin deployment (Docker/nginx) that's also readable via
 * document.cookie on the frontend page, but for a standalone cross-origin
 * deployment (frontend on Vercel, API elsewhere) it is NOT: cookies are
 * scoped to the domain that set them, so JS on the frontend's origin has
 * no access to a cookie belonging to the API's origin. The API mirrors the
 * same token back in a readable `X-CSRF-Token` response header (exposed
 * via CORS - see app/core/csrf.py) on login/register/verify-otp/change-
 * password and on GET /auth/me, so this in-memory copy works regardless
 * of deployment topology; the cookie read remains as a fallback.
 */
let csrfToken: string | null = null;

function getCsrfCookie(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)rso_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function captureCsrfToken(res: Response): void {
  const token = res.headers.get("x-csrf-token");
  if (token) csrfToken = token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(options.headers as Record<string, string> || {}) };

  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const token = csrfToken || getCsrfCookie();
    if (token) headers["X-CSRF-Token"] = token;
  }

  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    credentials: "include",
    headers,
    ...options,
  });
  captureCsrfToken(res);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

/**
 * Some images (e.g. an unpublished agriculture photo) are deliberately not
 * public - the serving endpoint requires the session cookie. A plain
 * `<img src>` can't do that for a cross-origin API (SameSite=Lax cookies
 * aren't sent on cross-site subresource requests), so this fetches the
 * bytes with credentials and hands back a local object URL to assign as
 * the img src instead. Caller is responsible for URL.revokeObjectURL
 * once it's no longer displayed.
 */
export async function fetchAuthedImageUrl(path: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}${path}`, { credentials: "include" });
  if (!res.ok) throw new ApiError(res.status, `Could not load image (${res.status})`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/**
 * File uploads use FormData (never JSON), so they go through this helper
 * rather than `api.post` - but they still need the session cookie and the
 * CSRF header like any other mutating request.
 */
export async function uploadFile<T>(path: string, formData: FormData): Promise<T> {
  const token = csrfToken || getCsrfCookie();
  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    method: "POST",
    credentials: "include",
    headers: token ? { "X-CSRF-Token": token } : undefined,
    body: formData,
  });
  captureCsrfToken(res);
  if (!res.ok) {
    let detail = `Upload failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}
