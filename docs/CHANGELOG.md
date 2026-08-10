# HikeCast — Changelog & Project State

> **Purpose:** single source of truth for what is built, what comes next, and
> how to resume work. Written to be the first file an AI agent (or a returning
> human) reads. Sections are ordered by usefulness for picking up work, not
> chronologically — the session log is at the bottom.
>
> **Maintenance contract:** at the end of every working session, update
> CURRENT STATE and NEXT UP, and prepend one entry to the SESSION LOG.
> Keep architecture *reasoning* in `docs/decisions/DECISIONS.md` (referenced
> as "DECISIONS NNN"); keep user-facing docs in `README.md`. Don't duplicate
> content across the three — link instead.

---

## CURRENT STATE (updated 2026-08-10)

18-day portfolio project (FMI) + real-use tool; started 2026-06-23; solo dev
(Marius) pair-programming with an AI agent. Backend: FastAPI + SQLAlchemy 2
async + PostgreSQL/PostGIS (Docker). Frontend: React 19 + TS + Tailwind v4 +
Leaflet + TanStack Query.

**Working end-to-end:** scored 7-day forecast (map click / search), hourly
drill-down chart, cookie auth with silent refresh, saved locations, ERA5
climatology instability banner, trail catalogue (25 routes, OSM-verified),
personalised trail recommendations, profile dialog (experience/difficulty/
home-from-pin/max-distance — feeds the recommendations), AI packing advice
(Claude, optional — 503 without API key, never tested live).

Romanian i18n is **complete** (bar the AI packing prompt, which stays English
while AI is on hold): all server-generated text is localized via
`Accept-Language`, every component's static chrome goes through
react-i18next, weekday names come from `Intl` in the active locale, the
score-label enum is translated for display (English enum kept for styling),
and a header RO/EN toggle (default RO) flips the whole UI. Both languages
browser-verified end to end.

**Deployment-ready, not yet deployed:** the container, database-URL handling,
and Vercel proxy config are built and locally verified; the three provider
steps that need Marius' accounts are not done. Runbook: `docs/DEPLOYMENT.md`.

**Quality bar:** 107 backend tests green; frontend `npx eslint src` and
`npx tsc --noEmit` clean. Every feature verified in the browser before done.

**Data caveats:** trail distances/durations are one-way planning estimates,
not GPS tracks (DECISIONS 013). ERA5 undercounts thunderstorms (DECISIONS 011).

---

## NEXT UP (priority order, with pickup context)

0. **Set `OPEN_METEO_BASE_URL` on Render** to
   `https://hiking-weather.vercel.app/upstream/open-meteo/v1` (Environment →
   Add; the service restarts itself). That is the last step of the Open-Meteo
   fix — everything else is pushed. Verify with a coordinate that was never
   warmed; see `docs/DEPLOYMENT.md`.
   **Before the exam (insurance, no longer required):** run
   `python -m app.seeds.warm_cache --regions --ipv4 45.36,25.46` that morning
   with `FORECAST_CACHE_TTL_MINUTES=1440`.

1. **Deployment — code side DONE, provider side pending.** Follow
   `docs/DEPLOYMENT.md` start to finish. Stack is Neon + Render + Vercel, all
   free tiers, $0/month, no card (DECISIONS 019). It needs three things only
   Marius can do: create the Neon project (+ `CREATE EXTENSION postgis,
   pgcrypto`), create the Render service from `render.yaml` (Blueprint) and
   answer the two prompts, and import the frontend on Vercel.
   **Before the Vercel deploy, replace `REPLACE-ME.onrender.com` in
   `frontend/vercel.json` with the real Render domain** — it is a placeholder.
   Seed trails **from the laptop** with `DATABASE_URL` pointed at Neon: Render's
   free tier has no shell. Then run the post-deploy checklist; the browser
   cookie steps are the ones that matter (DECISIONS 017).
   *Demo note:* the free backend sleeps after 15 min idle and takes ~1 min to
   wake — open the app a few minutes before presenting.
   *Loose end:* `backend/requirements.txt` is a stale pip-freeze from an
   unrelated environment (pandas, openmeteo_requests; missing sqlalchemy,
   alembic, asyncpg). Nothing reads it — `pyproject.toml` is authoritative and
   the Dockerfile installs from it — but it is a trap for any tool that
   auto-detects it. Recommend deleting.
