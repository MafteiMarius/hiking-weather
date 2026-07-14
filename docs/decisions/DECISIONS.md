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

## 008 — fastapi-users v15: DatabaseStrategy removed, AccessToken model owned by us

**What changed:** fastapi-users 15.0 dropped `DatabaseStrategy`, `SQLAlchemyBaseAccessTokenTableUUID`, and `SQLAlchemyAccessTokenDatabase`. The library no longer provides a DB-backed token strategy or an AccessToken base model.

**Decision:** We own the `access_tokens` table entirely. Added `expires_at TIMESTAMPTZ` column (required for expiry checks) and wrote thin helpers in `app/core/tokens.py`: `create_refresh_token`, `get_user_id_for_refresh_token`, `revoke_refresh_token`. The rest of fastapi-users (UserManager, register router, users router, current_user dependency, Argon2id) is unchanged.

---

## 009 — pytest-asyncio loop-scope configuration

**Problem:** Module-level `create_async_engine` + session-scoped fixtures + function-scoped tests caused asyncpg "Future attached to a different loop" errors.

**Decision:** Set `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml` so all async fixtures share one event loop. Add `pytestmark = pytest.mark.asyncio(loop_scope="session")` in each test module so tests also run in that loop. Engine is created inside a `scope="session"` fixture (not at module level) so it belongs to the right loop from the start.

---

## 010 — Test email domain must be a real TLD

**Problem:** `test@hikecast.test` fails `EmailStr` validation in email-validator ≥ 2.x because `.test` is RFC 6761 reserved.

**Decision:** Use `test@example.com` in tests. `example.com` is IANA-reserved for documentation and will never exist, so it's safe for test data and always passes email syntax validation.

---

## 007 — Two-token auth: stateless JWT access + DB-backed refresh

**Choice:** Short-lived JWT (15 min) in `hikecast_access` cookie for access; opaque token in `access_tokens` table and `hikecast_refresh` cookie for refresh.

**Why DB-backed refresh:** Clearing the cookie on logout is not enough — the token itself would still be valid until expiry if stolen. Storing refresh tokens in the DB lets logout do a hard `DELETE`, making the token unusable even if someone captured the cookie. No Redis in v1, so the DB is the revocation store.

**Why custom login/logout/refresh endpoints:** fastapi-users' built-in login route handles one backend. Issuing two tokens and setting two cookies in one response requires control over the `Response` object, so we write those three endpoints ourselves and use fastapi-users only for user management, register, `/users/me`, and the `current_user` dependency.

**Trade-off accepted:** Refresh tokens are not rotated on every use (a security best practice). Single-use rotation would require deleting the old refresh row and issuing a new one on every `/refresh` call, which adds DB writes on every token refresh. For v1 with a 30-day window, the risk is acceptable. Add rotation in v2 if this ships to production.

---

## 011 — Climatology: ERA5 weather codes undercount thunderstorms

**Observed:** For Bucegi in July — prime Carpathian thunderstorm season — ERA5
daily `weather_code` yields 0% thunderstorm days. ERA5 is a reanalysis (a model
re-run over observations); its daily code is derived from model precipitation
fields and rarely produces the convective codes (95/96/99).

**Decision:** Keep `thunderstorm_pct` in the schema and warning logic (it may
fire in other datasets/regions and costs nothing), but rely on the other
metrics to carry the instability signal: wet-day frequency, 90th-percentile
gust, and a volatility index. Volatility is defined as the share of
consecutive-day transitions that flip between wet (≥ 1 mm) and dry — a proxy
for "forecasts age fast here". Warning thresholds: thunder ≥ 20%, wet days
≥ 50%, p90 gust ≥ 70 km/h, volatility ≥ 40%. Revisit with CAPE-based hourly
archive data if the warning proves too quiet in storm season.

---

## 012 — AI integration: backend-only Claude calls, optional by config

**Choice:** AI features (packing advice, more later) run exclusively through the
backend (`services/ai.py`, Anthropic Python SDK). The frontend calls
`POST /api/v1/ai/*` and never touches Anthropic directly.

**Why backend-only:** the API key must not ship to browsers; the backend already
holds the forecast/climatology context so prompts stay server-side; auth-gating
(login required) prevents anonymous visitors from spending money.

**Why optional:** `ANTHROPIC_API_KEY` unset → endpoints return 503 and the UI
shows a friendly message. The app must stay fully usable (and deployable free)
without any AI dependency.

**Structured outputs, not prose parsing:** `client.messages.parse()` with a
Pydantic `output_format` guarantees a schema-valid `EquipmentPlan` — no JSON
repair. Model is configurable (`ANTHROPIC_MODEL`, default `claude-opus-4-8`);
the static system prompt carries a `cache_control` breakpoint so Anthropic's
prompt caching reduces per-call cost. Note: the current Claude API uses
adaptive thinking (`{"type": "adaptive"}`) — `budget_tokens`, `temperature`
etc. are removed on Opus 4.7+ and will 400.

**Trade-off accepted:** no response caching per (location, date) in v1 — every
button press is one paid call. Add a small DB cache if usage grows.

