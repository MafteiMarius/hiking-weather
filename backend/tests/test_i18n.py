"""Unit tests for the server-side i18n layer.

Pure functions — no DB, no HTTP. Covers language resolution from
Accept-Language, template rendering with fallback, and weather descriptions.
"""

from app.i18n import DEFAULT_LANG, describe_weather, resolve_lang, t


class TestResolveLang:
    def test_none_falls_back_to_default(self) -> None:
        assert resolve_lang(None) == DEFAULT_LANG
        assert resolve_lang("") == DEFAULT_LANG

    def test_plain_supported_tag(self) -> None:
        assert resolve_lang("ro") == "ro"
        assert resolve_lang("en") == "en"

    def test_region_and_quality_are_stripped(self) -> None:
        # Browsers send things like "ro-RO,ro;q=0.9,en-US;q=0.8"
        assert resolve_lang("ro-RO,ro;q=0.9,en-US;q=0.8") == "ro"
        assert resolve_lang("en-GB") == "en"

    def test_uppercase_is_normalised(self) -> None:
        assert resolve_lang("RO") == "ro"

    def test_unsupported_language_falls_back(self) -> None:
        # We only ship en/ro — a French browser gets the default, not a crash.
        assert resolve_lang("fr-FR,fr;q=0.9") == DEFAULT_LANG


class TestTranslate:
    def test_renders_in_requested_language(self) -> None:
        assert t("reason.good", "en") == "Conditions look good for hiking"
        assert t("reason.good", "ro") == "Condiții bune pentru drumeție"

    def test_interpolates_params_with_format_spec(self) -> None:
        # Float gust rounded to whole km/h by the template's :.0f spec
        assert t("reason.wind.strong", "en", gusts=54.7) == "Strong gusts (55 km/h)"
        assert t("reason.wind.strong", "ro", gusts=54.7) == "Rafale puternice (55 km/h)"

    def test_unknown_lang_falls_back_to_english(self) -> None:
        assert t("reason.good", "fr") == "Conditions look good for hiking"

    def test_unknown_key_returns_key_not_crash(self) -> None:
        assert t("reason.does_not_exist", "ro") == "reason.does_not_exist"


class TestDescribeWeather:
    def test_known_codes(self) -> None:
        assert describe_weather(95, "en") == "Thunderstorm"
        assert describe_weather(95, "ro") == "Furtună"
        assert describe_weather(0, "ro") == "Cer senin"

    def test_unknown_code_is_labelled_not_crashing(self) -> None:
        assert describe_weather(123, "en") == "Code 123"

    def test_unknown_lang_falls_back_to_english(self) -> None:
        assert describe_weather(95, "de") == "Thunderstorm"
