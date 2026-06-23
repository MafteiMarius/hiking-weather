from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.db.models import User, UserProfile
from app.db.session import get_db
from app.schemas.profile import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


async def _get_or_create_profile(
    user: User, session: AsyncSession
) -> UserProfile:
    """Return the user's profile, creating a default row if missing."""
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.get("", response_model=ProfileRead)
async def get_profile(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    return await _get_or_create_profile(user, session)


@router.patch("", response_model=ProfileRead)
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    profile = await _get_or_create_profile(user, session)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
