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

    # every cell in a bounding box, so clicking anywhere inside it works:
    python -m app.seeds.warm_cache --box 45.30,25.35:45.50,25.65

    # THE PRE-DEMO COMMAND: every massif in the catalogue (~3,000 cells).
    # Already-fresh cells are skipped, so re-running it is cheap.
    python -m app.seeds.warm_cache --regions --ipv4

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
from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ForecastCache
from app.db.session import AsyncSessionLocal
from app.seeds.trails import TRAILS

# _cache_key is private to the service, but this script exists precisely to
# write entries the service will read — it must agree on keys exactly.
from app.services.openmeteo import _cache_key, get_forecasts_bulk

# Open-Meteo takes many coordinates per request, but a URL with 50 pairs is
# both unwieldy and more likely to trip a limit. Batches keep each request
# ordinary-looking.
_BATCH = 20

# Open-Meteo enforces a *minutely* limit (600 weighted calls), and a bulk
# request counts roughly per location — so 20-point batches fired back to back
# blow through it in seconds and earn a 429 for the whole minute. Pausing
# between batches keeps us near 480 points/minute, comfortably under. Learned
# the hard way: warming eight regions in a row rate-limited the developer's own
# connection.
_BATCH_PAUSE_S = 2.5

# When we do get throttled, the limit is per minute, so waiting it out works.
_RATE_LIMIT_WAIT_S = 65
_MAX_RETRIES = 3

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


def _box_points(spec: str) -> list[tuple[float, float]]:
    """Every cache cell inside a "lat1,lng1:lat2,lng2" bounding box.

    Steps in 0.01 degrees because that is exactly what `_cache_key` rounds to —
    warming on any coarser spacing would produce keys no map click ever asks
    for. A click anywhere inside a cell rounds into the entry warmed here, so
    this is what makes arbitrary clicking work in a demo region.

    Note the asymmetry this papers over: our cache cell is ~1 km while
    Open-Meteo's grid is ~11 km, so a box costs far more entries than it does
    distinct weather. Fine for one massif, hopeless for a country.
    """
    corner_a, corner_b = spec.split(":")
    lat1, lng1 = (float(v) for v in corner_a.split(","))
    lat2, lng2 = (float(v) for v in corner_b.split(","))
    lo_lat, hi_lat = sorted((lat1, lat2))
    lo_lng, hi_lng = sorted((lng1, lng2))

    points: list[tuple[float, float]] = []
    lat = round(lo_lat, 2)
    while lat <= hi_lat + 1e-9:
        lng = round(lo_lng, 2)
        while lng <= hi_lng + 1e-9:
            points.append((lat, round(lng, 2)))
            lng = round(lng + 0.01, 2)
        lat = round(lat + 0.01, 2)
    return points


def _region_points() -> list[tuple[float, float]]:
    """Every cell in a padded bounding box around each region in the catalogue.

    This is the pre-demo command: it makes clicking anywhere near any of the
    catalogue's massifs work, not just the trailheads themselves. The padding
    gives room to click around a summit rather than exactly on it.
    """
    boxes: dict[str, list[tuple[float, float]]] = {}
    for t in TRAILS:
        pts = boxes.setdefault(t["region"], [])
        pts.append(t["start"])
        if t.get("summit"):
            pts.append(t["summit"])

    pad = 0.04
    points: list[tuple[float, float]] = []
    for pts in boxes.values():
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        points.extend(
            _box_points(
                f"{min(lats) - pad:.2f},{min(lngs) - pad:.2f}:"
                f"{max(lats) + pad:.2f},{max(lngs) + pad:.2f}"
            )
        )
    return sorted(set(points))


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
        elif arg == "--regions":
            extra.extend(_region_points())
        elif arg == "--box":
            i += 1
            extra.extend(_box_points(argv[i]))
        else:
            lat, lng = arg.split(",")
            extra.append((float(lat), float(lng)))
        i += 1
    return days, ipv4, extra


async def warm(days: int, extra: list[tuple[float, float]]) -> int:
    points = _trail_points() + extra
    settings = get_settings()
    warmed = 0

    # A runaway --box is the easy mistake here: one degree square is 10,000
    # cells and several hundred upstream requests, which is exactly the kind of
    # traffic that gets an IP rate-limited in the first place.
    if len(points) > 5000:
        raise SystemExit(
            f"{len(points)} points is too many for one run - narrow the --box. "
            "A 0.2 x 0.3 degree box (~650 cells) covers a massif; --regions "
            "covers the whole catalogue in about 3,000."
        )
    async with (
        httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as http,
        AsyncSessionLocal() as session,
    ):
        # Drop cells that are already fresh. `get_forecasts_bulk` would skip
        # them anyway, but doing it here means the inter-batch pause only
        # applies to batches that genuinely go upstream — so re-running before
        # a demo costs seconds instead of minutes of sleeping.
        now = datetime.now(UTC)
        keys = {p: _cache_key(p[0], p[1], days) for p in points}
        fresh = set(
            (
                await session.execute(
                    select(ForecastCache.cache_key).where(
                        ForecastCache.cache_key.in_(set(keys.values())),
                        ForecastCache.expires_at > now,
                    )
                )
            ).scalars()
        )
        points = [p for p in points if keys[p] not in fresh]
        if not points:
            print(f"All {len(keys)} cells already fresh - nothing to do.")
            return 0

        minutes = len(points) * _BATCH_PAUSE_S / _BATCH / 60
        print(
            f"{len(fresh)} cells already fresh; warming {len(points)} "
            f"at days={days} (~{minutes:.0f} min) ..."
        )

        for start in range(0, len(points), _BATCH):
            batch = points[start:start + _BATCH]

            for attempt in range(_MAX_RETRIES):
                try:
                    await get_forecasts_bulk(batch, days, http, session)
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 429:
                        raise
                    if attempt == _MAX_RETRIES - 1:
                        raise
                    print(
                        f"  rate-limited, waiting {_RATE_LIMIT_WAIT_S}s "
                        f"(attempt {attempt + 1}/{_MAX_RETRIES})..."
                    )
                    await asyncio.sleep(_RATE_LIMIT_WAIT_S)

            warmed += len(batch)
            print(f"  warmed {warmed}/{len(points)} points")
            if start + _BATCH < len(points):
                await asyncio.sleep(_BATCH_PAUSE_S)

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
