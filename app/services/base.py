from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import UserRole


class ServiceError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class BaseService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def not_found(entity: str) -> ServiceError:
        return ServiceError(status.HTTP_404_NOT_FOUND, f"{entity} topilmadi")

    @staticmethod
    def bad_request(message: str) -> ServiceError:
        return ServiceError(status.HTTP_400_BAD_REQUEST, message)

    @staticmethod
    def forbidden(message: str) -> ServiceError:
        return ServiceError(status.HTTP_403_FORBIDDEN, message)

    @staticmethod
    def is_super_admin(user) -> bool:
        return bool(user and user.has_role(UserRole.SUPER_ADMIN))

    @classmethod
    def is_admin_level(cls, user) -> bool:
        return bool(user and user.has_any_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))

    @classmethod
    def is_teacher_limited(cls, user) -> bool:
        return bool(user and user.has_role(UserRole.TEACHER) and not cls.is_admin_level(user))

    @classmethod
    def require_course_center_id(cls, user) -> UUID:
        if cls.is_super_admin(user):
            raise cls.bad_request("Super admin uchun course center konteksti alohida tanlanishi kerak")
        if not user or not getattr(user, "course_center_id", None):
            raise cls.forbidden("Foydalanuvchi hech qaysi course centerga biriktirilmagan")
        return parse_uuid(user.course_center_id, "course center id")

    @classmethod
    def ensure_same_course_center(cls, current_user, entity_course_center_id, entity_name: str = "Ma'lumot") -> None:
        if cls.is_super_admin(current_user):
            return
        current_center_id = cls.require_course_center_id(current_user)
        target_center_id = parse_uuid(entity_course_center_id, "course center id")
        if current_center_id != target_center_id:
            raise cls.forbidden(f"{entity_name} boshqa course centerga tegishli")

    def commit(self):
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise self.bad_request(self._get_constraint_message(exc)) from exc

    def refresh(self, instance):
        self.db.refresh(instance)
        return instance

    @staticmethod
    def _get_constraint_message(exc: IntegrityError) -> str:
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)
        raw_message = str(getattr(exc, "orig", exc)).lower()

        if constraint_name == "uq_groups_course_name" or "uq_groups_course_name" in raw_message:
            return "Bu kurs ichida shu nomdagi guruh allaqachon mavjud"

        if constraint_name == "rooms_name_key" or "rooms_name_key" in raw_message:
            return "Bu nomdagi xona allaqachon mavjud"

        if constraint_name == "uq_rooms_course_center_name" or "uq_rooms_course_center_name" in raw_message:
            return "Bu course center ichida shu nomdagi xona allaqachon mavjud"

        if constraint_name == "uq_courses_course_center_name" or "uq_courses_course_center_name" in raw_message:
            return "Bu course center ichida shu nomdagi kurs allaqachon mavjud"

        if "groups_course_id_fkey" in raw_message:
            return "Tanlangan kurs topilmadi"

        if "groups_teacher_id_fkey" in raw_message:
            return "Tanlangan teacher topilmadi"

        if "groups_room_id_fkey" in raw_message:
            return "Tanlangan xona topilmadi"

        return "Ma'lumotlar cheklovi buzildi"


def parse_uuid(value: str | UUID, field_name: str = "id") -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ServiceError(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{field_name} noto'g'ri") from exc
