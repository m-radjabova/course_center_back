from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.profile import StudentProfile, TeacherProfile
from app.models.user import User
from app.schemas.profiles import StudentProfileCreate, StudentProfileUpdate, TeacherProfileCreate, TeacherProfileUpdate
from app.schemas.users import CurrentUserUpdate, UserCreate, UserUpdate
from app.services.base import BaseService, parse_uuid


class UserService(BaseService):
    def list_users(self, role: UserRole | None = None) -> list[User]:
        statement = select(User).options(
            selectinload(User.student_profile),
            selectinload(User.teacher_profile),
        )
        if role:
            statement = statement.where(User.roles.contains([role.value]))
        statement = statement.order_by(User.created_at.desc())
        return list(self.db.execute(statement).scalars().unique())

    def get_user(self, user_id: str) -> User:
        user = self.db.execute(
            select(User)
            .options(selectinload(User.student_profile), selectinload(User.teacher_profile))
            .where(User.id == parse_uuid(user_id, "user id"))
        ).scalar_one_or_none()
        if not user:
            raise self.not_found("User")
        return user

    def create_user(self, payload: UserCreate) -> User:
        email = payload.email.strip().lower()
        self._ensure_email_available(email)
        user = User(
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            email=email,
            password_hash=hash_password(payload.password),
            roles=payload.roles,
            status=payload.status,
        )
        self.db.add(user)
        self.commit()
        return self.refresh(user)

    def update_user(self, user_id: str, payload: UserUpdate) -> User:
        user = self.get_user(user_id)
        data = payload.model_dump(exclude_unset=True)
        if "email" in data and data["email"]:
            email = data["email"].strip().lower()
            self._ensure_email_available(email, exclude_user_id=user.id)
            user.email = email
        if "password" in data and data["password"]:
            user.password_hash = hash_password(data.pop("password"))
        for field in ("full_name", "phone", "status"):
            if field in data:
                setattr(user, field, data[field])
        if "roles" in data and data["roles"] is not None:
            user.roles = data["roles"]
        self.db.add(user)
        self.commit()
        return self.refresh(user)

    def update_current_user(self, user: User, payload: CurrentUserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        if "email" in data and data["email"]:
            email = data["email"].strip().lower()
            self._ensure_email_available(email, exclude_user_id=user.id)
            user.email = email
        if "full_name" in data and data["full_name"] is not None:
            user.full_name = data["full_name"].strip()
        if "phone" in data:
            user.phone = data["phone"]
        self.db.add(user)
        self.commit()
        return self.refresh(user)

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password_hash):
            raise self.bad_request("Current password is incorrect")
        if current_password == new_password:
            raise self.bad_request("New password must be different from current password")
        user.password_hash = hash_password(new_password)
        self.db.add(user)
        self.commit()
        return self.refresh(user)

    def reset_password(self, user_id: str, new_password: str) -> User:
        user = self.get_user(user_id)
        user.password_hash = hash_password(new_password)
        self.db.add(user)
        self.commit()
        return self.refresh(user)

    def create_teacher_profile(self, user_id: str, payload: TeacherProfileCreate) -> TeacherProfile:
        user = self.get_user(user_id)
        if UserRole.TEACHER not in user.roles:
            raise self.bad_request("Teacher profile can only be created for users with teacher role")
        if user.teacher_profile:
            raise self.bad_request("Teacher profile already exists")
        profile = TeacherProfile(user_id=user.id, **payload.model_dump())
        self.db.add(profile)
        self.commit()
        return self.refresh(profile)

    def update_teacher_profile(self, user_id: str, payload: TeacherProfileUpdate) -> TeacherProfile:
        user = self.get_user(user_id)
        if not user.teacher_profile:
            raise self.not_found("Teacher profile")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user.teacher_profile, field, value)
        self.db.add(user.teacher_profile)
        self.commit()
        return self.refresh(user.teacher_profile)

    def create_student_profile(self, user_id: str, payload: StudentProfileCreate) -> StudentProfile:
        user = self.get_user(user_id)
        if UserRole.STUDENT not in user.roles:
            raise self.bad_request("Student profile can only be created for users with student role")
        if user.student_profile:
            raise self.bad_request("Student profile already exists")
        teacher_id = parse_uuid(payload.created_by_teacher_id, "teacher id") if payload.created_by_teacher_id else None
        if teacher_id:
            teacher = self.db.get(User, teacher_id)
            if not teacher or UserRole.TEACHER not in teacher.roles:
                raise self.bad_request("Created-by teacher not found")
        profile = StudentProfile(
            user_id=user.id,
            created_by_teacher_id=teacher_id,
            parent_name=payload.parent_name,
            parent_phone=payload.parent_phone,
            notes=payload.notes,
            extra_info=payload.extra_info,
        )
        self.db.add(profile)
        self.commit()
        return self.refresh(profile)

    def update_student_profile(self, user_id: str, payload: StudentProfileUpdate) -> StudentProfile:
        user = self.get_user(user_id)
        if not user.student_profile:
            raise self.not_found("Student profile")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user.student_profile, field, value)
        self.db.add(user.student_profile)
        self.commit()
        return self.refresh(user.student_profile)

    def _ensure_email_available(self, email: str, exclude_user_id=None) -> None:
        statement = select(User).where(func.lower(User.email) == email)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        existing = self.db.execute(statement).scalar_one_or_none()
        if existing:
            raise self.bad_request("Email already taken")


def get_user_service(db: Session) -> UserService:
    return UserService(db)
