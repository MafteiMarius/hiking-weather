import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ── fastapi-users owned tables ────────────────────────────────────────────────

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"


class AccessToken(Base):
    """Long-lived refresh tokens stored in DB so they can be revoked on logout.

    fastapi-users v15 dropped its own AccessToken base class; we own this table.
    token = secrets.token_urlsafe(32) → always 43 URL-safe chars.
    """

    __tablename__ = "access_tokens"

    token: Mapped[str] = mapped_column(String(43), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


# ── Application tables ────────────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(80))
    home_lat: Mapped[Optional[float]] = mapped_column(Double())
    home_lng: Mapped[Optional[float]] = mapped_column(Double())
    experience_level: Mapped[int] = mapped_column(SmallInteger(), default=3)
    max_distance_km: Mapped[int] = mapped_column(SmallInteger(), default=150)
    max_difficulty: Mapped[int] = mapped_column(SmallInteger(), default=4)
    units_metric: Mapped[bool] = mapped_column(Boolean(), default=True)
    locale: Mapped[str] = mapped_column(String(8), default="ro-RO")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("experience_level BETWEEN 1 AND 5", name="ck_profile_exp_level"),
        CheckConstraint("max_difficulty BETWEEN 1 AND 5", name="ck_profile_max_diff"),
    )


class SavedLocation(Base):
    __tablename__ = "saved_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    elevation_m: Mapped[Optional[int]] = mapped_column(SmallInteger())
    notes: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_saved_user", "user_id"),
        Index("idx_saved_geo", "location", postgresql_using="gist"),
    )


class Trail(Base):
    __tablename__ = "trails"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer(), nullable=False)
    elevation_gain_m: Mapped[int] = mapped_column(Integer(), nullable=False)
    start_point: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    summit_point: Mapped[Optional[WKBElement]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326)
    )
    summit_elev_m: Mapped[Optional[int]] = mapped_column(SmallInteger())
    description: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_trail_difficulty"),
        Index("idx_trails_start", "start_point", postgresql_using="gist"),
        Index("idx_trails_region", "region"),
    )


class ForecastCache(Base):
    __tablename__ = "forecast_cache"

    cache_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    lat: Mapped[float] = mapped_column(Double(), nullable=False)
    lng: Mapped[float] = mapped_column(Double(), nullable=False)
    elevation_m: Mapped[Optional[int]] = mapped_column(SmallInteger())
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (Index("idx_cache_expires", "expires_at"),)


class Climatology(Base):
    __tablename__ = "climatology"

    cache_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    iso_week: Mapped[int] = mapped_column(SmallInteger(), primary_key=True)
    years_analyzed: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    precip_day_frequency_pct: Mapped[Optional[int]] = mapped_column(SmallInteger())
    thunderstorm_pct: Mapped[Optional[int]] = mapped_column(SmallInteger())
    temp_avg_max_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1))
    temp_avg_min_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1))
    wind_gust_p90_kmh: Mapped[Optional[int]] = mapped_column(SmallInteger())
    volatility_index: Mapped[Optional[int]] = mapped_column(SmallInteger())
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("iso_week BETWEEN 1 AND 53", name="ck_climatology_iso_week"),
    )