2. **AI: live test or local fallback** — ON HOLD by Marius' choice (no
   ANTHROPIC_API_KEY for now). Option A: add key, verify "What to pack?"
   end-to-end (never tested against the real API). Option B: build the
   designed Ollama fallback (DECISIONS 012 addendum) so it works keyless.
   *i18n note:* when AI is switched on, make the prompt locale-aware (pass the
   request `lang` into `recommend_equipment` and ask for RO output when
   `ro`) — the packing summary/items/warnings are the last English-only
   user-facing strings.
3. **Later / nice-to-have:** ANM nowcasting alerts overlay, GPX import,
   multi-point trail forecasts, PWA polish, refresh-token rotation
   (DECISIONS 007 trade-off), `is_loop` flag on trails so the UI can label
   one-way vs loop distances, small response cache for AI calls.

---

## HOW TO RUN & VERIFY

```bash
docker compose up -d db                  # Postgres+PostGIS (container: hiking-weather-db-1)

# backend (from backend/, venv at backend/venv)
uvicorn app.main:app --reload            # http://localhost:8000/docs
python -m app.seeds.demo                 # demo@hikecast.app / HikeCast2026!
python -m app.seeds.trails               # idempotent; --update refreshes existing rows

# frontend (from frontend/)
npm run dev                              # http://localhost:5173 (proxies /api → :8000)

# tests (needs hikecast_test DB with pgcrypto+postgis; fixtures create/drop tables)
TEST_DATABASE_URL="postgresql+asyncpg://hikecast:hikecast@localhost:5432/hikecast_test" pytest
npx eslint src && npx tsc --noEmit       # frontend checks
```

`.claude/launch.json` has `backend` / `frontend` preview configs for agent use.

## CONVENTIONS (how work happens here)

- Marius reviews and **commits himself** — leave the tree uncommitted at
  session end and suggest a conventional-commit split.
- Small diffs; tests for critical paths as the feature is built (pure logic
  gets hand-computed unit tests — see scoring.py / recommend.py pattern).
- **Light UI only:** stone neutrals, white surfaces, single green-700 accent.
  No dark slate / neon "AI look" — explicit, repeated preference.
- Teach-as-you-go: code comments explain WHY (see scoring.py docstring style).
- Update this file + DECISIONS.md + README at session end.

## GOTCHAS (hard-won, do not rediscover)

- **Tailwind v4 dev HMR serves scrambled CSS** — hard-reload (Ctrl+F5) before
  judging UI; prefer longhand flex utilities (`lg:grow lg:basis-0`) over
  `flex-1` next to `shrink-0`.
- **Forecast cache key includes `days`** — a 1-day fetch must never poison
  7-day requests (regression-tested).
- **Open-Meteo bulk requests** return a bare object for one point, a list for
  many — `get_forecasts_bulk` normalizes and guards length mismatches.
- `hikecast_test` DB is empty outside pytest runs (fixtures create/drop).
- ERA5 daily `weather_code` yields ~0% thunderstorms in the Carpathians —
  wet-day %, p90 gust, and volatility carry the instability signal.
- Overpass API: 406 without a custom User-Agent; country-wide regex queries
  time out — use small bounding boxes.
- Claude API (2026): `thinking={"type":"adaptive"}`,
  `messages.parse(output_format=Model)`, model `claude-opus-4-8`;
  `budget_tokens`/`temperature` are removed (400).
- SQLAlchemy `AsyncSession` is not concurrency-safe — tests share one session
  via dependency override, so services must not fan out parallel DB work.

---

## SESSION LOG (newest first)

### 2026-08-10 (later) — First live deploy; Open-Meteo blocks Render's IP

**The app is live**: https://hiking-weather.vercel.app — Neon + Render + Vercel,
$0/month. Marius did the provider steps; verified end to end in the browser
(Romanian 7-day forecast, scores, instability banner, all through the Vercel
proxy). The cookie architecture (DECISIONS 017) works as designed.

- **Seeding hit an IPv6 trap.** The trail seeder timed out from Marius' laptop:
  DNS returns Neon's AAAA records first, IPv6 to Neon doesn't route there, and
  asyncpg burns its 60 s budget on three unreachable v6 addresses before ever
  trying the working v4 ones. Worked around per-process (force `AF_INET`), not
  in app code — the deployed backend reaches Neon over IPv4 fine. 25 trails in.
