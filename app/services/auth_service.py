from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jwt import create_token, decode_token
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginSchema
from app.services.base import BaseService, ServiceError, parse_uuid


class AuthService(BaseService):
    def login(self, payload: LoginSchema) -> dict:
        normalized_email = payload.email.strip().lower()
        statement = select(User).where(func.lower(User.email) == normalized_email)
        user = self.db.execute(statement).scalar_one_or_none()
        if not user or not verify_password(payload.password, user.password_hash):
            raise ServiceError(401, "Invalid credentials")
        if user.status.value != "active":
            raise ServiceError(403, "User is inactive")

        tokens = self._build_tokens(user)
        user.refresh_token_hash = hash_password(tokens["refresh_token"])
        self.db.add(user)
        self.commit()
        return tokens

    def refresh_access_token(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ServiceError(401, "Invalid refresh token")

        user_id = parse_uuid(payload.get("sub"), "refresh token subject")
        user = self.db.get(User, user_id)
        if not user or not user.refresh_token_hash:
            raise ServiceError(401, "Refresh token expired")
        if not verify_password(refresh_token, user.refresh_token_hash):
            raise ServiceError(401, "Refresh token mismatch")

        return {
            "access_token": create_token(
                payload={
                    "sub": str(user.id),
                    "type": "access",
                    "roles": [role.value for role in user.roles],
                    "course_center_id": str(user.course_center_id),
                },
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            ),
            "token_type": "bearer",
        }

    def logout(self, user: User) -> None:
        user.refresh_token_hash = None
        self.db.add(user)
        self.commit()

    def _build_tokens(self, user: User) -> dict:
        access_token = create_token(
            payload={
                "sub": str(user.id),
                "type": "access",
                "roles": [role.value for role in user.roles],
                "course_center_id": str(user.course_center_id),
            },
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_token(
            payload={"sub": str(user.id), "type": "refresh"},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def get_auth_service(db: Session) -> AuthService:
    return AuthService(db)
