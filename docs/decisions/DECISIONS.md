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

## 016 — i18n: server localizes generated text, frontend localizes chrome

**Context:** much user-facing text is *generated* server-side and some
interpolates live numbers — weather descriptions, score reasons ("Strong
gusts (54 km/h)"), and the climatology instability sentences. The frontend
can't translate those from a static bundle, so the split is:

- **Server-generated / interpolated text → localized on the backend.** New
  `app/i18n` package: flat EN+RO message tables (`messages.py`) keyed by
  stable codes (`reason.wind.strong`), rendered by `t(key, lang, **params)`
  via `str.format`. `scoring.py` keeps the *logic* (which factor wins, how
  big the penalty) and now returns a message **key + params**; the wording
  lives in the tables. `describe_weather(code, lang)` replaces the old
  `WMO_DESCRIPTIONS` dict. Chosen over gettext/.po — ~50 short strings, no
  plural rules worth the toolchain, and dict values stay greppable.
- **Static UI chrome → localized on the frontend** with react-i18next
  (`en.json`/`ro.json`), the existing wiring.
- **The score label enum ("Excellent"…"Dangerous") stays English in the API**
  and is translated by the frontend for display, because the frontend already
  keys styling off it (`SCORE_STYLES`, `SCORE_DOT`). Localizing it server-side
  would break those lookups.

**Language selection — `Accept-Language`, not the profile.** The forecast and
climatology endpoints are public (no auth), so a profile locale can't drive
them. The web client sends `Accept-Language` (an axios request interceptor
reads the live `i18n.language`); `resolve_lang` maps it to en/ro. One
mechanism covers anonymous and authed users alike.

**Why the API default is English while the UI default is Romanian.** The web
app's `fallbackLng` is `ro` and it always sends `Accept-Language: ro` for a
first-time visitor — so users get Romanian. But the API's *header-absent*
default is English (`DEFAULT_LANG`), which only affects non-UI callers (curl,
tests, other clients). Keeping it English means the existing test suite, which
asserts English strings without sending a header, stays valid — the i18n
refactor produces byte-identical English output, so not one prior scoring or
forecast assertion changed.

**Frontend refetch on switch:** the active language is part of the
`forecast` / `climatology` / `recommendations` query keys. Flipping the toggle
changes the key, so React Query fetches the new-language payload and caches
both — no manual invalidation, no stale-language flash. (Trails and geocode
results are proper nouns; deliberately not language-keyed.)

**Trade-off / status:** EN and RO tables must be kept key-for-key in sync by
hand — a missing key degrades to the English fallback, never a crash (tested).
Backend, language plumbing, and the full component-chrome pass are all shipped
and browser-verified in both languages. Weekday names come from `Intl` (no
hand-kept table); the score-label enum is translated for display only. The one
remaining English surface is the AI packing plan (summary/items/warnings),
left until AI comes off hold — the prompt should then request output in the
request `lang`.

---

## 017 — Production: Vercel proxies /api to the backend, keeping cookies first-party

**The problem.** Auth is httpOnly cookies with `SameSite=Lax`
(`api/v1/endpoints/auth.py`, `core/auth.py`). Split across
`hikecast.vercel.app` and a separate backend host (`*.onrender.com`), every API
call becomes *cross-site*, and a `Lax` cookie is by definition not sent on
cross-site requests. Login would return 200 and set the cookie; every authenticated
request afterwards would 401. The failure is silent and looks like a broken
session rather than a config mistake.

**Options considered.**

1. **`SameSite=None; Secure`** — make the attribute configurable, relax it in
   production, add exact CORS origins with `allow_credentials`. Works, and it's
   the textbook answer. But the cookie is then third-party: Safari's ITP blocks
   it outright, Firefox strict mode and Brave block it, and most ad blockers do
   too. For a portfolio link that gets opened on someone else's browser, "login
   silently fails for a third of visitors" is the worst possible failure mode.
2. **Vercel rewrite** (`frontend/vercel.json`) — the browser only ever talks to
   the Vercel domain, which forwards `/api/*` to the backend server-side.
   Requests are same-origin, the cookie stays first-party, `SameSite=Lax` keeps
   working **unchanged**, and CORS stops being load-bearing.

**Decision: the rewrite.** It removes the failure mode instead of configuring
around it, and it leaves the stricter cookie attribute in place — `Lax` is
meaningful CSRF protection that option 1 would have traded away for nothing.
Zero backend code changed as a result.

**Cost accepted:** one extra network hop through Vercel's edge on every API
call, and the API is now reachable at two addresses (via Vercel, and the
backend host directly). The latter is why `CORS_ORIGINS` is still set properly
rather than dropped.

**The trap this creates.** Setting `VITE_API_URL` to the backend URL in the
Vercel dashboard bypasses the proxy and reintroduces the exact bug. Guarded by
committing `frontend/.env.production` with the relative `/api/v1`, with the
reasoning in the file, plus a warning in `docs/DEPLOYMENT.md`. A dashboard
setting nobody can see from the repo was too easy to get wrong.

---

## 018 — Managed-Postgres URLs are normalized in config, not by hand

**Problem.** Neon (and Railway, Supabase, Heroku) hand out libpq connection
strings: `postgresql://user:pass@host/db?sslmode=require`. Two things in that
break this app — SQLAlchemy needs `postgresql+asyncpg://` to select the async
dialect (a bare `postgresql://` reaches for psycopg2, which isn't installed),
and `sslmode` is a libpq parameter that asyncpg rejects at connect time.

**Decision:** `normalize_database_url()` in `app/core/config.py` translates
both, exposed as `Settings.sqlalchemy_url` / `.sqlalchemy_connect_args`. Every
connection opener goes through them (`db/session.py`, `alembic/env.py`).

**Why translate rather than document "edit the string first":** a hand-edited
connection string is a one-time manual step that silently rots — it has to be
redone on every credential rotation, and getting it wrong produces an obscure
`TypeError` from deep inside asyncpg. Doing it in code means the provider's
string is pasted verbatim and the behaviour is unit-testable
(`tests/test_config.py`, 14 hand-written cases) without a live managed
database, which we can't reach from the test suite.

**Why not rely on the dialect:** SQLAlchemy's asyncpg dialect has handled
`sslmode` inconsistently across versions. Owning the translation makes the
behaviour version-independent and greppable.

**Also here:** `pool_pre_ping` + `pool_recycle=280` on the engine, because
managed Postgres drops idle connections and the pool would otherwise hand out
a dead one after an idle spell — the classic "first request after a quiet
period fails" bug on free tiers.

---

## 019 — Hosting: Neon + Render + Vercel, all free tiers

**Context.** The deployment exists to be presented at an exam in September 2026
and to be linkable afterwards. It is not expected to carry real traffic. So the
objective is **$0/month with a demo that doesn't embarrass us**, not
throughput.

**What actually costs money.** Not the frontend — Vercel Hobby and Netlify Free
are both $0. The only priced component is the **backend container**: Railway
retired its free tier (the "Free" plan grants $1/month of credits, and memory
alone for a 0.5 GB service runs ~$5/month at their per-second rate, so it dies
after about six days). Railway Hobby is a $5/month *minimum*, not a cap.

**Decision:** Render's free instance type for the backend, Neon free for the
database, Vercel Hobby for the frontend. Total $0, no credit card anywhere.

**Cost accepted — the backend sleeps.** Render spins a free service down after
15 minutes without inbound traffic; waking takes about a minute. Mitigation is
procedural, not technical: open the app a few minutes before presenting. A
keep-alive pinger would technically fit inside the 750 instance-hours/month
allowance (a 30-day month is 720 hours), but Render states there is no
supported way to prevent spin-down, so the demo does not depend on it.

**Why not Netlify, despite it being the "free" one people reach for.** Its free
tier moved to credits: 300/month, **15 per production deploy** — about 20
production deploys a month, shared with bandwidth and requests, after which the
project *pauses*. Vercel Hobby allows 100 deploys per day. Netlify's proxy also
times out around 30 s against Vercel's documented 120 s, which matters if the
Ollama fallback (20–60 s calls, DECISIONS 012) is ever built. For a project
under active iteration before a deadline, Netlify was the more restrictive
choice despite the identical $0 price.

**Consequence worth remembering: no shell on Render free.** Seeding therefore
runs from a developer laptop with `DATABASE_URL` pointed at Neon rather than
from a server shell. That is only possible because the app accepts a provider
connection string verbatim (DECISIONS 018) — the two decisions support each
other.

**Reversibility is the real safeguard.** Nothing host-specific leaked into the
image: the Dockerfile binds `$PORT` and reads plain env vars, so `render.yaml`
is the only Render-shaped artefact in the repo. Moving to a paid always-warm
instance, or back to Railway, is a config change rather than a rewrite.

---

## 020 — Open-Meteo blocks shared hosting IPs; degrade to stale, never to fiction

**Observed (2026-08-10, first live deploy).** `api.open-meteo.com` returns an
error to Render's outbound IP on every request, instantly. Meanwhile
`geocoding-api.open-meteo.com` and `archive-api.open-meteo.com` — different
hosts, separate quota buckets — work fine from the same container. The
identical requests succeed from a residential IP, including the trivial
elevation one. So the requests are valid; the *caller* is being refused.
Open-Meteo's free API rate-limits by IP, and shared cloud IPs arrive
pre-exhausted by other tenants.

**Decision, three parts.**

1. **Log what upstream actually said.** `raise_for_status()` discarded the
   response body, so a bare 502 was all anyone ever saw — and Render's free
   tier has no shell to investigate with. `_raise_for_status()` now logs
   status, host, and body first; `main.py` configures the root logger, which
   uvicorn leaves alone, so those lines reach the host's log stream.
2. **Send a real User-Agent.** The client sent `python-httpx/x.y`, which from a
   datacenter IP is indistinguishable from a scraper — and these providers
   have tightened blocking precisely because of scraper traffic. We already
   learned this with Overpass (406 without a custom agent) and failed to
   generalise it.
3. **Serve stale rather than fail.** `get_forecast` no longer filters the cache
   lookup on `expires_at`; an expired row is kept as a fallback. If upstream
   refuses and *any* cached payload exists, it is returned with `stale=True`.

**Why `stale` is on the wire and in the UI, not swallowed.** This app exists to
help someone decide whether to walk up a mountain. Silently presenting
yesterday's numbers as today's is worse than an error page, because an error
is obviously an error. So the flag reaches the client, and
`StaleForecastBanner` says which timestamp the data is from and to check
conditions before setting out.

**What we deliberately did NOT do:** fall back to *anything* when no cache
entry exists. A missing forecast stays a 502. Interpolating from neighbouring
cells or showing climatology-as-forecast would be inventing weather, and the
whole point of the score is that it is grounded in real data.

**Operational consequence — `app/seeds/warm_cache.py`.** Since the backend
cannot reliably fill its own cache, a laptop fills it: the script calls the
application's own `get_forecasts_bulk` (so entries land under exactly the keys
the API reads) for every trailhead and summit plus any extra coordinates,
against production. Run it with a long `FORECAST_CACHE_TTL_MINUTES` before a
demo. This is a workaround for a free-tier constraint, not an architecture —
if the User-Agent fix or a different egress IP resolves the block, warming
becomes a nice-to-have rather than a dependency.

**RESOLVED (2026-08-10, same day) — route forecast calls out through Vercel.**

The User-Agent theory was wrong: with a proper agent deployed, Render was still
refused. The log line settled it —
`HTTP 429 "Minutely API request limit exceeded"` — so this is a *shared
per-minute quota* that Render's IP is permanently over, not a ban on us.

Vercel's edge is not: the same requests from `hiking-weather.vercel.app` return
200 in ~70 ms, including the 20-point bulk call. So `frontend/vercel.json`
proxies `/upstream/open-meteo/*` to Open-Meteo, and `OPEN_METEO_BASE_URL` on
Render points at that path. The backend's outbound forecast traffic now leaves
from Vercel instead of Render. **No application code changed** — the base URL
was already configuration.

*Trade-offs accepted:*

- **The backend now depends on the frontend's domain.** Inverted, and slightly
  absurd. It is one env var, reversible by deleting the key, and the honest
  alternative was a broken app or a paid plan.
- **`/upstream/open-meteo/*` is an open proxy.** Anyone could route their own
  Open-Meteo traffic through the site and spend its quota. Acceptable for an
  unadvertised portfolio deployment; it would need an auth check or a same-origin
  restriction before this was anything more.
- **Archive and geocoding stay direct.** Different hosts, different quotas, and
  they answer Render fine. Standby rewrites exist so switching them is an env
  var away, but routing large ERA5 payloads through Vercel for no reason would
  just spend bandwidth.
- **Warming is now a backup, not the mechanism.** Keep it for demo-day
  insurance and because it still protects against Vercel being the thing that
  breaks.

---

## 006 — recharts v3 (not v2)

**Original scaffold had:** `recharts ^3.8.1`  
**Accidentally downgraded to:** v2 during dependency cleanup  
**Decision:** Restored to v3. v2 is no longer maintained and carries known
vulnerabilities. v3 migration guide exists; we will follow it when implementing
the hourly chart on Day 6.