- **Then the real problem (DECISIONS 020):** `api.open-meteo.com` refuses
  Render's shared outbound IP — instantly, every time, while geocoding and the
  ERA5 archive (different hosts, separate buckets) work from the same
  container. The identical requests succeed from a residential IP. Free-tier
  IP rate limiting, arriving pre-exhausted by other tenants.
- **Three fixes, all verified:**
  1. `_raise_for_status()` logs upstream status + body before raising, and
     `main.py` configures the root logger (uvicorn leaves it alone) — the app
     was previously undebuggable on a host with no shell. Demonstrated against
     a real Open-Meteo 400.
  2. Real `User-Agent` on the shared httpx client. `python-httpx/x.y` from a
     datacenter IP looks like a scraper; we already knew this from Overpass and
     hadn't generalised it. Plausible root-cause fix, not yet confirmed live.
  3. **Stale-cache fallback**: the cache lookup no longer filters on
     `expires_at`, so an expired row survives as a fallback. Upstream refusal +
     any cached payload → 200 with `stale=True` instead of 502. No cache at all
     still 502s — inventing weather is not a fallback (DECISIONS 020).
- **`stale` is surfaced, not swallowed.** New `stale` + `fetched_at` on
  `ForecastResponse`, and `StaleForecastBanner` tells the user which timestamp
  the data is from and to check conditions before setting out. A hiking-safety
  app showing yesterday's numbers as today's is worse than showing an error.
  Browser-verified in both languages (RO/EN, localized timestamps), console
  clean, eslint + tsc clean.
- **+4 tests (111 total)**: stale fallback on 429, stale fallback on network
  error, no-cache still 502s, fresh fetch never flagged stale.
- **`app/seeds/warm_cache.py`** — fills the production cache from a laptop via
  the app's own `get_forecasts_bulk`, so keys match exactly. Warmed 48 points
  (all trailheads/summits + the map's default view) at a 24 h TTL, which is
  what makes the live site work right now.
- **Follow-up, same day — map clicks fixed by region warming.** Deployed the
  above; confirmed the new code is live (`stale`/`fetched_at` present) and that
  **the User-Agent fix did NOT work** — Open-Meteo still refuses Render.
  - The new logging immediately paid for itself: the exact upstream reason is
    `HTTP 429 "Minutely API request limit exceeded"`. So it is a *shared
    minutely quota*, permanently saturated by other Render tenants — not a
    permanent ban. That also means it may intermittently succeed.
  - Warming a region turned out to be far cheaper than the earlier estimate:
    **~4.7 kB per cell**, 332 cells in 15 s. All 8 massifs = 3,057 cells = 27 MB
    of Neon's 500 MB. `--box` and `--regions` added to `warm_cache.py`, stepping
    on the exact 0.01° grid `_cache_key` rounds to, so any click inside a warmed
    box hits a warmed entry. Verified: one click per massif, all HTTP 200 on the
    live site.
  - **Pacing was learned the hard way:** firing 8 boxes back to back tripped
    Open-Meteo's *minutely* limit on Marius' own connection. The warmer now
    sleeps 2.5 s between batches (~480 points/min) and backs off 65 s on a 429.
    It also skips already-fresh cells up front, so a re-run before a demo takes
    3 s instead of 6 minutes of sleeping.
- **RESOLVED, same day — forecast calls now leave through Vercel.** Open-Meteo
  accepts Vercel's edge (5/5 full 7-day requests and a 20-point bulk call, all
  200 in ~70 ms) while refusing Render. `frontend/vercel.json` proxies
  `/upstream/open-meteo/*` to Open-Meteo and `OPEN_METEO_BASE_URL` (set in
  `render.yaml`) points the backend at it. **Zero application code changed** —
  the base URL was always configuration, which is the payoff for not
  hard-coding it. Trade-offs in DECISIONS 020: the backend now depends on the
  frontend's domain, and that path is an unauthenticated proxy. Archive and
  geocoding stay direct (separate quotas, still fine); standby rewrites exist
  for them.
- **Cache warming is now insurance, not the mechanism.** Still worth running
  before a demo — it covers Vercel or Open-Meteo having a bad day — but
  forecasts work everywhere without it.

