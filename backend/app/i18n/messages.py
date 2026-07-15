"""Translation tables for all server-generated user-facing text.

WHY this lives on the backend at all:
  Weather descriptions, score reasons, and the climatology instability
  sentences are *generated* server-side (some interpolate live numbers), so
  the frontend can't translate them from a static bundle the way it does its
  own chrome. The web UI signals the desired language with an `Accept-Language`
  header; `app.i18n.resolve_lang` maps it to one of SUPPORTED_LANGS.

WHY one flat dict per language instead of gettext/.po:
  ~50 short strings, no pluralisation rules worth the toolchain. A dict keyed
  by a stable code (e.g. "reason.wind.strong") with Python str.format
  placeholders is enough and stays greppable. English is the canonical
  fallback for any key/lang miss — never show a raw key to a user.

Values are Python format templates: numeric placeholders carry their format
spec inline (e.g. "{gusts:.0f}") so the same params dict renders in either
language. Keep the EN and RO tables key-for-key identical.
"""

# WMO weather code → short description. Codes 0–3 are the "no penalty" clear
# range; the rest mirror the penalty table below.
WEATHER_DESC: dict[str, dict[int, str]] = {
    "en": {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Icy fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Heavy rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    },
    "ro": {
        0: "Cer senin",
        1: "Predominant senin",
        2: "Parțial noros",
        3: "Înnorat",
        45: "Ceață",
        48: "Ceață înghețată",
        51: "Burniță ușoară",
        53: "Burniță",
        55: "Burniță densă",
        61: "Ploaie ușoară",
        63: "Ploaie",
        65: "Ploaie abundentă",
        71: "Ninsoare ușoară",
        73: "Ninsoare",
        75: "Ninsoare abundentă",
        77: "Grăunțe de zăpadă",
        80: "Averse de ploaie",
        81: "Averse puternice de ploaie",
        82: "Averse violente de ploaie",
        85: "Averse de ninsoare",
        86: "Averse puternice de ninsoare",
        95: "Furtună",
        96: "Furtună cu grindină",
        99: "Furtună cu grindină puternică",
    },
}

