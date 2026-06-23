"""Initial schema: extensions + all tables

Revision ID: 0001
Revises:
Create Date: 2026-06-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── PostgreSQL extensions (must come before geography columns) ────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # ── fastapi-users: users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── access_tokens (our refresh-token store; fastapi-users v15 dropped this) ─
    op.create_table(
        "access_tokens",
        sa.Column("token", sa.String(length=43), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index("ix_access_tokens_user_id", "access_tokens", ["user_id"])
    op.create_index("ix_access_tokens_expires_at", "access_tokens", ["expires_at"])

    # ── user_profiles ─────────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("home_lat", sa.Double(), nullable=True),
        sa.Column("home_lng", sa.Double(), nullable=True),
        sa.Column(
            "experience_level",
            sa.SmallInteger(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "max_distance_km",
            sa.SmallInteger(),
            nullable=False,
            server_default="150",
        ),
        sa.Column(
            "max_difficulty",
            sa.SmallInteger(),
            nullable=False,
            server_default="4",
        ),
        sa.Column(
            "units_metric", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "locale", sa.String(length=8), nullable=False, server_default="ro-RO"
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "experience_level BETWEEN 1 AND 5", name="ck_profile_exp_level"
        ),
        sa.CheckConstraint(
            "max_difficulty BETWEEN 1 AND 5", name="ck_profile_max_diff"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # ── saved_locations ───────────────────────────────────────────────────────
    op.create_table(
        "saved_locations",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("elevation_m", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_saved_user", "saved_locations", ["user_id"])
    op.create_index(
        "idx_saved_geo",
        "saved_locations",
        ["location"],
        postgresql_using="gist",
    )

    # ── trails ────────────────────────────────────────────────────────────────
    op.create_table(
        "trails",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("distance_m", sa.Integer(), nullable=False),
        sa.Column("elevation_gain_m", sa.Integer(), nullable=False),
        sa.Column(
            "start_point",
            Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column(
            "summit_point",
            Geography(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("summit_elev_m", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_trail_difficulty"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "idx_trails_start", "trails", ["start_point"], postgresql_using="gist"
    )
    op.create_index("idx_trails_region", "trails", ["region"])

    # ── forecast_cache ────────────────────────────────────────────────────────
    op.create_table(
        "forecast_cache",
        sa.Column("cache_key", sa.String(length=40), nullable=False),
        sa.Column("lat", sa.Double(), nullable=False),
        sa.Column("lng", sa.Double(), nullable=False),
        sa.Column("elevation_m", sa.SmallInteger(), nullable=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index("idx_cache_expires", "forecast_cache", ["expires_at"])

    # ── climatology ───────────────────────────────────────────────────────────
    op.create_table(
        "climatology",
        sa.Column("cache_key", sa.String(length=40), nullable=False),
        sa.Column("iso_week", sa.SmallInteger(), nullable=False),
        sa.Column("years_analyzed", sa.SmallInteger(), nullable=False),
        sa.Column("precip_day_frequency_pct", sa.SmallInteger(), nullable=True),
        sa.Column("thunderstorm_pct", sa.SmallInteger(), nullable=True),
        sa.Column("temp_avg_max_c", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("temp_avg_min_c", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("wind_gust_p90_kmh", sa.SmallInteger(), nullable=True),
        sa.Column("volatility_index", sa.SmallInteger(), nullable=True),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "iso_week BETWEEN 1 AND 53", name="ck_climatology_iso_week"
        ),
        sa.PrimaryKeyConstraint("cache_key", "iso_week"),
    )


def downgrade() -> None:
    op.drop_table("climatology")
    op.drop_table("forecast_cache")
    op.drop_index("idx_trails_region", table_name="trails")
    op.drop_index("idx_trails_start", table_name="trails")
    op.drop_table("trails")
    op.drop_index("idx_saved_geo", table_name="saved_locations")
    op.drop_index("idx_saved_user", table_name="saved_locations")
    op.drop_table("saved_locations")
    op.drop_table("user_profiles")
    op.drop_index("ix_access_tokens_expires_at", table_name="access_tokens")
    op.drop_index("ix_access_tokens_user_id", table_name="access_tokens")
    op.drop_table("access_tokens")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    # Extensions intentionally left in place on downgrade — removing postgis
    # is destructive and can break other DB objects. Run manually if needed.