### 2026-08-10 — Deployment prep (code side complete, verified in Docker)

Audited the deploy path before touching anything; found six blockers, fixed
five in code and documented the sixth.

- **Cookie topology (DECISIONS 017).** `SameSite=Lax` is hardcoded, so a
  Vercel-frontend/Railway-backend split would have made every API call
  cross-site: login 200s, then every authenticated request 401s, silently.
  Chose a **Vercel rewrite** (`frontend/vercel.json`, `/api/:path*` → Railway)
  over relaxing to `SameSite=None`, so requests stay same-origin and the
  cookies stay first-party. **Zero backend code changed** — the stricter cookie
  attribute survives, and Safari ITP / Brave can't break login.
  Guard-rail: `frontend/.env.production` pins `VITE_API_URL=/api/v1`, because
  overriding it in the Vercel dashboard silently reintroduces the bug.
- **Managed-Postgres URLs (DECISIONS 018).** Neon's
  `postgresql://…?sslmode=require` breaks twice — wrong dialect (reaches for
  psycopg2) and `sslmode` is a libpq param asyncpg rejects. New pure
  `normalize_database_url()` in `core/config.py` + `Settings.sqlalchemy_url` /
  `.sqlalchemy_connect_args`; `db/session.py` and `alembic/env.py` both go
  through them. Engine also gained `pool_pre_ping` + `pool_recycle=280` for
  free-tier idle disconnects. **+14 hand-written tests** (107 total).
- **Dockerfile rebuilt.** Was installing `.[dev]` (pytest in prod), hardcoding
  port 8000 while Railway injects `$PORT`, and never running migrations.
  Now: dependency layer cached separately from code, no compiler toolchain
  (all deps have cp312 wheels — saved ~300 MB), non-root user, `$PORT`, and
  `alembic upgrade head` in the start command (Railway has no release phase).
  **386 MB** image.
- **Added `backend/.dockerignore`.** Docker does not read `.gitignore`, so
  `COPY . .` was shipping `backend/venv/` and would bake a `.env` into a layer.
- **`pyproject.toml`:** explicit `[build-system]` + `packages.find` — setuptools
  auto-discovery saw `app/` and `alembic/` and refused to guess, which broke
  the non-editable install. (Found by building, not by reading.)
- **Verified in Docker, not just theorised:** built the image, ran it against
  the local DB with a deliberately libpq-style `postgresql://` URL to exercise
  the normalization → migrations applied, server booted, `/health` ok, RO
  forecast returned "Înnorat", login set both cookies, and authed
  `/profile` + `/recommendations` round-tripped. Frontend `npm run build`
  clean; confirmed the bundle bakes `baseURL:"/api/v1"` and no `localhost`.
- **Docs:** new `docs/DEPLOYMENT.md` runbook (provider steps, env-var table,
  post-deploy checklist incl. the browser cookie tests, accepted gaps);
  DECISIONS 017 + 018; `.env.example` production notes; README status/roadmap
  refreshed (it still advertised Romanian UI and the profile editor as todo).
- **Not done, deliberately:** the three provider steps need Marius' accounts.
  Pre-existing ruff `I001` in `alembic/env.py` left alone (unrelated to this
  change, would muddy the commit split).

**Same session — retargeted to a $0 stack (DECISIONS 019).** Marius' goal is an
exam demo in September 2026, not traffic, so cost beat convenience.

- Priced it out: the frontend was never the cost (Vercel Hobby and Netlify Free
  are both $0). **Railway** was — its free tier is gone in practice ($1/month of
  credits ≈ six days of a 0.5 GB container), Hobby is a $5/month minimum. Swapped
  it for **Render's free instance type**: $0, Docker-native, 750 instance-hours.
- **Counter-intuitive finding, documented so it isn't re-litigated:** Netlify's
  free tier is now the *more* restrictive of the two frontends — credit-based,
  15 credits per production deploy out of 300/month ≈ 20 deploys, shared with
  bandwidth, project pauses when exhausted (Vercel: 100/day). Netlify's proxy
  also times out ~30 s vs Vercel's documented 120 s. Stayed on Vercel.
