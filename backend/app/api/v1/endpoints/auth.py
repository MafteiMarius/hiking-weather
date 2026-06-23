"""Custom auth endpoints: login, logout, refresh.

Why custom instead of fastapi-users built-in?
  fastapi-users v15 no longer ships a DatabaseStrategy or AccessToken base model —
  token storage is now the application's responsibility. We write these three
  endpoints ourselves and delegate user management to fastapi-users (register,
  /users/me, current_user dependency, password hashing).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    UserManager,
    current_active_user,
    get_jwt_strategy,
    get_user_manager,
)
from app.core.config import get_settings
from app.core.tokens import (
    create_refresh_token,
    get_user_id_for_refresh_token,
    revoke_refresh_token,
)
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()

_ACCESS_COOKIE = "hikecast_access"
_REFRESH_COOKIE = "hikecast_refresh"

_COOKIE_KWARGS = {
    "httponly": True,
    "secure": _settings.cookie_secure,
    "samesite": "lax",
    "path": "/",
}


@router.post("/jwt/login", status_code=status.HTTP_200_OK)
async def login(
    response: Response,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials",
        )

    # Access token — short-lived JWT, validated by signature alone
    access_token = await get_jwt_strategy().write_token(user)
    # Refresh token — opaque string stored in DB; logout deletes the row
    refresh_token = await create_refresh_token(user.id, session)

    response.set_cookie(
        _ACCESS_COOKIE,
        access_token,
        max_age=_settings.jwt_lifetime_seconds,
        **_COOKIE_KWARGS,
    )
    response.set_cookie(
        _REFRESH_COOKIE,
        refresh_token,
        max_age=_settings.refresh_lifetime_seconds,
        **_COOKIE_KWARGS,
    )
    return {"message": "logged in"}


@router.post("/jwt/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    request: Request,
    response: Response,
    user_manager: UserManager = Depends(get_user_manager),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    refresh_token = request.cookies.get(_REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    user_id = await get_user_id_for_refresh_token(refresh_token, session)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await user_manager.get(user_id)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account inactive",
        )

    access_token = await get_jwt_strategy().write_token(user)
    response.set_cookie(
        _ACCESS_COOKIE,
        access_token,
        max_age=_settings.jwt_lifetime_seconds,
        **_COOKIE_KWARGS,
    )
    return {"message": "token refreshed"}


@router.post("/jwt/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    refresh_token = request.cookies.get(_REFRESH_COOKIE)
    if refresh_token:
        # Deletes the DB row — any subsequent /refresh with this token → 401
        await revoke_refresh_token(refresh_token, session)

    response.delete_cookie(_ACCESS_COOKIE, path="/")
    response.delete_cookie(_REFRESH_COOKIE, path="/")
