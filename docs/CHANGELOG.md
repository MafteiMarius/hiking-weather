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

## CURRENT STATE (updated 2026-07-14)

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

**Quality bar:** 93 backend tests green; frontend `npx eslint src` and
`npx tsc --noEmit` clean. Every feature verified in the browser before done.

**Data caveats:** trail distances/durations are one-way planning estimates,
not GPS tracks (DECISIONS 013). ERA5 undercounts thunderstorms (DECISIONS 011).

---

## NEXT UP (priority order, with pickup context)

1. **Deployment (~Day 16 of the original plan)** — Neon (Postgres+PostGIS),
   Railway (backend; Dockerfile pins Python 3.12, DECISIONS 005), Vercel
   (frontend). Pre-flight: generate a ≥32-byte `JWT_SECRET` (dev one is 26
   bytes — pyjwt warns), run seeds against prod DB, set CORS origins.
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
