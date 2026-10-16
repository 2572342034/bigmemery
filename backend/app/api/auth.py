from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, to_profile
from app.db.user_models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserProfile
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    return auth_service.register(
        username=request.username,
        password=request.password,
        display_name=request.display_name,
        email=request.email,
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    return auth_service.login(request.username, request.password)


@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)):
    return to_profile(current_user)
