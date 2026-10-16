from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.db.user_models import User
from app.schemas.auth import UserProfile
from app.services.auth_service import auth_service


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token有问题")
    payload = decode_access_token(credentials.credentials)
    user = auth_service.get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_current_user_from_query(token: str = Query(...)) -> User:
    payload = decode_access_token(token)
    user = auth_service.get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def to_profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        created_at=user.created_at,
    )