**Addendum (2026-07-12) — local-LLM fallback, designed but not built:** to make
the feature work without an API key, add Ollama as a second provider behind
the same `EquipmentPlan` schema. Provider order: `ANTHROPIC_API_KEY` set →
Claude; else `OLLAMA_BASE_URL` set → local model via Ollama's native
`/api/chat` with `format = EquipmentPlan.model_json_schema()` (grammar-
constrained JSON, the local equivalent of `messages.parse()`); else 503 as
today. No new dependency (uses the shared httpx client). Expect weaker reason
quality from 7–8B models and 20–60 s CPU latency; the UI's pending state
already tolerates this. Deliberately opt-in via config so production
(no local Ollama) degrades to Claude-or-503 unchanged.

---

## 013 — Trail catalogue data is drafted, not surveyed — RESOLVED 2026-07-11

**What:** the 25 seed trails (`app/seeds/trails.py`) carry coordinates,
distances, durations, and elevation figures drafted from general route
knowledge. Plausible, but NOT verified against maps or GPS tracks.

**Decision:** ship the feature now to unblock UI/forecast integration; verify
every figure against Munții Noștri / OpenTopoMap before promoting the data as
trustworthy. The seed file and README both carry the warning.

**Resolution (2026-07-11):** all coordinates and summit elevations verified
against OpenStreetMap via the Overpass API (bounding-box queries around each
drafted point; worst drafts were off by 12 km). Distances/durations
standardised as ONE-WAY trailhead→destination estimates (full loop for
circuits), sanity-checked against guidebook times — planning figures, not GPS
tracks. Known source conflicts kept in the seed docstring: Vârful Turnu
1923 m (guidebooks) vs 1911 m (OSM); Omu 2505 vs 2507. The seeder gained an
`--update` mode because the default insert-only mode deliberately never
touches existing rows — corrections need an explicit
`python -m app.seeds.trails --update`.

---

## 014 — Recommendation ranking: weather first, profile as adjustment

**Choice:** `GET /api/v1/recommendations` ranks trails by the weather safety
score at each trail's summit (start point when no summit), then subtracts
personal penalties: 8 points per difficulty level above the profile's
`experience_level`, and up to 10 points for distance from home (linear to
`max_distance_km`). `max_difficulty` and `max_distance_km` are hard filters.

**Why weather dominates:** the maximum distance penalty (10) is deliberately
smaller than one score-label step (15–20), so a stormy trail near home can
never outrank a clear day further away. Safety ranking must not be
personalisable into unsafety.

**Why the breakdown is exposed:** every response item carries
`weather_score`, `difficulty_penalty`, `distance_penalty`, and the excluded
count, and the UI renders them — a ranking users can't interrogate is a
ranking they won't trust.

**Bulk forecast fetch:** ranking 25 trails must not mean 25 Open-Meteo round
trips. `get_forecasts_bulk()` sends one request with comma-separated
coordinates (Open-Meteo returns a list — or a bare object for a single
point) and upserts each payload under the same per-grid-cell cache keys the
map view uses, so the two features share one cache. A length-mismatch guard
raises instead of letting `zip()` silently mis-pair cells.

**Trade-off accepted:** the ranking core is pure and unit-tested with
hand-computed values (see `tests/test_recommend.py`), but the penalty
constants themselves are judgement calls, not learned weights — revisit if
real usage shows the ranking feels off.

---

## 015 — Profile editor lives on the map, home is picked ON the map

**Choice:** the hiking-profile trigger is a map overlay button (next to
Saved), not a header/menu item, and home location is set by a pick-on-map
mode: "Choose on map" hides the dialog (children stay mounted, so unsaved
edits survive), a hint pill appears, and the next map click becomes home and
brings the dialog back. No coordinate inputs, no second map.

**Why:** the app already has exactly one way to point at a place (the map),
so reusing it costs zero new UI. A header trigger would have forced lifting
pin state out of `ForecastPage` or a context just to pass coordinates to a
dialog. Typed lat/lng inputs invite garbage data for no benefit at this
scale.

**First cut failed in real use:** v1 was a "Use map pin" button that copied
the pin's *current* position — which forced positioning the pin before
opening the dialog, and Marius (reasonably) expected the button itself to
start a placement interaction. Lesson: a modal that needs input from the
surface it covers must hand control back to that surface, not assume the
user prepared it in advance. Mechanics: `Dialog` gained a `hidden` prop
(display-none without unmount), the page owns the one-shot picking mode, and
the picked point deliberately does NOT move the forecast pin (home is
usually a city, not the spot being forecast).

**Clearing semantics:** the form always PATCHes the full field set; clearing
home sends explicit `home_lat/lng: null` (Pydantic `exclude_unset` treats a
present null as "set to null", an absent field as "leave alone"). Documented
in `ProfileUpdate` (frontend type) because the distinction is invisible at
the call site.

**Related fix:** logout now drops user-scoped query caches (saved-locations,
profile, recommendations). With 5-minute `staleTime`, TanStack Query would
otherwise happily serve user A's data to user B for a few minutes after an
account switch on the same browser.

---

## 006 — recharts v3 (not v2)

**Original scaffold had:** `recharts ^3.8.1`  
**Accidentally downgraded to:** v2 during dependency cleanup  
**Decision:** Restored to v3. v2 is no longer maintained and carries known
vulnerabilities. v3 migration guide exists; we will follow it when implementing
the hourly chart on Day 6.
