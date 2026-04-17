from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.base import BaseService, parse_uuid
from app.services.telegram_service import TelegramService


class AttendanceService(BaseService):
    def _ensure_lesson_access(self, lesson: Lesson, current_user: User) -> Lesson:
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN):
            group = lesson.group if hasattr(lesson, "group") else None
            teacher_id = group.teacher_id if group else None
            if teacher_id != current_user.id:
                raise self.forbidden("You can only access attendance for your assigned groups")
        return lesson

    def list_attendance(self, lesson_id: str, current_user: User) -> list[Attendance]:
        lesson = self.db.execute(
            select(Lesson).options(joinedload(Lesson.group)).where(Lesson.id == parse_uuid(lesson_id, "lesson id"))
        ).scalar_one_or_none()
        if not lesson:
            raise self.not_found("Lesson")
        self._ensure_lesson_access(lesson, current_user)
        statement = (
            select(Attendance)
            .options(joinedload(Attendance.student).joinedload(User.student_profile))
            .where(Attendance.lesson_id == lesson.id)
            .order_by(Attendance.created_at.asc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def mark_attendance(self, payload: AttendanceCreate, current_user: User) -> Attendance:
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
            raise self.bad_request("Attendance payload does not match lesson enrollment")
        existing = self.db.execute(
            select(Attendance).where(
                Attendance.lesson_id == lesson.id,
                Attendance.student_id == parse_uuid(payload.student_id, "student id"),
            )
        ).scalar_one_or_none()
        if existing:
            raise self.bad_request("Attendance already saved for this student")
        attendance = Attendance(**payload.model_dump())
        self.db.add(attendance)
        self.commit()
        created_attendance = self.get_attendance(str(attendance.id), current_user)
        TelegramService(self.db).notify_new_attendance(created_attendance)
        return created_attendance

    def get_attendance(self, attendance_id: str, current_user: User) -> Attendance:
        attendance = self.db.execute(
            select(Attendance)
            .options(
                joinedload(Attendance.student).joinedload(User.student_profile),
                joinedload(Attendance.lesson).joinedload(Lesson.group),
            )
            .where(Attendance.id == parse_uuid(attendance_id, "attendance id"))
        ).scalar_one_or_none()
        if not attendance:
            raise self.not_found("Attendance")
        self._ensure_lesson_access(attendance.lesson, current_user)
        return attendance

    def update_attendance(self, attendance_id: str, payload: AttendanceUpdate, current_user: User) -> Attendance:
        self.get_attendance(attendance_id, current_user)
        raise self.bad_request("Saved attendance cannot be changed")


def get_attendance_service(db: Session) -> AttendanceService:
    return AttendanceService(db)
