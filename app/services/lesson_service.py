from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import UserRole
from app.models.group import Group
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.lessons import LessonCreate, LessonUpdate
from app.services.base import BaseService, parse_uuid
from app.services.telegram_service import TelegramService


class LessonService(BaseService):
    def _ensure_group_access(self, group: Group, current_user: User) -> Group:
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN) and group.teacher_id != current_user.id:
            raise self.forbidden("You can only access your assigned groups")
        return group

    def _ensure_unique_lesson_date(
        self,
        group_id: str,
        lesson_date: date,
        exclude_lesson_id: str | None = None,
    ) -> None:
        statement = select(Lesson).where(
            Lesson.group_id == parse_uuid(group_id, "group id"),
            Lesson.lesson_date == lesson_date,
        )
        if exclude_lesson_id:
          statement = statement.where(Lesson.id != parse_uuid(exclude_lesson_id, "lesson id"))

        existing_lesson = self.db.execute(statement).scalar_one_or_none()
        if existing_lesson:
            raise self.bad_request("This group already has a lesson on the selected day")

    def list_lessons(
        self,
        current_user: User,
        group_id: str | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> list[Lesson]:
        statement = select(Lesson).options(joinedload(Lesson.group).joinedload(Group.course)).order_by(
            Lesson.lesson_date.asc(), Lesson.lesson_number.asc()
        )
        if group_id:
            group = self.db.get(Group, parse_uuid(group_id, "group id"))
            if not group:
                raise self.not_found("Group")
            self._ensure_group_access(group, current_user)
            statement = statement.where(Lesson.group_id == group.id)
        elif current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN):
            statement = statement.join(Lesson.group).where(Group.teacher_id == current_user.id)
        if year is not None:
            statement = statement.where(func.extract("year", Lesson.lesson_date) == year)
        if month is not None:
            statement = statement.where(func.extract("month", Lesson.lesson_date) == month)
        return list(self.db.execute(statement).scalars().unique())

    def get_lesson(self, lesson_id: str, current_user: User) -> Lesson:
        lesson = self.db.execute(
            select(Lesson)
            .options(
                joinedload(Lesson.group).joinedload(Group.course),
                joinedload(Lesson.group).joinedload(Group.teacher),
                joinedload(Lesson.group).joinedload(Group.room),
            )
            .where(Lesson.id == parse_uuid(lesson_id, "lesson id"))
        ).scalar_one_or_none()
        if not lesson:
            raise self.not_found("Lesson")
        self._ensure_group_access(lesson.group, current_user)
        return lesson

    def create_lesson(self, payload: LessonCreate, current_user: User) -> Lesson:
        group = self.db.get(Group, parse_uuid(payload.group_id, "group id"))
        if not group:
            raise self.bad_request("Group not found")
        self._ensure_group_access(group, current_user)
        self._ensure_unique_lesson_date(str(payload.group_id), payload.lesson_date)
        data = payload.model_dump()
        if data.get("lesson_number") is None:
            next_lesson_number = self.db.execute(
                select(func.coalesce(func.max(Lesson.lesson_number), 0) + 1).where(Lesson.group_id == group.id)
            ).scalar_one()
            data["lesson_number"] = int(next_lesson_number)

        lesson = Lesson(**data)
        self.db.add(lesson)
        self.commit()
        created_lesson = self.get_lesson(str(lesson.id), current_user)
        TelegramService(self.db).notify_new_lesson(created_lesson)
        return created_lesson

    def update_lesson(self, lesson_id: str, payload: LessonUpdate, current_user: User) -> Lesson:
        lesson = self.get_lesson(lesson_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "lesson_date" in data and data["lesson_date"] is not None:
            self._ensure_unique_lesson_date(str(lesson.group_id), data["lesson_date"], exclude_lesson_id=lesson_id)
        for field, value in data.items():
            setattr(lesson, field, value)
        self.db.add(lesson)
        self.commit()
        return self.get_lesson(str(lesson.id), current_user)


def get_lesson_service(db: Session) -> LessonService:
    return LessonService(db)
