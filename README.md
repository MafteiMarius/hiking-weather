# HikeCast

A weather companion for hiking in the Romanian Carpathians.

Most weather apps tell you it will be 18 degrees and partly cloudy. That is
not what you need to know at 4 AM before driving to a trailhead. HikeCast
answers the questions that actually matter on a mountain: are the ridge gusts
safe, will a thunderstorm build over the ridge, is it cold enough up there for
ice — and turns the answer into a single go / no-go score per day.

Built as a learning project and as a tool I use on real trips.

## Status

Work in progress. What works today:

- **Scored 7-day forecast** for any point on the map. Each day gets a safety
  score from 0 to 100, a label (Excellent → Dangerous), and the main reason
  behind it.
- **Hourly drill-down** — click a day card to see when in the day the risk
  concentrates: temperature, rain, and wind gusts hour by hour.
- **Interactive topo map** (OpenTopoMap tiles) — click anywhere or search a
  place by name to get its forecast and elevation.
- **Accounts** — register / sign in with httpOnly-cookie auth (short-lived
  access JWT + revocable DB-backed refresh token, silent refresh in the UI).
- **Saved locations** — bookmark your spots (stored as PostGIS points) and
  jump back to them from any device.
- **Historical instability warning** — 10 years of ERA5 reanalysis data,
  aggregated over the same ISO week of the year, flag locations with a track
  record of bad weather even when the forecast looks fine.
- **Trail catalogue** — 25 curated routes in Bucegi, Piatra Craiului, Făgăraș,
  Retezat, Apuseni, Ceahlău, Ciucaș, and Iezer-Păpușa; pick one to fly the map
  to its trailhead. Coordinates and summit elevations are verified against
  OpenStreetMap; distances and durations are one-way planning estimates.
- **Personalised recommendations** — signed-in users get a "Best trails"
  ranking for any forecast day: the safety score at each trail's summit,
  adjusted by their profile (experience level, difficulty cap, distance from
  home), with the penalty breakdown shown so the ranking is never a black box.
- **AI packing advice** *(optional)* — with an Anthropic API key configured,
  signed-in users get a Claude-generated equipment list for the selected day,
  grounded in the hourly forecast and the location's historical pattern.
- **Forecast caching** — the backend fetches Open-Meteo once per ~1 km grid
  cell and caches the payload in Postgres for 30 minutes; the frontend never
  talks to Open-Meteo directly.
- **Installable PWA scaffold** — map tiles and the last forecasts are cached
  by a service worker.

Planned next (see Roadmap): Romanian UI, production deployment.

## Setup guide

### Prerequisites

| Tool | Version | Check |
| --- | --- | --- |
| Git | any recent | `git --version` |
| Docker + Compose | 24+ | `docker compose version` |
| Python | 3.12+ (3.14 works) | `python --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |

### 1 — Clone and configure

```bash
git clone https://github.com/MafteiMarius/hiking-weather.git
cd hiking-weather
cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and replace the JWT secret with a real one (the placeholder is
too short):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# paste the output as JWT_SECRET= in .env
```

Leave everything else as-is — the defaults match the Docker Compose setup.

### 2 — Start the database

```bash
docker compose up -d db
docker compose logs db --tail 5   # wait for "ready to accept connections"
```

### 3 — Backend

Linux / macOS:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Windows (PowerShell):

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Apply the migrations, create the test database, and seed the demo account:

```bash
alembic upgrade head

docker exec hiking-weather-db-1 psql -U hikecast -c "CREATE DATABASE hikecast_test;"
docker exec hiking-weather-db-1 psql -U hikecast -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" hikecast_test
docker exec hiking-weather-db-1 psql -U hikecast -c "CREATE EXTENSION IF NOT EXISTS postgis;" hikecast_test

python -m app.seeds.demo
python -m app.seeds.trails
```

Verify everything works, then start the dev server:

```bash
# Linux / macOS
TEST_DATABASE_URL="postgresql+asyncpg://hikecast:hikecast@localhost:5432/hikecast_test" pytest tests/ -v

# Windows (PowerShell)
$env:TEST_DATABASE_URL="postgresql+asyncpg://hikecast:hikecast@localhost:5432/hikecast_test"; pytest tests/ -v

uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

### 4 — Frontend

```bash
cd ../frontend
npm install
npm run dev
# App at http://localhost:5173
```

Sign in with the demo account seeded above:

```
email:    demo@hikecast.app
password: HikeCast2026!
```

### 5 — Daily workflow

```bash
# Terminal 1 (backend)
cd backend && source venv/bin/activate    # Windows: .\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminal 2 (frontend)
cd frontend && npm run dev
```

