from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.forecast import router as forecast_router
from app.api.v1.endpoints.profile import router as profile_router
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
