"""Seed the demo account advertised in the README.

Run from backend/ with the venv active and the database up and migrated:

    python -m app.seeds.demo

Idempotent: if the demo user already exists nothing is changed, so it is safe
to run on every deploy.
"""
import asyncio

from sqlalchemy import select

from app.core.auth import password_helper
from app.db.models import User, UserProfile
from app.db.session import AsyncSessionLocal

DEMO_EMAIL = "demo@hikecast.app"
DEMO_PASSWORD = "HikeCast2026!"


async def seed_demo_user() -> bool:
    """Create the demo user + empty profile. Returns True if created."""
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(User).where(User.email == DEMO_EMAIL)
        )
        if existing is not None:
            return False

        user = User(
            email=DEMO_EMAIL,
            hashed_password=password_helper.hash(DEMO_PASSWORD),
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()  # populates user.id for the profile FK
        session.add(UserProfile(user_id=user.id))
        await session.commit()
        return True


def main() -> None:
    created = asyncio.run(seed_demo_user())
    if created:
        print(f"Demo account created: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    else:
        print(f"Demo account already exists: {DEMO_EMAIL}")


if __name__ == "__main__":
    main()
