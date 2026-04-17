from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import hash_password
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus, GroupStatus, UserRole
from app.models.group import Group
from app.models.profile import StudentProfile
from app.models.user import User
from app.schemas.enrollments import BulkEnrollmentCreate, EnrollmentCreate, EnrollmentUpdate
from app.schemas.profiles import StudentProfileCreate
from app.schemas.users import UserCreate
from app.services.base import BaseService, parse_uuid
from app.services.user_service import UserService


class StudentService(BaseService):
    def create_student(self, user_payload: UserCreate, profile_payload: StudentProfileCreate) -> User:
        if UserRole.STUDENT not in user_payload.roles:
            raise self.bad_request("Created user must include student role")

        email = user_payload.email.strip().lower()
        UserService(self.db)._ensure_email_available(email)

        teacher_id = parse_uuid(profile_payload.created_by_teacher_id, "teacher id") if profile_payload.created_by_teacher_id else None
        if teacher_id:
            teacher = self.db.get(User, teacher_id)
            if not teacher or UserRole.TEACHER not in teacher.roles:
                raise self.bad_request("Created-by teacher not found")

        user = User(
            full_name=user_payload.full_name.strip(),
            phone=user_payload.phone,
            email=email,
            password_hash=hash_password(user_payload.password),
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
        return UserService(self.db).get_user(str(user.id))

    def list_students(self) -> list[User]:
        statement = (
            select(User)
            .options(selectinload(User.student_profile))
            .where(User.roles.contains([UserRole.STUDENT.value]))
            .order_by(User.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def list_unassigned_students(self) -> list[User]:
        statement = (
            select(User)
            .options(selectinload(User.student_profile))
            .where(User.roles.contains([UserRole.STUDENT.value]))
            .where(
                ~exists(
                    select(Enrollment.id).where(Enrollment.student_id == User.id)
                )
            )
            .order_by(User.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def _get_valid_student(self, student_id: str) -> User:
        student = self.db.execute(
            select(User).options(selectinload(User.student_profile)).where(User.id == parse_uuid(student_id, "student id"))
        ).scalar_one_or_none()
        if not student or UserRole.STUDENT not in student.roles:
            raise self.bad_request("Student not found")
        return student

    def _get_active_group(self, group_id: str) -> Group:
        group = self.db.get(Group, parse_uuid(group_id, "group id"))
        if not group:
            raise self.bad_request("Group not found")
        if group.status != GroupStatus.ACTIVE:
            raise self.bad_request("Only active groups can accept new students")
        return group

    def _ensure_group_access(self, group: Group, current_user: User) -> Group:
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN) and group.teacher_id != current_user.id:
            raise self.forbidden("You can only access your assigned groups")
        return group

    def enroll_student(self, payload: EnrollmentCreate) -> Enrollment:
        self._get_valid_student(str(payload.student_id))
        self._get_active_group(str(payload.group_id))
        existing_enrollment = self.db.execute(
            select(Enrollment).where(
                Enrollment.student_id == parse_uuid(payload.student_id, "student id"),
                Enrollment.group_id == parse_uuid(payload.group_id, "group id"),
            )
        ).scalar_one_or_none()
        if existing_enrollment:
            raise self.bad_request("Student is already assigned to this group")
        enrollment = Enrollment(**payload.model_dump())
        self.db.add(enrollment)
        self.commit()
        return self.get_enrollment(str(enrollment.id))

    def bulk_enroll_students(self, payload: BulkEnrollmentCreate) -> list[Enrollment]:
        self._get_active_group(str(payload.group_id))

        enrollments: list[Enrollment] = []
        for student_id in payload.student_ids:
            self._get_valid_student(str(student_id))

            has_any_enrollment = self.db.execute(
                select(Enrollment.id).where(Enrollment.student_id == parse_uuid(student_id, "student id"))
            ).scalar_one_or_none()
            if has_any_enrollment:
                raise self.bad_request("One of the selected students is already assigned to a group")

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
            raise self.not_found("Enrollment")
        return enrollment

    def list_group_enrollments(self, group_id: str, current_user: User) -> list[Enrollment]:
        group = self.db.get(Group, parse_uuid(group_id, "group id"))
        if not group:
            raise self.not_found("Group")
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

    def update_enrollment(self, enrollment_id: str, payload: EnrollmentUpdate) -> Enrollment:
        enrollment = self.get_enrollment(enrollment_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("status") == EnrollmentStatus.LEFT and not data.get("left_at") and not enrollment.left_at:
            raise self.bad_request("left_at is required when status is left")
        for field, value in data.items():
            setattr(enrollment, field, value)
        self.db.add(enrollment)
        self.commit()
        return self.get_enrollment(str(enrollment.id))


def get_student_service(db: Session) -> StudentService:
    return StudentService(db)
