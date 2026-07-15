"""Server-side i18n for generated text (weather, score reasons, climatology).

Public surface:
  - `t(key, lang, **params)`      → render a message template
  - `describe_weather(code, lang)`→ WMO code → localized description
  - `resolve_lang(header)`        → Accept-Language string → supported code
  - `get_lang`                    → FastAPI dependency wrapping resolve_lang

DECISIONS 016 explains why DEFAULT_LANG is English even though the web UI
defaults to Romanian: the header-absent default only affects non-UI callers
(curl, tests, other clients), and keeping it English means the existing test
suite — which asserts English strings without sending a header — stays valid.
The web app always sends `Accept-Language: ro`.
"""
from typing import Optional

from fastapi import Header

from app.i18n.messages import MESSAGES, WEATHER_DESC

SUPPORTED_LANGS: tuple[str, ...] = ("en", "ro")
DEFAULT_LANG = "en"


def resolve_lang(accept_language: Optional[str]) -> str:
    """Map an Accept-Language header to a supported language code.

    Only the primary tag of the first (highest-priority) language is honoured
    — we don't parse q-values because we support exactly two languages and the
    web client sends a single explicit tag. Unknown/absent → DEFAULT_LANG.
    """
    if not accept_language:
        return DEFAULT_LANG
    first = accept_language.split(",")[0].strip().lower()  # "ro-ro;q=0.9" → "ro-ro;q=0.9"
    primary = first.split(";")[0].split("-")[0]            # → "ro"
    return primary if primary in SUPPORTED_LANGS else DEFAULT_LANG


def get_lang(accept_language: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: resolved UI language for this request."""
    return resolve_lang(accept_language)


def t(key: str, lang: str, **params: object) -> str:
    """Render a message template. Falls back EN, then the raw key (never raises
    on a missing key so a typo degrades to something visible, not a 500)."""
    table = MESSAGES.get(lang) or MESSAGES[DEFAULT_LANG]
    template = table.get(key) or MESSAGES[DEFAULT_LANG].get(key) or key
    return template.format(**params)


def describe_weather(code: int, lang: str) -> str:
    """WMO weather code → localized short description."""
    table = WEATHER_DESC.get(lang) or WEATHER_DESC[DEFAULT_LANG]
    return table.get(code) or WEATHER_DESC[DEFAULT_LANG].get(code) or f"Code {code}"
