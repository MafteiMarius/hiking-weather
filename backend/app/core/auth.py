import uuid
from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User, UserProfile
from app.db.session import get_db

_settings = get_settings()

# ── Argon2id password hashing ─────────────────────────────────────────────────
# Replaces fastapi-users' default bcrypt with the PHC winner.
_password_helper = PasswordHelper(PasswordHash((Argon2Hasher(),)))


# ── User DB adapter ───────────────────────────────────────────────────────────

async def get_user_db(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    yield SQLAlchemyUserDatabase(session, User)


# ── User manager ──────────────────────────────────────────────────────────────

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = _settings.jwt_secret
    verification_token_secret = _settings.jwt_secret

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        """Create an empty profile row every time a user registers."""
        profile = UserProfile(user_id=user.id)
        self.user_db.session.add(profile)
        await self.user_db.session.commit()


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db, password_helper=_password_helper)


# ── Access-token backend (short-lived JWT in httpOnly cookie) ─────────────────

_access_transport = CookieTransport(
    cookie_name="hikecast_access",
    cookie_max_age=_settings.jwt_lifetime_seconds,
    cookie_httponly=True,
    cookie_secure=_settings.cookie_secure,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    return JWTStrategy(
        secret=_settings.jwt_secret,
        lifetime_seconds=_settings.jwt_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=_access_transport,
    get_strategy=get_jwt_strategy,
)


# ── FastAPIUsers instance — source of all route factories + current_user ──────

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
optional_user = fastapi_users.current_user(optional=True)
