from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.profile import TeacherProfile
from app.models.user import User
from app.schemas.profiles import TeacherProfileCreate
from app.schemas.users import UserCreate
from app.services.base import BaseService
from app.services.user_service import UserService


class TeacherService(BaseService):
    def create_teacher(self, user_payload: UserCreate, profile_payload: TeacherProfileCreate) -> User:
        if UserRole.TEACHER not in user_payload.roles:
            raise self.bad_request("Created user must include teacher role")

        email = user_payload.email.strip().lower()
        UserService(self.db)._ensure_email_available(email)

        user = User(
            full_name=user_payload.full_name.strip(),
            phone=user_payload.phone,
            email=email,
            password_hash=hash_password(user_payload.password),
            roles=user_payload.roles,
            status=user_payload.status,
        )
        self.db.add(user)
        self.db.flush()

        profile = TeacherProfile(user_id=user.id, **profile_payload.model_dump())
        self.db.add(profile)
        self.commit()
        return UserService(self.db).get_user(str(user.id))

    def list_teachers(self) -> list[User]:
        statement = (
            select(User)
            .options(selectinload(User.teacher_profile))
            .where(User.roles.contains([UserRole.TEACHER.value]))
            .order_by(User.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().unique())


def get_teacher_service(db: Session) -> TeacherService:
    return TeacherService(db)