# Score reasons + climatology instability sentences. Keys are stable codes;
# scoring.py and the climatology endpoint build the key + params, this table
# owns the wording. `{...}` placeholders are filled via str.format.
MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # Fallback when nothing penalised the day
        "reason.good": "Conditions look good for hiking",
        # WMO-code reasons (worst-concern wording, may differ from the plain
        # description above — e.g. adds the ridge-safety note)
        "reason.wmo.45": "Fog — navigation risk on ridges",
        "reason.wmo.48": "Icy fog — visibility and ice hazard",
        "reason.wmo.51": "Light drizzle",
        "reason.wmo.53": "Drizzle",
        "reason.wmo.55": "Dense drizzle",
        "reason.wmo.61": "Rain expected",
        "reason.wmo.63": "Moderate rain",
        "reason.wmo.65": "Heavy rain — hypothermia risk",
        "reason.wmo.71": "Light snow",
        "reason.wmo.73": "Snow — slippery terrain",
        "reason.wmo.75": "Heavy snow — trail may be impassable",
        "reason.wmo.77": "Snow grains",
        "reason.wmo.80": "Rain showers",
        "reason.wmo.81": "Heavy rain showers",
        "reason.wmo.82": "Violent rain showers",
        "reason.wmo.85": "Snow showers",
        "reason.wmo.86": "Heavy snow showers",
        "reason.wmo.95": "Thunderstorm — stay off exposed ridges",
        "reason.wmo.96": "Thunderstorm with hail",
        "reason.wmo.99": "Thunderstorm with heavy hail",
        # Wind (param: gusts, km/h)
        "reason.wind.dangerous": "Dangerous gusts ({gusts:.0f} km/h) — do not summit",
        "reason.wind.very_strong": "Very strong gusts ({gusts:.0f} km/h)",
        "reason.wind.strong": "Strong gusts ({gusts:.0f} km/h)",
        "reason.wind.moderate": "Moderate gusts ({gusts:.0f} km/h)",
        # Precipitation (param: mm)
        "reason.precip.heavy": "Heavy rainfall ({mm:.1f} mm)",
        "reason.precip.significant": "Significant rainfall ({mm:.1f} mm)",
        "reason.precip.moderate": "Moderate rainfall ({mm:.1f} mm)",
        "reason.precip.light": "Light rainfall ({mm:.1f} mm)",
        # Temperature (param: temp, °C)
        "reason.temp.extreme_cold": "Extreme cold ({temp:.0f}°C) — frostbite risk",
        "reason.temp.very_cold": "Very cold ({temp:.0f}°C)",
        "reason.temp.below_freezing": "Below freezing ({temp:.0f}°C)",
        "reason.temp.extreme_heat": "Extreme heat ({temp:.0f}°C) — heat stroke risk",
        "reason.temp.very_hot": "Very hot ({temp:.0f}°C) — carry extra water",
        # Climatology instability (params vary — see the climatology endpoint)
        "climatology.thunderstorm": "Thunderstorms on {pct}% of these days over the last {years} years",
        "climatology.wet": "Rain on {pct}% of these days historically",
        "climatology.gusts": "Top-decile gusts reach {kmh} km/h this week of the year",
        "climatology.volatility": "Conditions flip between wet and dry {pct}% of day-to-day transitions — forecasts age fast here",
    },
    "ro": {
        "reason.good": "Condiții bune pentru drumeție",
        "reason.wmo.45": "Ceață — risc de orientare pe creste",
        "reason.wmo.48": "Ceață înghețată — vizibilitate redusă și risc de gheață",
        "reason.wmo.51": "Burniță ușoară",
        "reason.wmo.53": "Burniță",
        "reason.wmo.55": "Burniță densă",
        "reason.wmo.61": "Se așteaptă ploaie",
        "reason.wmo.63": "Ploaie moderată",
        "reason.wmo.65": "Ploaie abundentă — risc de hipotermie",
        "reason.wmo.71": "Ninsoare ușoară",
        "reason.wmo.73": "Ninsoare — teren alunecos",
        "reason.wmo.75": "Ninsoare abundentă — traseul poate fi impracticabil",
        "reason.wmo.77": "Grăunțe de zăpadă",
        "reason.wmo.80": "Averse de ploaie",
        "reason.wmo.81": "Averse puternice de ploaie",
        "reason.wmo.82": "Averse violente de ploaie",
        "reason.wmo.85": "Averse de ninsoare",
        "reason.wmo.86": "Averse puternice de ninsoare",
        "reason.wmo.95": "Furtună — evitați crestele expuse",
        "reason.wmo.96": "Furtună cu grindină",
        "reason.wmo.99": "Furtună cu grindină puternică",
        "reason.wind.dangerous": "Rafale periculoase ({gusts:.0f} km/h) — nu urcați pe vârf",
        "reason.wind.very_strong": "Rafale foarte puternice ({gusts:.0f} km/h)",
        "reason.wind.strong": "Rafale puternice ({gusts:.0f} km/h)",
        "reason.wind.moderate": "Rafale moderate ({gusts:.0f} km/h)",
        "reason.precip.heavy": "Precipitații abundente ({mm:.1f} mm)",
        "reason.precip.significant": "Precipitații semnificative ({mm:.1f} mm)",
        "reason.precip.moderate": "Precipitații moderate ({mm:.1f} mm)",
        "reason.precip.light": "Precipitații ușoare ({mm:.1f} mm)",
        "reason.temp.extreme_cold": "Frig extrem ({temp:.0f}°C) — risc de degerături",
        "reason.temp.very_cold": "Foarte frig ({temp:.0f}°C)",
        "reason.temp.below_freezing": "Sub zero grade ({temp:.0f}°C)",
        "reason.temp.extreme_heat": "Caniculă extremă ({temp:.0f}°C) — risc de insolație",
        "reason.temp.very_hot": "Foarte cald ({temp:.0f}°C) — luați apă în plus",
        "climatology.thunderstorm": "Furtuni în {pct}% din aceste zile în ultimii {years} ani",
        "climatology.wet": "Ploaie în {pct}% din aceste zile, istoric",
        "climatology.gusts": "Rafalele din decila superioară ajung la {kmh} km/h în această săptămână a anului",
        "climatology.volatility": "Vremea alternează umed/uscat în {pct}% dintre tranzițiile zilnice — prognozele se învechesc rapid aici",
    },
}