- Added `render.yaml` (Blueprint: docker runtime, free plan, frankfurt,
  `/health` check, `JWT_SECRET` via `generateValue` so the short dev secret can
  never leak in). Verified the exact build Render will run —
  `docker build -f ./backend/Dockerfile ./backend` from the repo root — because
  `dockerfilePath`/`dockerContext` resolve from the repo root, not the service
  root.
- **Render free has no shell**, so trail seeding moved to "run it from the
  laptop against the Neon URL" — which only works because DECISIONS 018 makes
  the app swallow a provider connection string verbatim.
- Accepted: the backend sleeps after 15 min idle, ~1 min cold start. Handled
  procedurally (warm the app before presenting), not with a keep-alive hack.
- Dockerfile comments de-Railway'd; nothing host-specific is in the image, so
  moving hosts stays a config change. `vercel.json` destination now
  `REPLACE-ME.onrender.com`. DEPLOYMENT.md rewritten with a cost table and the
  cold-start warning; README infra/roadmap updated.

### 2026-07-15 — Romanian i18n: frontend chrome pass (feature complete)
- Wired `useTranslation` through every remaining component: AppShell (done
  earlier), ForecastPage, DayCard, ScoreBadge, InstabilityBanner, HourlyChart,
  SearchBox, TrailsPanel, SavedPanel, RecommendPanel, PackingPanel,
  ProfileDialog, AuthModal, and the shared Dialog close button.
- `en.json`/`ro.json` rebuilt into a real key structure (common/header/auth/
  search/forecast/score/instability/chart/trails/saved/recommend/packing/
  profile), kept key-for-key in sync; profile level names live as translated
  arrays via `returnObjects`.
- Weekday names now from `Intl.DateTimeFormat(locale, {weekday:"short"})` —
  no hand-kept table. Score-label enum translated for display through
  `score.label.*` while `SCORE_STYLES`/`SCORE_DOT` still key off the English
  enum (DECISIONS 016). HourlyChart tooltip picks its unit by series
  `dataKey`, not the now-translated legend name.
- Verified in browser: default RO shows fully-Romanian chrome + weekdays +
  labels + auth dialog; EN toggle flips everything (chrome + server text)
  with no stale flash; console clean; eslint + tsc clean.
- Only English left: the AI packing plan text (AI on hold) — noted in NEXT UP.

### 2026-07-15 — Romanian i18n: backend localization + language toggle
- **Backend (DECISIONS 016):** new `app/i18n` package — EN+RO message tables
  (`messages.py`), `t(key, lang, **params)`, `describe_weather(code, lang)`,
  `resolve_lang`/`get_lang` (Accept-Language → en/ro, header-absent default
  `en`). `scoring.py` refactored to return a message key + params (logic
  unchanged); forecast/recommend/climatology endpoints thread `lang`. English
  output is byte-identical, so all prior tests stayed green.
- **Frontend:** axios request interceptor sends `Accept-Language` from the live
  `i18n.language`; i18n default RO (localStorage-only detection, no browser
  auto-switch); `forecast`/`climatology`/`recommendations` query keys include
  the language so a toggle refetches cleanly (both cached, no stale flash);
  `LanguageToggle` (RO/EN segmented) in the header; `AppShell` strings + `<html
  lang>` synced. First chrome example done.
- **Tests:** +18 (93 total). New `test_i18n.py` (resolve_lang/t/describe_weather
  incl. fallbacks); RO reason cases in `test_scoring.py`; Accept-Language
  round-trip + English-default cases in `test_forecast.py`.
- **Verified live:** backend curl RO="Averse de ploaie" / EN="Rain showers";
  browser default RO, toggle → EN refetches all server text, console clean,
  eslint + tsc clean.
