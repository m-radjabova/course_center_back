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
    @staticmethod
    def _attendance_has_meaningful_changes(existing: Attendance, payload: AttendanceCreate) -> bool:
        return any(
            (
                existing.status != payload.status,
                (existing.note or "") != (payload.note or ""),
                existing.enrollment_id != parse_uuid(payload.enrollment_id, "enrollment id"),
            )
        )

    def _get_lesson_for_write(self, lesson_id: str, current_user: User) -> Lesson:
        lesson = self.db.execute(
            select(Lesson).options(joinedload(Lesson.group)).where(Lesson.id == parse_uuid(lesson_id, "lesson id"))
        ).scalar_one_or_none()
        if not lesson:
            raise self.bad_request("Dars topilmadi")
        self._ensure_lesson_access(lesson, current_user)
        return lesson

    def _validate_enrollment(self, enrollment: Enrollment | None, lesson: Lesson, student_id: str) -> None:
        if not enrollment:
            raise self.bad_request("Ro'yxatdan o'tish ma'lumoti topilmadi")
        if enrollment.group_id != lesson.group_id or enrollment.student_id != parse_uuid(student_id, "student id"):
            raise self.bad_request("Davomat ma'lumoti dars ro'yxati bilan mos kelmadi")

    def _list_attendance_by_ids(self, attendance_ids: list[str]) -> list[Attendance]:
        if not attendance_ids:
            return []
        attendance_uuid_ids = [parse_uuid(attendance_id, "attendance id") for attendance_id in attendance_ids]
        statement = (
            select(Attendance)
            .options(
                joinedload(Attendance.student).joinedload(User.student_profile),
                joinedload(Attendance.lesson).joinedload(Lesson.group),
            )
            .where(Attendance.id.in_(attendance_uuid_ids))
            .order_by(Attendance.para.asc(), Attendance.created_at.asc())
        )
        records = list(self.db.execute(statement).scalars().unique())
        order = {attendance_id: index for index, attendance_id in enumerate(attendance_ids)}
        records.sort(key=lambda item: order.get(str(item.id), len(order)))
        return records

    def _ensure_lesson_access(self, lesson: Lesson, current_user: User) -> Lesson:
        self.ensure_same_course_center(current_user, lesson.group.course_center_id, "Dars")
        if self.is_teacher_limited(current_user):
            group = lesson.group if hasattr(lesson, "group") else None
            teacher_id = group.teacher_id if group else None
            if teacher_id != current_user.id:
                raise self.forbidden("Siz faqat o'zingizga biriktirilgan guruhlar davomatini ko'ra olasiz")
        return lesson

    def list_attendance(self, lesson_id: str, current_user: User) -> list[Attendance]:
        lesson = self.db.execute(
            select(Lesson).options(joinedload(Lesson.group)).where(Lesson.id == parse_uuid(lesson_id, "lesson id"))
        ).scalar_one_or_none()
        if not lesson:
            raise self.not_found("Dars")
        self._ensure_lesson_access(lesson, current_user)
        statement = (
            select(Attendance)
            .options(joinedload(Attendance.student).joinedload(User.student_profile))
            .where(Attendance.lesson_id == lesson.id)
            .order_by(Attendance.para.asc(), Attendance.created_at.asc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def mark_attendance(self, payload: AttendanceCreate, current_user: User) -> Attendance:
        lesson = self._get_lesson_for_write(str(payload.lesson_id), current_user)
        enrollment = self.db.get(Enrollment, parse_uuid(payload.enrollment_id, "enrollment id"))
        self._validate_enrollment(enrollment, lesson, str(payload.student_id))
        existing = self.db.execute(
            select(Attendance).where(
                Attendance.lesson_id == lesson.id,
                Attendance.student_id == parse_uuid(payload.student_id, "student id"),
                Attendance.para == payload.para,
            )
        ).scalar_one_or_none()
        if existing:
            raise self.bad_request(f"Bu student uchun {payload.para}-para davomat allaqachon saqlangan")
        attendance = Attendance(**payload.model_dump())
        self.db.add(attendance)
        self.commit()
        created_attendance = self.get_attendance(str(attendance.id), current_user)
        TelegramService(self.db).notify_new_attendance(created_attendance)
        return created_attendance

    def bulk_upsert_attendance(self, payloads: list[AttendanceCreate], current_user: User) -> list[Attendance]:
        if not payloads:
            return []

        lesson_ids = {str(payload.lesson_id) for payload in payloads}
        if len(lesson_ids) != 1:
            raise self.bad_request("Bulk davomat faqat bitta dars uchun yuborilishi kerak")

        lesson = self._get_lesson_for_write(next(iter(lesson_ids)), current_user)

        request_keys = [(str(payload.student_id), payload.para) for payload in payloads]
        if len(request_keys) != len(set(request_keys)):
            raise self.bad_request("Bir student va para uchun takroriy davomat yuborildi")

        enrollment_ids = [parse_uuid(payload.enrollment_id, "enrollment id") for payload in payloads]
        enrollments = {
            str(enrollment.id): enrollment
            for enrollment in self.db.execute(
                select(Enrollment).where(Enrollment.id.in_(enrollment_ids))
            ).scalars()
        }

        student_ids = [parse_uuid(payload.student_id, "student id") for payload in payloads]
        paras = sorted({payload.para for payload in payloads})
        existing_records = {
            (str(record.student_id), record.para): record
            for record in self.db.execute(
                select(Attendance).where(
                    Attendance.lesson_id == lesson.id,
                    Attendance.student_id.in_(student_ids),
                    Attendance.para.in_(paras),
                )
            ).scalars()
        }

        changed_ids: list[str] = []
        for payload in payloads:
            enrollment = enrollments.get(str(payload.enrollment_id))
            self._validate_enrollment(enrollment, lesson, str(payload.student_id))

            existing = existing_records.get((str(payload.student_id), payload.para))
            if existing:
                if not self._attendance_has_meaningful_changes(existing, payload):
                    continue
                existing.status = payload.status
                existing.note = payload.note
                existing.enrollment_id = parse_uuid(payload.enrollment_id, "enrollment id")
                self.db.add(existing)
                changed_ids.append(str(existing.id))
                continue

            attendance = Attendance(**payload.model_dump())
            self.db.add(attendance)
            self.db.flush()
            existing_records[(str(payload.student_id), payload.para)] = attendance
            changed_ids.append(str(attendance.id))

        self.commit()

        updated_records = self._list_attendance_by_ids(changed_ids)
        telegram_service = TelegramService(self.db)
        for record in updated_records:
            telegram_service.notify_new_attendance(record)
        return updated_records

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
            raise self.not_found("Davomat")
        self._ensure_lesson_access(attendance.lesson, current_user)
        return attendance

    def update_attendance(self, attendance_id: str, payload: AttendanceUpdate, current_user: User) -> Attendance:
        attendance = self.get_attendance(attendance_id, current_user)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return attendance

        next_para = update_data.get("para", attendance.para)
        if next_para != attendance.para:
            conflicting_attendance = self.db.execute(
                select(Attendance).where(
                    Attendance.lesson_id == attendance.lesson_id,
                    Attendance.student_id == attendance.student_id,
                    Attendance.para == next_para,
                    Attendance.id != attendance.id,
                )
            ).scalar_one_or_none()
            if conflicting_attendance:
                raise self.bad_request(f"Bu student uchun {next_para}-para davomat allaqachon saqlangan")

        for field, value in update_data.items():
            setattr(attendance, field, value)

        self.db.add(attendance)
        self.commit()
        return self.get_attendance(str(attendance.id), current_user)


def get_attendance_service(db: Session) -> AttendanceService:
    return AttendanceService(db)