Docker Compose keeps the database running between reboots. If it stopped:
`docker compose up -d db`.

## How it works

The frontend never calls Open-Meteo directly. The backend fetches once per
~1 km grid cell (coordinates rounded to 2 decimals), stores the raw payload
in Postgres (JSONB) for 30 minutes, scores each day, and serves a single
clean payload. Storing the raw payload means the scoring weights can change
without invalidating the cache.

Auth uses two tokens: a 15-minute JWT in an httpOnly cookie for requests,
and an opaque 30-day refresh token stored in the database so logout can
revoke it with a hard `DELETE`. The frontend refreshes silently on 401.
Details and trade-offs: `docs/decisions/DECISIONS.md`.

## The safety score

Each day starts at 100 and loses points for conditions that matter on a
mountain (implementation: `backend/app/services/scoring.py`):

- **Weather code** — thunderstorm −55 to −65, heavy rain/snow −40,
  fog −30 (navigation risk above treeline), lighter precipitation less.
- **Wind gusts** — over 90 km/h −60 (can knock you off a ridge),
  over 60 km/h −40, over 45 km/h −25, over 30 km/h −10.
- **Precipitation sum** — up to −25 above 20 mm.
- **Temperature** — extreme cold (< −15 °C) −30, extreme heat (> 38 °C) −25,
  with milder steps between.

| Score | Label |
| --- | --- |
| 85–100 | Excellent |
| 70–84 | Good |
| 50–69 | Fair |
| 30–49 | Poor |
| 0–29 | Dangerous |

The response also carries the single worst factor as a human-readable reason
("Thunderstorm — stay off exposed ridges").

## Stack

**Backend.** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2,
PostgreSQL 16 with PostGIS 3.4, fastapi-users (Argon2id), httpx + tenacity.

**Frontend.** React 19, Vite, TypeScript, Tailwind CSS v4, React Router v7,
TanStack Query v5, react-leaflet with OpenTopoMap tiles, lucide-react,
vite-plugin-pwa.

**Infra.** Docker Compose locally. Planned production: Neon for Postgres,
Railway for the backend, Vercel for the frontend.

## Project layout

```
backend/
  app/
    api/v1/        routes (auth, profile, forecast, geocode, elevation, locations, climatology, trails, recommendations, ai)
    core/          config, auth wiring, refresh-token helpers
    services/      openmeteo client + cache, scoring, climatology, recommend (trail ranking), ai (Claude)
    db/            models, session
    seeds/         demo account, trail catalogue
  alembic/         migrations
  tests/           pytest (scoring, forecast + cache, auth flow, saved locations)
frontend/
  src/
    components/    app shell, auth modal, search box, ui primitives
    features/      auth hooks, forecast hooks + day cards + hourly chart, saved locations, trails + recommendations
    pages/         forecast page (map + 7-day strip)
    lib/           axios client with silent token refresh
docs/decisions/    architecture decision log
docker-compose.yml
```

## Testing

```bash
cd backend && pytest        # needs the db container + hikecast_test database
```

Covered: the safety score (pure unit tests), the Open-Meteo client with
cache-hit proof (HTTP mocked with respx), the full auth flow, saved
locations (incl. ownership), the climatology aggregation math, the trail
seeder (idempotent + update mode), and the recommendation ranking
(hand-computed penalties, bulk-fetch call count, profile filters).

## Roadmap

Progress and per-session details: `docs/CHANGELOG.md`.

- Profile UI for home location (used by recommendations; currently only
  settable via the API).
- Romanian UI (i18n is wired, strings not yet translated).
- Production deployment: Neon (Postgres), Railway (backend), Vercel (frontend).
- AI packing advice live test, or a local-LLM (Ollama) fallback so it works
  without an API key (design in `docs/decisions/DECISIONS.md`, 012).
- ANM nowcasting alerts overlay, GPX import, multi-point trail forecasts.

## Credits

- Weather data: [Open-Meteo](https://open-meteo.com/), CC BY 4.0.
- Map tiles: [OpenTopoMap](https://opentopomap.org/), CC BY-SA; data
  © OpenStreetMap contributors.
- Icons: [Lucide](https://lucide.dev/). Charts: [Recharts](https://recharts.org/).

## Disclaimer

Forecasts are for planning only. They are not a substitute for professional
mountain advice. Always check [ANM](https://www.meteoromania.ro/) warnings
and [Salvamont](https://salvamontromania.ro/) before going into the mountains.

## License

MIT — see [LICENSE](LICENSE).
