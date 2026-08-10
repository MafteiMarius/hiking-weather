"""Pre-populate the forecast cache from a machine Open-Meteo will talk to.

Why this exists
---------------
Open-Meteo's free API rate-limits by IP, and shared hosting IPs (Render's
free tier among them) get rejected regardless of how little traffic *we* send.
The backend therefore cannot always fill its own cache. This script fills it
from somewhere that can — a laptop on a normal connection — writing straight
to the production database.

It deliberately calls the application's own `get_forecasts_bulk`, so entries
land under exactly the cache keys the API reads. Anything else would warm a
cache nobody looks in.

Usage
-----
    # from backend/, with DATABASE_URL pointing at production
    python -m app.seeds.warm_cache
    python -m app.seeds.warm_cache 45.36,25.46 45.44,25.45   # extra points
    python -m app.seeds.warm_cache --days 1 --ipv4

Make the entries outlive the default 30-minute TTL by setting it for the run:

    FORECAST_CACHE_TTL_MINUTES=1440 python -m app.seeds.warm_cache

The TTL is read from settings when the row is written, so a long value here
keeps the demo working for a day even if the backend never reaches Open-Meteo.
Past that, the stale-cache fallback in `get_forecast` takes over and the app
serves the same data flagged as stale rather than failing.

`--ipv4` forces IPv4 name resolution for this process. Some networks resolve
Neon's AAAA records but cannot route IPv6, and asyncpg then burns its whole
connect timeout on unreachable addresses before ever trying IPv4. This is a
local-network workaround and is deliberately confined to this script.
"""
import asyncio
import socket
import sys

import httpx

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.seeds.trails import TRAILS
from app.services.openmeteo import get_forecasts_bulk

# Open-Meteo takes many coordinates per request, but a URL with 50 pairs is
# both unwieldy and more likely to trip a limit. Batches keep each request
# ordinary-looking.
_BATCH = 20

_USER_AGENT = "HikeCast/1.0 (+https://hiking-weather.vercel.app)"


def _force_ipv4() -> None:
    _orig = socket.getaddrinfo

    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):  # type: ignore[no-untyped-def] # noqa: A002
        return _orig(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = ipv4_only  # type: ignore[assignment]


def _trail_points() -> list[tuple[float, float]]:
    """Every trailhead and summit in the catalogue.

    These are what the trail list and the recommendations ranking ask for, so
    warming them covers both features. `get_forecasts_bulk` dedups by grid
    cell, so nearby pairs cost nothing extra.
    """
    points: list[tuple[float, float]] = []
    for t in TRAILS:
        points.append(t["start"])
        if t.get("summit"):
            points.append(t["summit"])
    return points


def _parse_args(argv: list[str]) -> tuple[int, bool, list[tuple[float, float]]]:
    days, ipv4, extra = 7, False, []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--ipv4":
            ipv4 = True
        elif arg == "--days":
            i += 1
            days = int(argv[i])
        else:
            lat, lng = arg.split(",")
            extra.append((float(lat), float(lng)))
        i += 1
    return days, ipv4, extra


async def warm(days: int, extra: list[tuple[float, float]]) -> int:
    points = _trail_points() + extra
    settings = get_settings()
    warmed = 0

    async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as http:
        async with AsyncSessionLocal() as session:
            for start in range(0, len(points), _BATCH):
                batch = points[start:start + _BATCH]
                await get_forecasts_bulk(batch, days, http, session)
                warmed += len(batch)
                print(f"  warmed {warmed}/{len(points)} points")

    print(
        f"\nDone: {len(points)} points at days={days}, "
        f"TTL {settings.forecast_cache_ttl_minutes} min."
    )
    if settings.forecast_cache_ttl_minutes < 120:
        print(
            "NOTE: that TTL is short for a demo. Re-run with "
            "FORECAST_CACHE_TTL_MINUTES=1440 to keep entries fresh for a day."
        )
    return len(points)


def main() -> None:
    days, ipv4, extra = _parse_args(sys.argv[1:])
    if ipv4:
        _force_ipv4()
        print("Forcing IPv4 resolution for this process.")
    asyncio.run(warm(days, extra))


if __name__ == "__main__":
    main()
