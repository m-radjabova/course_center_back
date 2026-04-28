from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, verify_password
from app.models.course_center import CourseCenter
from app.models.enums import UserRole
from app.models.profile import StudentProfile, TeacherProfile
from app.models.user import User
from app.schemas.profiles import StudentProfileCreate, StudentProfileUpdate, TeacherProfileCreate, TeacherProfileUpdate
from app.schemas.users import CurrentUserUpdate, UserCreate, UserUpdate
from app.services.base import BaseService, parse_uuid


class UserService(BaseService):
    def _user_options(self):
        return (
            selectinload(User.student_profile),
            selectinload(User.teacher_profile),
            selectinload(User.course_center),
        )

    def _base_user_statement(self):
        return select(User).options(*self._user_options())

    def _get_course_center(self, course_center_id) -> CourseCenter:
        course_center = self.db.get(CourseCenter, parse_uuid(course_center_id, "course center id"))
        if not course_center:
            raise self.bad_request("Course center topilmadi")
        return course_center

    def _get_default_course_center(self) -> CourseCenter:
        course_center = self.db.execute(
            select(CourseCenter).order_by(CourseCenter.created_at.asc()).limit(1)
        ).scalar_one_or_none()
        if not course_center:
            raise self.bad_request("Tizimda hech qanday course center mavjud emas")
        return course_center

    def _resolve_target_course_center_id(self, requested_course_center_id, current_user: User | None) -> str:
        if requested_course_center_id:
            target_course_center = self._get_course_center(requested_course_center_id)
            if current_user and not self.is_super_admin(current_user):
                self.ensure_same_course_center(current_user, target_course_center.id, "Course center")
            return str(target_course_center.id)

        if current_user and not self.is_super_admin(current_user):
            return str(self.require_course_center_id(current_user))

        return str(self._get_default_course_center().id)

    def _ensure_single_admin_per_course_center(
        self,
        target_roles: list[UserRole],
        course_center_id: str,
        exclude_user_id=None,
    ) -> None:
        if UserRole.ADMIN not in target_roles:
            return

        statement = select(User).where(
            User.course_center_id == parse_uuid(course_center_id, "course center id"),
            User.roles.contains([UserRole.ADMIN.value]),
        )
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)

        existing_admin = self.db.execute(statement).scalar_one_or_none()
        if existing_admin:
            raise self.bad_request("Har bir course center uchun faqat bitta admin biriktirilishi mumkin")

    def _ensure_role_assignment_allowed(
        self,
        target_roles: list[UserRole],
        current_user: User | None,
        existing_user: User | None = None,
    ) -> None:
        if UserRole.SUPER_ADMIN in target_roles and not (current_user and self.is_super_admin(current_user)):
            raise self.forbidden("Super admin rolini faqat super admin bera oladi")

        if UserRole.ADMIN in target_roles and current_user and not self.is_super_admin(current_user):
            raise self.forbidden("Admin rolini faqat super admin bera oladi")

        if existing_user and self.is_super_admin(existing_user) and not (current_user and self.is_super_admin(current_user)):
            raise self.forbidden("Super admin foydalanuvchini boshqarish mumkin emas")

    def list_users(self, current_user: User, role: UserRole | None = None) -> list[User]:
        statement = self._base_user_statement()
        if role:
            statement = statement.where(User.roles.contains([role.value]))
        if not self.is_super_admin(current_user):
            statement = statement.where(User.course_center_id == self.require_course_center_id(current_user))
        statement = statement.order_by(User.created_at.desc())
        return list(self.db.execute(statement).scalars().unique())

    def get_user(self, user_id: str, current_user: User | None = None) -> User:
        user = self.db.execute(
            self._base_user_statement()
            .where(User.id == parse_uuid(user_id, "user id"))
        ).scalar_one_or_none()
        if not user:
            raise self.not_found("Foydalanuvchi")
        if current_user is not None:
            self.ensure_same_course_center(current_user, user.course_center_id, "Foydalanuvchi")
        return user

    def create_user(self, payload: UserCreate, current_user: User | None = None) -> User:
        email = payload.email.strip().lower()
        self._ensure_email_available(email)
        self._ensure_role_assignment_allowed(payload.roles, current_user)
        target_course_center_id = self._resolve_target_course_center_id(payload.course_center_id, current_user)
        self._ensure_single_admin_per_course_center(payload.roles, target_course_center_id)
        user = User(
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            email=email,
            password_hash=hash_password(payload.password),
            course_center_id=target_course_center_id,
            roles=payload.roles,
            status=payload.status,
        )
        self.db.add(user)
        self.commit()
        return self.get_user(str(user.id), current_user if current_user else user)

    def update_user(self, user_id: str, payload: UserUpdate, current_user: User) -> User:
        user = self.get_user(user_id, current_user)
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
        next_roles = data["roles"] if "roles" in data and data["roles"] is not None else user.roles
        next_course_center_id = (
            self._resolve_target_course_center_id(data["course_center_id"], current_user)
            if "course_center_id" in data and data["course_center_id"] is not None
            else str(user.course_center_id)
        )
        self._ensure_role_assignment_allowed(next_roles, current_user, existing_user=user)
        self._ensure_single_admin_per_course_center(next_roles, next_course_center_id, exclude_user_id=user.id)
        if "roles" in data and data["roles"] is not None:
            user.roles = next_roles
        if "course_center_id" in data and data["course_center_id"] is not None:
            user.course_center_id = next_course_center_id
        self.db.add(user)
        self.commit()
        return self.get_user(str(user.id), current_user)

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
            raise self.bad_request("Joriy parol noto'g'ri")
        if current_password == new_password:
            raise self.bad_request("Yangi parol joriy paroldan farq qilishi kerak")
        user.password_hash = hash_password(new_password)
        self.db.add(user)
        self.commit()
        return self.refresh(user)

    def reset_password(self, user_id: str, new_password: str, current_user: User) -> User:
        user = self.get_user(user_id, current_user)
        user.password_hash = hash_password(new_password)
        self.db.add(user)
        self.commit()
        return self.get_user(str(user.id), current_user)

    def create_teacher_profile(self, user_id: str, payload: TeacherProfileCreate, current_user: User) -> TeacherProfile:
        user = self.get_user(user_id, current_user)
        if UserRole.TEACHER not in user.roles:
            raise self.bad_request("O'qituvchi profili faqat o'qituvchi roli bor foydalanuvchi uchun yaratiladi")
        if user.teacher_profile:
            raise self.bad_request("O'qituvchi profili allaqachon mavjud")
        profile = TeacherProfile(user_id=user.id, **payload.model_dump())
        self.db.add(profile)
        self.commit()
        return self.refresh(profile)

    def update_teacher_profile(self, user_id: str, payload: TeacherProfileUpdate, current_user: User) -> TeacherProfile:
        user = self.get_user(user_id, current_user)
        if not user.teacher_profile:
            raise self.not_found("O'qituvchi profili")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user.teacher_profile, field, value)
        self.db.add(user.teacher_profile)
        self.commit()
        return self.refresh(user.teacher_profile)

    def create_student_profile(self, user_id: str, payload: StudentProfileCreate, current_user: User) -> StudentProfile:
        user = self.get_user(user_id, current_user)
        if UserRole.STUDENT not in user.roles:
            raise self.bad_request("Student profili faqat student roli bor foydalanuvchi uchun yaratiladi")
        if user.student_profile:
            raise self.bad_request("Student profili allaqachon mavjud")
        teacher_id = parse_uuid(payload.created_by_teacher_id, "teacher id") if payload.created_by_teacher_id else None
        if teacher_id:
            teacher = self.get_user(str(teacher_id), current_user)
            if not teacher or UserRole.TEACHER not in teacher.roles:
                raise self.bad_request("Biriktirilgan o'qituvchi topilmadi")
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

    def update_student_profile(self, user_id: str, payload: StudentProfileUpdate, current_user: User) -> StudentProfile:
        user = self.get_user(user_id, current_user)
        if not user.student_profile:
            raise self.not_found("Student profili")
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
            raise self.bad_request("Bu email allaqachon band")


def get_user_service(db: Session) -> UserService:
    return UserService(db)
