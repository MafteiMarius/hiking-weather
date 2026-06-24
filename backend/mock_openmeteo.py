"""Tiny mock for Open-Meteo APIs — used when the real APIs are blocked.

Runs on port 8001. Set in .env:
  OPEN_METEO_BASE_URL=http://localhost:8001/v1
  OPEN_METEO_GEOCODE_URL=http://localhost:8001/v1
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import math

# 7-day weather cycle: good → decent → stormy → recovering → great
_DAILY_CODES    = [1, 2,  3,  95, 61,  2,  0]
_TEMP_MAX       = [24, 22, 18, 16, 19, 23, 26]
_TEMP_MIN       = [12, 11,  9,  8, 10, 12, 14]
_APPARENT_MIN   = [10,  9,  7,  5,  8, 10, 13]
_PRECIP_SUM     = [0.0, 1.2, 5.5, 18.0, 6.0, 0.5, 0.0]
_PRECIP_PROB    = [5,  20,  55,  90,  65,  20,  5]
_WIND_SPEED     = [12, 18, 25, 45, 30, 15, 10]
_WIND_GUSTS     = [22, 30, 42, 75, 52, 28, 18]
_UV_MAX         = [6.0, 5.5, 3.0, 2.0, 4.0, 6.5, 8.0]
_SUNRISE        = ["2026-06-24T05:32", "2026-06-25T05:33", "2026-06-26T05:33",
                   "2026-06-27T05:34", "2026-06-28T05:35", "2026-06-29T05:35",
                   "2026-06-30T05:36"]
_SUNSET         = ["2026-06-24T21:15", "2026-06-25T21:15", "2026-06-26T21:14",
                   "2026-06-27T21:14", "2026-06-28T21:13", "2026-06-29T21:13",
                   "2026-06-30T21:12"]
_DATES          = ["2026-06-24", "2026-06-25", "2026-06-26", "2026-06-27",
                   "2026-06-28", "2026-06-29", "2026-06-30"]

# Hourly CAPE: spikes on storm day (day 3 = index 3, hours 72-95)
_HOURLY_CAPE = []
for day in range(7):
    for hour in range(24):
        if day == 3 and 11 <= hour <= 17:
            _HOURLY_CAPE.append(1400.0)  # high CAPE on storm day
        elif day == 4 and 13 <= hour <= 15:
            _HOURLY_CAPE.append(600.0)   # moderate CAPE recovering
        else:
            _HOURLY_CAPE.append(0.0)

# Hourly visibility: poor on storm day and day after
_HOURLY_VIS = []
for day in range(7):
    for hour in range(24):
        if day == 3:
            _HOURLY_VIS.append(800.0)    # very poor on storm day
        elif day == 4 and 8 <= hour <= 14:
            _HOURLY_VIS.append(3500.0)   # reduced visibility
        else:
            _HOURLY_VIS.append(20000.0)

_HOURLY_TIME = []
for day_offset in range(7):
    for hour in range(24):
        _HOURLY_TIME.append(f"2026-06-{24+day_offset:02d}T{hour:02d}:00")

_GEOCODE_RESULTS = [
    {"id": 683506, "name": "Bucharest", "country": "Romania", "country_code": "RO",
     "latitude": 44.43225, "longitude": 26.10626, "elevation": 91.0},
    {"id": 685761, "name": "Brașov", "country": "Romania", "country_code": "RO",
     "latitude": 45.65169, "longitude": 25.60605, "elevation": 568.0},
    {"id": 666524, "name": "Sinaia", "country": "Romania", "country_code": "RO",
     "latitude": 45.35, "longitude": 25.55, "elevation": 800.0},
    {"id": 671138, "name": "Predeal", "country": "Romania", "country_code": "RO",
     "latitude": 45.50539, "longitude": 25.57717, "elevation": 1033.0},
    {"id": 682100, "name": "Piatra Craiului", "country": "Romania", "country_code": "RO",
     "latitude": 45.51, "longitude": 25.22, "elevation": 2238.0},
]


def _make_forecast(lat: float, lng: float, days: int) -> dict:
    # Rough elevation estimate based on Carpathian region
    elev = 800.0 + abs(math.sin(lat * lng)) * 1400.0

    return {
        "latitude": lat,
        "longitude": lng,
        "elevation": round(elev, 1),
        "timezone": "Europe/Bucharest",
        "timezone_abbreviation": "EEST",
        "utc_offset_seconds": 10800,
        "daily_units": {
            "time": "iso8601",
            "weather_code": "wmo code",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "apparent_temperature_min": "°C",
            "precipitation_sum": "mm",
            "precipitation_probability_max": "%",
            "wind_speed_10m_max": "km/h",
            "wind_gusts_10m_max": "km/h",
            "uv_index_max": "",
            "sunrise": "iso8601",
            "sunset": "iso8601",
        },
        "daily": {
            "time": _DATES[:days],
            "weather_code": _DAILY_CODES[:days],
            "temperature_2m_max": _TEMP_MAX[:days],
            "temperature_2m_min": _TEMP_MIN[:days],
            "apparent_temperature_min": _APPARENT_MIN[:days],
            "precipitation_sum": _PRECIP_SUM[:days],
            "precipitation_probability_max": _PRECIP_PROB[:days],
            "wind_speed_10m_max": _WIND_SPEED[:days],
            "wind_gusts_10m_max": _WIND_GUSTS[:days],
            "uv_index_max": _UV_MAX[:days],
            "sunrise": _SUNRISE[:days],
            "sunset": _SUNSET[:days],
        },
        "hourly": {
            "time": _HOURLY_TIME[:days * 24],
            "cape": _HOURLY_CAPE[:days * 24],
            "visibility": _HOURLY_VIS[:days * 24],
        },
    }


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence default access log
        pass

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        path = parsed.path.rstrip("/")

        if path == "/v1/forecast":
            lat = float(qs.get("latitude", [44.4])[0])
            lng = float(qs.get("longitude", [26.1])[0])
            days = int(qs.get("forecast_days", [7])[0])
            self._json(_make_forecast(lat, lng, min(days, 7)))

        elif path == "/v1/search":
            name = qs.get("name", [""])[0].lower()
            results = [r for r in _GEOCODE_RESULTS
                       if name in r["name"].lower()] or _GEOCODE_RESULTS[:3]
            self._json({"results": results[:5]})

        else:
            self._json({"error": f"unknown path {path}"}, 404)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8001), MockHandler)
    print("Mock Open-Meteo running on http://localhost:8001")
    server.serve_forever()
