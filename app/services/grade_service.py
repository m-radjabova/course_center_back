from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.grade import Grade
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.grades import GradeCreate, GradeUpdate
from app.services.base import BaseService, parse_uuid
from app.services.telegram_service import TelegramService


class GradeService(BaseService):
    def _ensure_lesson_access(self, lesson: Lesson, current_user: User) -> Lesson:
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN):
            group = lesson.group if hasattr(lesson, "group") else None
            teacher_id = group.teacher_id if group else None
            if teacher_id != current_user.id:
                raise self.forbidden("You can only access grades for your assigned groups")
        return lesson

    def list_grades(
        self,
        current_user: User,
        lesson_id: str | None = None,
        student_id: str | None = None,
    ) -> list[Grade]:
        statement = select(Grade).options(
            joinedload(Grade.student).joinedload(User.student_profile),
            joinedload(Grade.teacher).joinedload(User.teacher_profile),
            joinedload(Grade.lesson).joinedload(Lesson.group),
        ).order_by(Grade.created_at.desc())
        if lesson_id:
            statement = statement.where(Grade.lesson_id == parse_uuid(lesson_id, "lesson id"))
        if student_id:
            statement = statement.where(Grade.student_id == parse_uuid(student_id, "student id"))
        grades = list(self.db.execute(statement).scalars().unique())
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN):
            grades = [grade for grade in grades if grade.lesson.group.teacher_id == current_user.id]
        return grades

    def give_grade(self, payload: GradeCreate, current_user: User) -> Grade:
        lesson = self.db.execute(
            select(Lesson).options(joinedload(Lesson.group)).where(Lesson.id == parse_uuid(payload.lesson_id, "lesson id"))
        ).scalar_one_or_none()
        if not lesson:
            raise self.bad_request("Lesson not found")
        self._ensure_lesson_access(lesson, current_user)
        enrollment = self.db.get(Enrollment, parse_uuid(payload.enrollment_id, "enrollment id"))
        if not enrollment:
            raise self.bad_request("Enrollment not found")
        if enrollment.group_id != lesson.group_id or enrollment.student_id != parse_uuid(payload.student_id, "student id"):
            raise self.bad_request("Grade payload does not match lesson enrollment")
        existing = self.db.execute(
            select(Grade).where(
                Grade.lesson_id == lesson.id,
                Grade.student_id == parse_uuid(payload.student_id, "student id"),
            )
        ).scalar_one_or_none()
        if existing:
            raise self.bad_request("Grade already saved for this student")
        data = payload.model_dump()
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN):
            data["teacher_id"] = current_user.id
        grade = Grade(**data)
        self.db.add(grade)
        self.commit()
        created_grade = self.get_grade(str(grade.id), current_user)
        TelegramService(self.db).notify_new_grade(created_grade)
        return created_grade

    def get_grade(self, grade_id: str, current_user: User) -> Grade:
        grade = self.db.execute(
            select(Grade)
            .options(
                joinedload(Grade.student).joinedload(User.student_profile),
                joinedload(Grade.teacher).joinedload(User.teacher_profile),
                joinedload(Grade.lesson).joinedload(Lesson.group),
            )
            .where(Grade.id == parse_uuid(grade_id, "grade id"))
        ).scalar_one_or_none()
        if not grade:
            raise self.not_found("Grade")
        self._ensure_lesson_access(grade.lesson, current_user)
        return grade

    def update_grade(self, grade_id: str, payload: GradeUpdate, current_user: User) -> Grade:
        self.get_grade(grade_id, current_user)
        raise self.bad_request("Saved grade cannot be changed")


def get_grade_service(db: Session) -> GradeService:
    return GradeService(db)
