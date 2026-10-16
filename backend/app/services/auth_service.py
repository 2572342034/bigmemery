from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import user_session_scope
from app.db.user_models import User
from app.schemas.auth import AuthResponse, UserProfile


class AuthService:
    def ensure_default_admin(self) -> None:
        with user_session_scope() as session:
            existing = session.scalar(select(User).where(User.username == settings.default_admin_username))
            if existing:
                return
            session.add(
                User(
                    username=settings.default_admin_username,
                    display_name=settings.default_admin_display_name,
                    email=None,
                    hashed_password=hash_password(settings.default_admin_password),
                    is_active=True,
                )
            )

    def register(
        self,
        *,
        username: str,
        password: str,
        display_name: str,
        email: str | None,
    ) -> AuthResponse:
        with user_session_scope() as session:
            # 拼接url
            conditions = [User.username == username]
            if email:
                conditions.append(User.email == email)
            duplicate = session.scalar(select(User).where(or_(*conditions)))

        #     SELECT * FROM
        #     users
        #     WHERE
        #     username = '输入的用户名'
        #     OR(email='输入的邮箱')
        # LIMIT
        # 1

            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

            user = User(
                username=username,
                display_name=display_name,
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
            )
            session.add(user)
            session.flush()
            session.refresh(user)
            token = create_access_token(user.id, user.username)
            return AuthResponse(access_token=token, user=self._to_profile(user))

    def login(self, username: str, password: str) -> AuthResponse:
        with user_session_scope() as session:
            user = session.scalar(select(User).where(User.username == username))
            if user is None or not verify_password(password, user.hashed_password):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
            user.last_login_at = datetime.now(timezone.utc)
            session.add(user)
            session.flush()
            token = create_access_token(user.id, user.username)
            return AuthResponse(access_token=token, user=self._to_profile(user))

    def get_user_by_id(self, user_id: int) -> User | None:
        with user_session_scope() as session:
            return session.get(User, user_id)

    @staticmethod
    def _to_profile(user: User) -> UserProfile:
        return UserProfile(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            created_at=user.created_at,
        )


auth_service = AuthService()
