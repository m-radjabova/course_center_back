from __future__ import annotations

from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance
from app.models.grade import Grade
from app.models.lesson import Lesson
from app.models.payment import Payment
from app.models.user import User
from app.services.base import BaseService, parse_uuid


class StudentDashboardService(BaseService):
    def get_student_portal_snapshot(self, student_id: str, year: int, month: int) -> dict:
        student_uuid = parse_uuid(student_id, "student id")
        period_start = date(year, month, 1)
        period_end = date(year, month, monthrange(year, month)[1])

        student = self.db.execute(
            select(User).where(User.id == student_uuid).options(joinedload(User.student_profile))
        ).scalar_one_or_none()
        if not student:
            raise self.not_found("Student")

        attendance_records = list(
            self.db.execute(
                select(Attendance)
                .options(joinedload(Attendance.lesson))
                .where(
                    Attendance.student_id == student_uuid,
                    Attendance.lesson.has(Lesson.lesson_date >= period_start),
                    Attendance.lesson.has(Lesson.lesson_date <= period_end),
                )
            ).scalars().unique()
        )
        grades = list(
            self.db.execute(
                select(Grade)
                .options(joinedload(Grade.lesson), joinedload(Grade.teacher))
                .where(
                    Grade.student_id == student_uuid,
                    Grade.lesson.has(Lesson.lesson_date >= period_start),
                    Grade.lesson.has(Lesson.lesson_date <= period_end),
                )
            ).scalars().unique()
        )
        payments = list(
            self.db.execute(
                select(Payment)
                .where(Payment.student_id == student_uuid, Payment.month_for == period_start)
                .order_by(Payment.paid_at.desc())
            ).scalars()
        )

        return {
            "student": student,
            "attendance": attendance_records,
            "grades": grades,
            "payments": payments,
            "period": {"year": year, "month": month},
        }


def get_student_dashboard_service(db: Session) -> StudentDashboardService:
    return StudentDashboardService(db)
