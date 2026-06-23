# Architecture & Trade-off Decisions

Each entry records a choice that deviated from the spec, a question that
required a judgement call, or a constraint accepted knowingly. Logged so
future sessions don't re-litigate settled questions.

---

## 001 — Keep React 19 instead of downgrading to 18

**Spec says:** React 18  
**Repo has:** React 19 (already installed when project was set up)  
**Decision:** Keep 19. Every library in the spec (TanStack Query v5, react-leaflet
v5, react-router-dom v7, recharts v3, react-i18next) is fully compatible with
React 19. No breaking changes affect our usage. Downgrading would be churn with
no benefit.

---

## 002 — Keep react-router-dom v7 instead of v6

**Spec says:** React Router v6  
**Repo has:** v7 (already installed)  
**Decision:** Keep v7. The API surface we use (`BrowserRouter`, `Routes`, `Route`,
`Link`, `useNavigate`, `useParams`) is identical in v6 and v7. The breaking
changes in v7 are in the framework-mode ("React Router as a framework") which we
are not using. Will call out any v6→v7 difference as it appears.

---

## 003 — `cors_origins` stored as `str` in Settings

**Spec says:** nothing explicit about the field type  
**Problem:** Pydantic-settings v2 tries to JSON-decode any `list[...]`-typed field
before field validators run. `http://localhost:5173` is not valid JSON, so startup
crashed with a `JSONDecodeError`.  
**Decision:** Type `cors_origins` as plain `str` in `Settings`; split on commas
when building the CORS middleware in `main.py`. Simple, robust, no footguns.

---

## 004 — `extra="ignore"` in Pydantic Settings

**Problem:** `.env` contains `VITE_API_URL` (a Vite/frontend variable). Pydantic
v2 strict mode rejects unknown fields by default, causing startup to fail.  
**Decision:** Add `extra="ignore"` to `SettingsConfigDict`. The frontend and
backend share one `.env` file for convenience in local dev; ignoring unknown keys
is the right call rather than splitting into two files.

---

## 005 — Python 3.14 in local venv, 3.12 in Dockerfile

**Spec says:** Python 3.12  
**Machine has:** Python 3.14 installed globally; venv uses 3.14 bytecache  
**Decision:** Accept 3.14 locally — all dependencies work. Dockerfile pins
`python:3.12-slim` so production (Railway) and CI (GitHub Actions) both match the
spec. Flag on Day 16 if Railway's build image doesn't yet carry 3.12.

---

## 006 — recharts v3 (not v2)

**Original scaffold had:** `recharts ^3.8.1`  
**Accidentally downgraded to:** v2 during dependency cleanup  
**Decision:** Restored to v3. v2 is no longer maintained and carries known
vulnerabilities. v3 migration guide exists; we will follow it when implementing
the hourly chart on Day 6.
