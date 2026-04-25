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
    @staticmethod
    def _resolve_teacher_id(payload: GradeCreate, current_user: User):
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_any_role(UserRole.SUPER_ADMIN, UserRole.ADMIN):
            return current_user.id
        return parse_uuid(payload.teacher_id, "teacher id") if payload.teacher_id else None

    @classmethod
    def _grade_has_meaningful_changes(cls, existing: Grade, payload: GradeCreate, current_user: User) -> bool:
        next_teacher_id = cls._resolve_teacher_id(payload, current_user)
        next_enrollment_id = parse_uuid(payload.enrollment_id, "enrollment id")
        return any(
            (
                existing.score != payload.score,
                (existing.note or "") != (payload.note or ""),
                existing.enrollment_id != next_enrollment_id,
                existing.teacher_id != next_teacher_id,
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
            raise self.bad_request("Baho ma'lumoti dars ro'yxati bilan mos kelmadi")

    def _list_grades_by_ids(self, grade_ids: list[str]) -> list[Grade]:
        if not grade_ids:
            return []
        grade_uuid_ids = [parse_uuid(grade_id, "grade id") for grade_id in grade_ids]
        statement = (
            select(Grade)
            .options(
                joinedload(Grade.student).joinedload(User.student_profile),
                joinedload(Grade.teacher).joinedload(User.teacher_profile),
                joinedload(Grade.lesson).joinedload(Lesson.group),
            )
            .where(Grade.id.in_(grade_uuid_ids))
            .order_by(Grade.created_at.desc())
        )
        grades = list(self.db.execute(statement).scalars().unique())
        order = {grade_id: index for index, grade_id in enumerate(grade_ids)}
        grades.sort(key=lambda item: order.get(str(item.id), len(order)))
        return grades

    def _ensure_lesson_access(self, lesson: Lesson, current_user: User) -> Lesson:
        self.ensure_same_course_center(current_user, lesson.group.course_center_id, "Dars")
        if self.is_teacher_limited(current_user):
            group = lesson.group if hasattr(lesson, "group") else None
            teacher_id = group.teacher_id if group else None
            if teacher_id != current_user.id:
                raise self.forbidden("Siz faqat o'zingizga biriktirilgan guruhlar baholarini ko'ra olasiz")
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
        if not self.is_super_admin(current_user):
            grades = [grade for grade in grades if str(grade.lesson.group.course_center_id) == str(current_user.course_center_id)]
        if self.is_teacher_limited(current_user):
            grades = [grade for grade in grades if grade.lesson.group.teacher_id == current_user.id]
        return grades

    def give_grade(self, payload: GradeCreate, current_user: User) -> Grade:
        lesson = self._get_lesson_for_write(str(payload.lesson_id), current_user)
        enrollment = self.db.get(Enrollment, parse_uuid(payload.enrollment_id, "enrollment id"))
        self._validate_enrollment(enrollment, lesson, str(payload.student_id))
        existing = self.db.execute(
            select(Grade).where(
                Grade.lesson_id == lesson.id,
                Grade.student_id == parse_uuid(payload.student_id, "student id"),
            )
        ).scalar_one_or_none()
        if existing:
            raise self.bad_request("Bu student uchun baho allaqachon saqlangan")
        data = payload.model_dump()
        if self.is_teacher_limited(current_user):
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
            raise self.not_found("Baho")
        self._ensure_lesson_access(grade.lesson, current_user)
        return grade

    def update_grade(self, grade_id: str, payload: GradeUpdate, current_user: User) -> Grade:
        grade = self.get_grade(grade_id, current_user)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return grade

        if self.is_teacher_limited(current_user):
            update_data["teacher_id"] = current_user.id

        for field, value in update_data.items():
            setattr(grade, field, value)

        self.db.add(grade)
        self.commit()
        updated_grade = self.get_grade(str(grade.id), current_user)
        TelegramService(self.db).notify_new_grade(updated_grade)
        return updated_grade

    def bulk_upsert_grades(self, payloads: list[GradeCreate], current_user: User) -> list[Grade]:
        if not payloads:
            return []

        lesson_ids = {str(payload.lesson_id) for payload in payloads}
        if len(lesson_ids) != 1:
            raise self.bad_request("Bulk baho faqat bitta dars uchun yuborilishi kerak")

        lesson = self._get_lesson_for_write(next(iter(lesson_ids)), current_user)

        student_ids_as_text = [str(payload.student_id) for payload in payloads]
        if len(student_ids_as_text) != len(set(student_ids_as_text)):
            raise self.bad_request("Bir student uchun takroriy baho yuborildi")

        enrollment_ids = [parse_uuid(payload.enrollment_id, "enrollment id") for payload in payloads]
        enrollments = {
            str(enrollment.id): enrollment
            for enrollment in self.db.execute(
                select(Enrollment).where(Enrollment.id.in_(enrollment_ids))
            ).scalars()
        }

        student_ids = [parse_uuid(payload.student_id, "student id") for payload in payloads]
        existing_grades = {
            str(grade.student_id): grade
            for grade in self.db.execute(
                select(Grade).where(
                    Grade.lesson_id == lesson.id,
                    Grade.student_id.in_(student_ids),
                )
            ).scalars()
        }

        changed_ids: list[str] = []
        for payload in payloads:
            enrollment = enrollments.get(str(payload.enrollment_id))
            self._validate_enrollment(enrollment, lesson, str(payload.student_id))

            existing = existing_grades.get(str(payload.student_id))
            if existing:
                if not self._grade_has_meaningful_changes(existing, payload, current_user):
                    continue
                existing.score = payload.score
                existing.note = payload.note
                existing.enrollment_id = parse_uuid(payload.enrollment_id, "enrollment id")
                if self.is_teacher_limited(current_user):
                    existing.teacher_id = current_user.id
                else:
                    existing.teacher_id = payload.teacher_id
                self.db.add(existing)
                changed_ids.append(str(existing.id))
                continue

            data = payload.model_dump()
            if self.is_teacher_limited(current_user):
                data["teacher_id"] = current_user.id
            grade = Grade(**data)
            self.db.add(grade)
            self.db.flush()
            existing_grades[str(payload.student_id)] = grade
            changed_ids.append(str(grade.id))

        self.commit()

        updated_grades = self._list_grades_by_ids(changed_ids)
        telegram_service = TelegramService(self.db)
        for grade in updated_grades:
            telegram_service.notify_new_grade(grade)
        return updated_grades


def get_grade_service(db: Session) -> GradeService:
    return GradeService(db)