- **Remaining (NEXT UP #1):** translate the rest of the component chrome +
  score-label enum display map.

### 2026-07-14 — Profile UI (open item #1 done)
- `ProfileDialog` (`frontend/src/features/profile/`): display name, 1–5
  pickers for experience + max difficulty (same scale as trail dots, worded),
  home location via pick-on-map (explicit-null PATCH to clear), max distance
  km. Backend `PATCH /profile` unchanged.
- Home picking: "Choose on map" hides the dialog (new `hidden` prop on
  `Dialog` — display-none without unmount, so unsaved edits survive), shows
  a hint pill, and the next map click becomes home and reopens the dialog
  without moving the forecast pin. Replaced a v1 "copy current pin" button
  Marius immediately tripped over (modal covered the map it needed input
  from) — DECISIONS 015.
- Trigger button sits on the map overlay next to Saved (not the header)
  because home picking happens on the map — DECISIONS 015.
- Saving writes the PATCH response into the `["profile"]` cache and
  invalidates `["recommendations"]` (rankings derive from the profile).
- Fix: logout now removes user-scoped query caches (saved-locations,
  profile, recommendations) — with 5-min staleTime the next account signing
  in on the same browser could briefly see the previous user's data.
- Verified in browser (demo account): save → PATCH 200 → reopen shows
  persisted values → Best trails shows home distances, −8/−16 experience
  penalties, "11 trails hidden by your profile limits". eslint + tsc clean.
- Marius' same-day working-tree tweaks (Trails button styling, commented-out
  score dot / cached label, README + DECISIONS edits) left untouched.

### 2026-07-14 — Docs pass
- Created this file; refreshed README (status, roadmap, layout, testing) and
  DECISIONS.md (013 resolved, 012 local-LLM addendum, new 014).

### 2026-07-12 — Personalised recommendations (open item "Day 13" done early)
- `GET /api/v1/recommendations?date&limit` (auth): profile + trails + ONE bulk
  Open-Meteo call → `score_day` at each summit → pure `rank_trails()`
  (services/recommend.py). Design + constants: DECISIONS 014.
- `get_forecasts_bulk()` in services/openmeteo.py — multi-coordinate fetch
  sharing the per-grid-cell cache with the map view.
- Frontend: "Best trails" button in forecast strip header → RecommendPanel
  dialog (rank, score badge, penalty breakdown, "N hidden by profile
  limits"); click flies to trailhead. Ranks the selected day, default today.
- 10 new tests (75 total). Verified live: storm day ranked Retezat (67) over
  Ciucaș (27); fly-to landed on the corrected Cârnic trailhead.
- AI put ON HOLD; Ollama fallback designed only (DECISIONS 012 addendum).
- Commit: `7a7797a`.

### 2026-07-10/11 — Trail data verification (DECISIONS 013 resolved)
- All 25 trails checked against OSM (Overpass, bbox-around-draft queries).
  Coordinates/summit elevations corrected — worst drafts: Voina trailhead
  12 km off, Sâmbăta 5.6 km, Păpușa summit 3.6 km, Urlea in the wrong valley.
- Distance/duration standardised to one-way estimates; provenance + known
  conflicts documented in the seed docstring.
- Seeder `--update` mode (default stays insert-only); trail tests now derive
  expectations from `TRAILS` instead of hardcoding; +1 test (65 total).
- Commit: `7ff66d2`.

### 2026-07-05 — Days 5–8 compressed (three commits, one long day)
- **Auth hardened** (`d79afd5`, `ac1cdb3`): two-token scheme fixed (15-min JWT
  access + 30-day DB refresh, DECISIONS 007/008), silent-refresh axios
  interceptor, saved locations CRUD (PostGIS points, 100/user), light-stone
  UI redesign, README rewrite + MIT license, dead code deleted.
- **Hourly chart + chunk split**: Recharts ComposedChart lazy-loaded (~400 kB
  chunk off first paint), `ForecastResponse.hours`, cache-key `days` bugfix.
- **Climatology** (DECISIONS 011): ERA5 10-yr ISO-week aggregation
  (`services/climatology.py`), `/api/v1/climatology`, amber InstabilityBanner.
- **Trails + AI groundwork** (`92c32a4`, DECISIONS 012/013): 25-trail seed +
  public endpoints + TrailsPanel; `services/ai.py` (Claude structured
  outputs, optional via key, 503 path verified); collapsible forecast bar;
  responsive pass (375px–1920px). 64 tests.

### 2026-06-23 — Day 1: foundation
- Scaffold (`9c9fdf3`): FastAPI + SQLAlchemy async + Alembic + PostGIS compose,
  React+Vite+Tailwind, CI. DECISIONS log started (001–006).
- Working scored forecast API + Open-Meteo Postgres cache; basic frontend
  (map + 7-day strip) tied to backend; demo account seeder (`16eb72a`).

### 2026-06-22 — Day 0: project setup, first API experiments (`b14e797`, `e54880c`).
