import axios from "axios";

// Reads VITE_API_URL from the .env file at build time.
// In dev, Vite's proxy (vite.config.ts) forwards /api → localhost:8000,
// so the baseURL just needs to match the prefix.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api/v1",
  withCredentials: true, // sends the httpOnly JWT cookie on every request
});

export default api;
