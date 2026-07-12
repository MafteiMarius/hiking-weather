from fastapi import APIRouter

from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.climatology import router as climatology_router
from app.api.v1.endpoints.forecast import router as forecast_router
from app.api.v1.endpoints.locations import router as locations_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.recommend import router as recommend_router
from app.api.v1.endpoints.trails import router as trails_router
from app.core.auth import fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()

# fastapi-users managed routes
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Custom routes
router.include_router(auth_router)
router.include_router(profile_router)
router.include_router(forecast_router)
router.include_router(locations_router)
router.include_router(climatology_router)
router.include_router(trails_router)
router.include_router(recommend_router)
router.include_router(ai_router)
