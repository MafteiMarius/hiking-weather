"""Refresh-token CRUD.

fastapi-users v15 dropped DatabaseStrategy and its AccessToken base model.
We implement a thin layer that stores opaque tokens in the access_tokens table.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import AccessToken


async def create_refresh_token(user_id: uuid.UUID, session: AsyncSession) -> str:
    """Insert a new refresh token row and return the token string."""
    settings = get_settings()
    token = secrets.token_urlsafe(32)  # 43 URL-safe chars
    expires = datetime.now(timezone.utc) + timedelta(
        seconds=settings.refresh_lifetime_seconds
    )
    row = AccessToken(token=token, user_id=user_id, expires_at=expires)
    session.add(row)
    await session.commit()
    return token


async def get_user_id_for_refresh_token(
    token: str, session: AsyncSession
) -> Optional[uuid.UUID]:
    """Return the user_id if the token exists and has not expired, else None."""
    result = await session.execute(
        select(AccessToken).where(
            AccessToken.token == token,
            AccessToken.expires_at > datetime.now(timezone.utc),
        )
    )
    row = result.scalar_one_or_none()
    return row.user_id if row else None


async def revoke_refresh_token(token: str, session: AsyncSession) -> None:
    """Delete the refresh token row (no-op if it doesn't exist)."""
    result = await session.execute(
        select(AccessToken).where(AccessToken.token == token)
    )
    row = result.scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()
