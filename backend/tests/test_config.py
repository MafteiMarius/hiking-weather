"""Unit tests for database URL normalization.

Pure function — no DB, no settings, no async. These exist because the failure
they guard against only shows up against a *managed* Postgres (Neon, Railway,
Heroku), which we can't reach from the test suite: a libpq connection string
either picks the wrong dialect or makes asyncpg raise on connect. Testing the
translation directly means the deploy doesn't have to be the first place we
find out.
"""

from app.core.config import normalize_database_url

# A realistic Neon connection string — the exact shape the dashboard hands out.
NEON = (
    "postgresql://hikecast:secret@ep-cool-name-123456.eu-central-1.aws.neon.tech"
    "/hikecast?sslmode=require&channel_binding=require"
)

# What local dev has in .env today.
LOCAL = "postgresql+asyncpg://hikecast:hikecast@localhost:5432/hikecast"


class TestDriver:
    def test_bare_postgresql_gets_the_async_driver(self) -> None:
        url, _ = normalize_database_url("postgresql://u:p@host:5432/db")
        assert url == "postgresql+asyncpg://u:p@host:5432/db"

    def test_legacy_postgres_scheme_is_upgraded(self) -> None:
        # Heroku-style `postgres://` — same database, older spelling.
        url, _ = normalize_database_url("postgres://u:p@host:5432/db")
        assert url == "postgresql+asyncpg://u:p@host:5432/db"

    def test_correct_driver_is_left_alone(self) -> None:
        url, connect_args = normalize_database_url(LOCAL)
        assert url == LOCAL
        assert connect_args == {}

    def test_other_drivers_are_not_hijacked(self) -> None:
        # If someone deliberately asks for psycopg, respect it rather than
        # silently rewriting their choice.
        url, _ = normalize_database_url("postgresql+psycopg://u:p@host/db")
        assert url == "postgresql+psycopg://u:p@host/db"


class TestSslTranslation:
    def test_sslmode_becomes_an_ssl_connect_arg(self) -> None:
        url, connect_args = normalize_database_url("postgresql://u:p@host/db?sslmode=require")
        assert "sslmode" not in url          # asyncpg would raise on it
        assert connect_args == {"ssl": "require"}

    def test_verify_full_carries_over_verbatim(self) -> None:
        _, connect_args = normalize_database_url("postgresql://u:p@host/db?sslmode=verify-full")
        assert connect_args == {"ssl": "verify-full"}

    def test_explicit_disable_is_preserved(self) -> None:
        # An explicit opt-out must stay meaningful, not be dropped into the
        # "no ssl argument at all" default.
        _, connect_args = normalize_database_url("postgresql://u:p@host/db?sslmode=disable")
        assert connect_args == {"ssl": "disable"}

    def test_no_sslmode_means_no_ssl_argument(self) -> None:
        _, connect_args = normalize_database_url("postgresql://u:p@host/db")
        assert connect_args == {}


class TestQueryString:
    def test_libpq_only_params_are_dropped(self) -> None:
        # channel_binding has no asyncpg equivalent; passing it through would
        # be a TypeError at connect time.
        url, _ = normalize_database_url(
            "postgresql://u:p@host/db?channel_binding=require&gssencmode=prefer"
        )
        assert url == "postgresql+asyncpg://u:p@host/db"

    def test_unrelated_params_survive(self) -> None:
        url, connect_args = normalize_database_url(
            "postgresql://u:p@host/db?application_name=hikecast&sslmode=require"
        )
        assert url == "postgresql+asyncpg://u:p@host/db?application_name=hikecast"
        assert connect_args == {"ssl": "require"}

    def test_param_matching_is_case_insensitive(self) -> None:
        _, connect_args = normalize_database_url("postgresql://u:p@host/db?SSLMode=require")
        assert connect_args == {"ssl": "require"}


class TestRealWorldStrings:
    def test_neon_string_is_fully_usable(self) -> None:
        url, connect_args = normalize_database_url(NEON)
        assert url == (
            "postgresql+asyncpg://hikecast:secret"
            "@ep-cool-name-123456.eu-central-1.aws.neon.tech/hikecast"
        )
        assert connect_args == {"ssl": "require"}

    def test_password_special_characters_are_untouched(self) -> None:
        # urlsplit/urlunsplit must not re-encode credentials — a mangled
        # password fails authentication in a way that looks like a wrong secret.
        url, _ = normalize_database_url("postgresql://u:p%40ss%2Fword@host/db?sslmode=require")
        assert "p%40ss%2Fword" in url

    def test_local_dev_url_is_a_no_op(self) -> None:
        # The everyday case: whatever we do must not disturb it.
        assert normalize_database_url(LOCAL) == (LOCAL, {})
