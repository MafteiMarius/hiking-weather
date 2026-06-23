# HikeCast

A weather companion for hiking in the Romanian Carpathians.

---

## Setting up on a new Linux machine

### Prerequisites

```bash
# Verify these are installed before starting
git --version          # any recent version
docker --version       # 24+ recommended
docker compose version # built-in plugin, not docker-compose
python3 --version      # 3.12 or 3.14
node --version         # 20+
npm --version          # 10+
```

If Python 3.12+ is missing on Ubuntu/Debian:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update && sudo apt install python3.12 python3.12-venv python3.12-dev
```

### 1 — Clone and configure

```bash
git clone https://github.com/MafteiMarius/hiking-weather.git
cd hiking-weather
cp .env.example .env
```

Open `.env` and replace the JWT secret with a real one (the placeholder is too short and triggers a warning):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# paste the output as JWT_SECRET= in .env
```

Leave everything else as-is — the defaults match the Docker Compose setup.

### 2 — Start the database

```bash
docker compose up -d db
# wait ~5 seconds for Postgres to be ready
docker compose logs db --tail 5   # should end with "database system is ready to accept connections"
```

### 3 — Backend

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"          # installs app + test deps from pyproject.toml
```

Run the migration and create the test database:

```bash
alembic upgrade head

docker exec hiking-weather-db-1 psql -U hikecast -c "CREATE DATABASE hikecast_test;"
docker exec hiking-weather-db-1 psql -U hikecast -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" hikecast_test
docker exec hiking-weather-db-1 psql -U hikecast -c "CREATE EXTENSION IF NOT EXISTS postgis;" hikecast_test
```

Verify everything works:

```bash
TEST_DATABASE_URL="postgresql+asyncpg://hikecast:hikecast@localhost:5432/hikecast_test" \
  pytest tests/ -v
# expected: 39 passed
```

Start the dev server:

```bash
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

### 4 — Frontend

```bash
cd ../frontend        # from repo root: cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

### 5 — Daily workflow

Each session only needs:

```bash
# Terminal 1 (backend)
cd hiking-weather/backend && source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 (frontend)
cd hiking-weather/frontend
npm run dev
```

Docker Compose keeps the database running between reboots. If it stopped:

```bash
docker compose up -d db
```

---

Most weather apps tell you it will be 18 degrees and partly cloudy. That is
not what you need to know at 4 AM before driving to a trailhead. HikeCast
answers the questions that actually matter on a mountain: are the ridge gusts
safe, is the freezing level above the summit, is there enough daylight, and
is this spot historically nasty for this week of the year.

Built as a learning project and as a tool I use on real trips.

## What it does

- **7-day forecast** for any point, with an hourly view.
- **Safety score** from 0 to 100 per day, with a verdict (go, caution, no-go)
  and a short list of reasons that explain it.
- **Historical instability warning** when a location has a track record of bad
  weather this week of the year, based on 10 years of reanalysis data.
- **Trail catalogue** of 25 curated routes in Bucegi, Piatra Craiului,
  Fagaras, Retezat, Apuseni, Ceahlau, Ciucas, and Iezer-Papusa.
- **Personalised recommendations** based on your home location, experience
  level, and the upcoming week's weather.
- **Save and revisit** your favourite spots.
- **Works offline.** Installable as a PWA. The last forecast you viewed is
  cached for the trail.
- **Romanian and English UI.**

## Try it locally

You need Docker Desktop. That is it.

```bash
git clone https://github.com/USERNAME/hikecast.git
cd hikecast
cp .env.example .env
docker compose up --build
```

After about a minute:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

A demo account is seeded for you:

```
email:    demo@hikecast.app
password: HikeCast2026!
```

It comes pre-loaded with three saved locations (Varful Omu, Cascada 7 Scari,
Negoiu) so every feature works on first launch.

## How it works

The frontend never calls Open-Meteo directly. The backend fetches once,
caches in Postgres for 30 minutes, enriches the response with the safety
score and historical context, and serves a single clean payload.

Full architecture diagram and request lifecycle: `docs/architecture.md`.

## Stack

**Backend.** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2,
PostgreSQL 16 with PostGIS 3.4, fastapi-users, httpx, APScheduler.

**Frontend.** React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui, React
Router v7, TanStack Query v5, Leaflet with OpenTopoMap tiles, Recharts,
react-i18next, vite-plugin-pwa.

**Infra.** Docker Compose locally. In production: Neon for Postgres, Railway
for the backend, Vercel for the frontend.

## The safety score

Each day's score starts at 100 and loses points for conditions that matter on
a mountain:

```
- precipitation       up to 35 off
- wind gusts          up to 25 off
- thunderstorm (CAPE) up to 25 off
- cold                up to 15 off
- visibility          up to 10 off
- UV                  up to  5 off
```

| Score | Verdict |
| --- | --- |
| 70 - 100 | go |
| 40 - 69 | caution |
| 0 - 39 | no-go |

Full formula and reasoning: `docs/decisions/0003-safety-score-weights.md`.
Implementation: `backend/app/services/scoring.py`.

## Historical instability

For every location you view, the app lazily pulls 10 years of ERA5 reanalysis
data from Open-Meteo's archive, aggregates over the same ISO week of the
year, and stores six metrics (thunderstorm frequency, precipitation day
frequency, average min and max temperature, 90th percentile wind gust,
volatility index).

A warning is shown when the area has a clear pattern of trouble for this
time of year, even if today's forecast looks fine. Results are cached for
30 days per location.

## Project layout

```
backend/
  app/
    api/v1/        routes
    services/      openmeteo, scoring, climatology, recommend
    db/            models
    jobs/          scheduled tasks
    seeds/         trail data
  alembic/
  tests/
frontend/
  src/
    features/      auth, forecast, map, recommendations, saved
    components/
    lib/
    pages/
    i18n/
docs/
docker-compose.yml
.env.example
```

## Testing

```bash
cd backend && pytest
cd frontend && npm test
```

Critical paths covered: the safety score, the recommendation ranker, auth
flow, Open-Meteo client retry and cache, climatology aggregation.

## Roadmap

Not in v1, planned for later:

- ANM nowcasting alerts overlay (yellow, orange, red).
- Multi-point forecasts along a trail.
- GPX import and export.
- Email digest with the best hiking day of the weekend.
- Google sign-in.
- Bear-activity heatmap.

## Credits

- Weather and archive data: [Open-Meteo](https://open-meteo.com/), CC BY 4.0.
- Map tiles: https://opentopomap.org/, CC BY-SA; data
  (c) OpenStreetMap contributors.
- UI: https://ui.shadcn.com/. Icons: https://lucide.dev/.
  Charts: https://recharts.org/.

## Disclaimer

Forecasts are for planning only. They are not a substitute for professional
mountain advice. Always check [ANM](https://www.meteoromania.ro/) warnings
and https://salvamontromania.ro/ before going into the mountains.

## License

MIT. See ./LICENSE.
