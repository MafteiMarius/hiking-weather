import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

// Reads VITE_API_URL from the .env file at build time.
// In dev, Vite's proxy (vite.config.ts) forwards /api → localhost:8000,
// so the baseURL just needs to match the prefix.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api/v1",
  withCredentials: true, // sends the httpOnly JWT cookie on every request
});

// ── Silent token refresh ──────────────────────────────────────────────────────
// The access JWT lives 15 minutes; the refresh token (DB-backed) lives 30 days.
// When any request comes back 401 we call /auth/jwt/refresh once and replay the
// original request. If the refresh itself fails the user really is logged out
// and the original 401 propagates to the caller.

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

// Shared promise so concurrent 401s trigger a single refresh call.
let refreshInFlight: Promise<unknown> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    // Never refresh-and-retry auth calls themselves (login failures are real,
    // and /auth/jwt/refresh must not recurse into itself).
    if (
      error.response?.status !== 401 ||
      !config ||
      config._retried ||
      config.url?.startsWith("/auth/")
    ) {
      throw error;
    }

    config._retried = true;
    refreshInFlight ??= api
      .post("/auth/jwt/refresh")
      .finally(() => {
        refreshInFlight = null;
      });

    try {
      await refreshInFlight;
    } catch {
      throw error; // refresh token expired/revoked → surface the original 401
    }
    return api(config);
  },
);

export default api;
