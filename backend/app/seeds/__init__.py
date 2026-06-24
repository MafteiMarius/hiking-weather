"""Idempotent demo-data seed. Safe to run multiple times."""
import asyncio
import uuid

from sqlalchemy import select

from app.core.auth import _password_helper
from app.db.models import SavedLocation, User, UserProfile
from app.db.session import AsyncSessionLocal

DEMO_EMAIL = "demo@hikecast.app"
DEMO_PASSWORD = "HikeCast2026!"

# WKT uses (longitude latitude) order
_LOCATIONS = [
    {
        "name": "Vârful Omu",
        "wkt": "POINT(25.4547 45.4417)",
        "elevation_m": 2505,
        "notes": "Cel mai înalt vârf din Munții Bucegi (2505 m)",
    },
    {
        "name": "Cascada 7 Scări",
        "wkt": "POINT(25.5611 45.5928)",
        "elevation_m": 1150,
        "notes": "Cascadă spectaculoasă în Munții Piatra Mare",
    },
    {
        "name": "Negoiu",
        "wkt": "POINT(24.5561 45.5639)",
        "elevation_m": 2535,
        "notes": "Al doilea cel mai înalt vârf din România, Munții Făgăraș",
    },
]


async def run() -> None:
    async with AsyncSessionLocal() as session:
        exists = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if exists:
            return

        user = User(
            id=uuid.uuid4(),
            email=DEMO_EMAIL,
            hashed_password=_password_helper.hash(DEMO_PASSWORD),
            is_active=True,
            is_superuser=False,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        session.add(UserProfile(user_id=user.id))

        for loc in _LOCATIONS:
            session.add(
                SavedLocation(
                    user_id=user.id,
                    name=loc["name"],
                    location=f"SRID=4326;{loc['wkt']}",
                    elevation_m=loc["elevation_m"],
                    notes=loc["notes"],
                )
            )

        await session.commit()
        print(f"[seed] demo account created: {DEMO_EMAIL}")


if __name__ == "__main__":
    asyncio.run(run())
