from __future__ import annotations

import math

from typing import cast

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import hash_password
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus, GroupStatus, UserRole, UserStatus
from app.models.group import Group
from app.models.profile import StudentProfile
from app.models.user import User
from app.schemas.enrollments import BulkEnrollmentCreate, EnrollmentCreate, EnrollmentUpdate
from app.schemas.profiles import StudentProfileCreate
from app.schemas.users import UserCreate
from app.services.base import BaseService, parse_uuid
from app.services.user_service import UserService


class StudentService(BaseService):
    def create_student(self, user_payload: UserCreate, profile_payload: StudentProfileCreate, current_user: User) -> User:
        if UserRole.STUDENT not in user_payload.roles:
            raise self.bad_request("Yaratilayotgan foydalanuvchida student roli bo'lishi kerak")

        email = user_payload.email.strip().lower()
        UserService(self.db)._ensure_email_available(email)

        teacher_id = parse_uuid(profile_payload.created_by_teacher_id, "teacher id") if profile_payload.created_by_teacher_id else None
        if teacher_id:
            teacher = UserService(self.db).get_user(str(teacher_id), current_user)
            if not teacher or UserRole.TEACHER not in teacher.roles:
                raise self.bad_request("Biriktirilgan o'qituvchi topilmadi")

        user = User(
            full_name=user_payload.full_name.strip(),
            phone=user_payload.phone,
            email=email,
            password_hash=hash_password(user_payload.password),
            course_center_id=UserService(self.db)._resolve_target_course_center_id(
                user_payload.course_center_id,
                current_user,
            ),
            roles=user_payload.roles,
            status=user_payload.status,
        )
        self.db.add(user)
        self.db.flush()

        profile = StudentProfile(
            user_id=user.id,
            created_by_teacher_id=teacher_id,
            parent_name=profile_payload.parent_name,
            parent_phone=profile_payload.parent_phone,
            notes=profile_payload.notes,
            extra_info=profile_payload.extra_info,
        )
        self.db.add(profile)
        self.commit()
        return UserService(self.db).get_user(str(user.id), current_user)

    def _student_filters(self, current_user: User, search: str | None = None, unassigned_only: bool = False):
        filters = [User.roles.contains([UserRole.STUDENT.value])]

        if not self.is_super_admin(current_user):
            filters.append(User.course_center_id == self.require_course_center_id(current_user))

        if unassigned_only:
            filters.append(
                ~exists(
                    select(Enrollment.id).where(Enrollment.student_id == User.id)
                )
            )

        cleaned_search = (search or "").strip()
        if cleaned_search:
            search_like = f"%{cleaned_search}%"
            filters.append(
                or_(
                    User.full_name.ilike(search_like),
                    User.email.ilike(search_like),
                    User.phone.ilike(search_like),
                    User.student_profile.has(StudentProfile.parent_phone.ilike(search_like)),
                )
            )

        return filters

    def list_students_paginated(
        self,
        current_user: User,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        unassigned_only: bool = False,
    ) -> dict[str, int | list[User]]:
        filters = self._student_filters(current_user=current_user, search=search, unassigned_only=unassigned_only)

        total = int(
            self.db.execute(
                select(func.count()).select_from(User).where(*filters)
            ).scalar_one()
            or 0
        )
        active_total = int(
            self.db.execute(
                select(func.count())
                .select_from(User)
                .where(*filters, User.status == UserStatus.ACTIVE)
            ).scalar_one()
            or 0
        )

        pages = max(1, math.ceil(total / limit)) if limit > 0 else 1
        safe_page = min(max(page, 1), pages)
        offset = (safe_page - 1) * limit

        statement = (
            select(User)
            .options(
                selectinload(User.student_profile),
                selectinload(User.enrollments).selectinload(Enrollment.group),
                selectinload(User.course_center),
            )
            .where(*filters)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self.db.execute(statement).scalars().unique())

        return {
            "items": items,
            "total": total,
            "active_total": active_total,
            "page": safe_page,
            "limit": limit,
            "pages": pages,
        }

    def list_students(self, current_user: User) -> list[User]:
        payload = self.list_students_paginated(current_user=current_user, page=1, limit=10_000)
        return cast(list[User], payload["items"])

    def list_unassigned_students(self, current_user: User) -> list[User]:
        statement = (
            select(User)
            .options(
                selectinload(User.student_profile),
                selectinload(User.enrollments).selectinload(Enrollment.group),
                selectinload(User.course_center),
            )
            .where(User.roles.contains([UserRole.STUDENT.value]))
            .where(
                ~exists(
                    select(Enrollment.id).where(Enrollment.student_id == User.id)
                )
            )
            .order_by(User.created_at.desc())
        )
        if not self.is_super_admin(current_user):
            statement = statement.where(User.course_center_id == self.require_course_center_id(current_user))
        return list(self.db.execute(statement).scalars().unique())

    def _get_valid_student(self, student_id: str, current_user: User | None = None) -> User:
        student = self.db.execute(
            select(User)
            .options(
                selectinload(User.student_profile),
                selectinload(User.enrollments).selectinload(Enrollment.group),
                selectinload(User.course_center),
            )
            .where(User.id == parse_uuid(student_id, "student id"))
        ).scalar_one_or_none()
        if not student or UserRole.STUDENT not in student.roles:
            raise self.bad_request("Student topilmadi")
        if current_user is not None:
            self.ensure_same_course_center(current_user, student.course_center_id, "Student")
        return student

    def get_student(self, student_id: str, current_user: User) -> User:
        return self._get_valid_student(student_id, current_user)

    def _get_active_group(self, group_id: str, current_user: User | None = None) -> Group:
        group = self.db.get(Group, parse_uuid(group_id, "group id"))
        if not group:
            raise self.bad_request("Guruh topilmadi")
        if group.status != GroupStatus.ACTIVE:
            raise self.bad_request("Faqat faol guruhlarga yangi student qo'shish mumkin")
        if current_user is not None:
            self.ensure_same_course_center(current_user, group.course_center_id, "Guruh")
        return group

    def _ensure_group_access(self, group: Group, current_user: User) -> Group:
        self.ensure_same_course_center(current_user, group.course_center_id, "Guruh")
        if self.is_teacher_limited(current_user) and group.teacher_id != current_user.id:
            raise self.forbidden("Siz faqat o'zingizga biriktirilgan guruhlarni ko'ra olasiz")
        return group

    def enroll_student(self, payload: EnrollmentCreate, current_user: User) -> Enrollment:
        self._get_valid_student(str(payload.student_id), current_user)
        self._get_active_group(str(payload.group_id), current_user)
        existing_enrollment = self.db.execute(
            select(Enrollment).where(
                Enrollment.student_id == parse_uuid(payload.student_id, "student id"),
                Enrollment.group_id == parse_uuid(payload.group_id, "group id"),
            )
        ).scalar_one_or_none()
        if existing_enrollment:
            raise self.bad_request("Student bu guruhga allaqachon biriktirilgan")
        enrollment = Enrollment(**payload.model_dump())
        self.db.add(enrollment)
        self.commit()
        return self.get_enrollment(str(enrollment.id))

    def bulk_enroll_students(self, payload: BulkEnrollmentCreate, current_user: User) -> list[Enrollment]:
        self._get_active_group(str(payload.group_id), current_user)
        unique_student_ids = list(dict.fromkeys(payload.student_ids))

        enrollments: list[Enrollment] = []
        for student_id in unique_student_ids:
            self._get_valid_student(str(student_id), current_user)

            existing_enrollment = self.db.execute(
                select(Enrollment.id).where(
                    Enrollment.student_id == parse_uuid(student_id, "student id"),
                    Enrollment.group_id == parse_uuid(payload.group_id, "group id"),
                )
            ).scalar_one_or_none()
            if existing_enrollment:
                raise self.bad_request("Tanlangan studentlardan biri bu guruhga allaqachon biriktirilgan")

            enrollment = Enrollment(
                student_id=student_id,
                group_id=payload.group_id,
                enrolled_at=payload.enrolled_at,
                status=payload.status,
            )
            self.db.add(enrollment)
            enrollments.append(enrollment)

        self.commit()
        return [self.get_enrollment(str(enrollment.id)) for enrollment in enrollments]

    def get_enrollment(self, enrollment_id: str) -> Enrollment:
        enrollment = self.db.execute(
            select(Enrollment)
            .options(
                joinedload(Enrollment.student).joinedload(User.student_profile),
                joinedload(Enrollment.group).joinedload(Group.course),
                joinedload(Enrollment.group).joinedload(Group.teacher),
                joinedload(Enrollment.group).joinedload(Group.room),
            )
            .where(Enrollment.id == parse_uuid(enrollment_id, "enrollment id"))
        ).scalar_one_or_none()
        if not enrollment:
            raise self.not_found("Ro'yxatdan o'tish ma'lumoti")
        return enrollment

    def list_group_enrollments(self, group_id: str, current_user: User) -> list[Enrollment]:
        group = self.db.get(Group, parse_uuid(group_id, "group id"))
        if not group:
            raise self.not_found("Guruh")
        self._ensure_group_access(group, current_user)
        statement = (
            select(Enrollment)
            .options(
                joinedload(Enrollment.student).joinedload(User.student_profile),
                joinedload(Enrollment.group).joinedload(Group.course),
                joinedload(Enrollment.group).joinedload(Group.teacher),
                joinedload(Enrollment.group).joinedload(Group.room),
            )
            .where(Enrollment.group_id == parse_uuid(group_id, "group id"))
            .order_by(Enrollment.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def update_enrollment(self, enrollment_id: str, payload: EnrollmentUpdate, current_user: User) -> Enrollment:
        enrollment = self.get_enrollment(enrollment_id)
        self.ensure_same_course_center(current_user, enrollment.group.course_center_id, "Ro'yxatdan o'tish")
        data = payload.model_dump(exclude_unset=True)
        if data.get("status") == EnrollmentStatus.LEFT and not data.get("left_at") and not enrollment.left_at:
            raise self.bad_request("Status chiqarilgan bo'lsa, chiqish sanasi kiritilishi shart")
        for field, value in data.items():
            setattr(enrollment, field, value)
        self.db.add(enrollment)
        self.commit()
        return self.get_enrollment(str(enrollment.id))


def get_student_service(db: Session) -> StudentService:
    return StudentService(db)
