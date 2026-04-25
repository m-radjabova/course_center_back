from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.group import Group
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payments import PaymentCreate, PaymentUpdate
from app.services.base import BaseService, parse_uuid
from app.services.telegram_service import TelegramService


class PaymentService(BaseService):
    def list_payments(self, current_user: User, student_id: str | None = None, group_id: str | None = None) -> list[Payment]:
        statement = (
            select(Payment)
            .options(
                joinedload(Payment.student).joinedload(User.student_profile),
                joinedload(Payment.group),
            )
            .join(Payment.group)
            .order_by(Payment.paid_at.desc())
        )
        if student_id:
            statement = statement.where(Payment.student_id == parse_uuid(student_id, "student id"))
        if group_id:
            statement = statement.where(Payment.group_id == parse_uuid(group_id, "group id"))

        if current_user.has_role(UserRole.STUDENT):
            statement = statement.where(Payment.student_id == current_user.id)
        elif not self.is_super_admin(current_user):
            statement = statement.where(Group.course_center_id == self.require_course_center_id(current_user))
            if self.is_teacher_limited(current_user):
                statement = statement.where(Group.teacher_id == current_user.id)

        return list(self.db.execute(statement).scalars().unique())

    def add_payment(self, payload: PaymentCreate, current_user: User) -> Payment:
        group_id = parse_uuid(payload.group_id, "group id")
        student_id = parse_uuid(payload.student_id, "student id")
        group = self.db.get(Group, group_id)
        if not group:
            raise self.bad_request("Guruh topilmadi")
        self.ensure_same_course_center(current_user, group.course_center_id, "Guruh")
        if self.is_teacher_limited(current_user) and group.teacher_id != current_user.id:
            raise self.forbidden("Siz faqat o'zingizga biriktirilgan guruhlar uchun to'lov qo'sha olasiz")

        student = self.db.get(User, student_id)
        if not student or not student.has_role(UserRole.STUDENT):
            raise self.bad_request("Student topilmadi")
        self.ensure_same_course_center(current_user, student.course_center_id, "Student")

        enrollment = None
        if payload.enrollment_id:
            enrollment = self.db.get(Enrollment, parse_uuid(payload.enrollment_id, "enrollment id"))
            if not enrollment:
                raise self.bad_request("Ro'yxatdan o'tish ma'lumoti topilmadi")
            self.ensure_same_course_center(current_user, enrollment.group.course_center_id, "Ro'yxatdan o'tish")
            if enrollment.group_id != group_id or enrollment.student_id != student_id:
                raise self.bad_request("To'lov ma'lumoti ro'yxatdan o'tish ma'lumoti bilan mos kelmadi")
        payment = Payment(
            student_id=student_id,
            group_id=group_id,
            enrollment_id=enrollment.id if enrollment else None,
            amount=payload.amount,
            paid_at=payload.paid_at,
            month_for=date(payload.month_for.year, payload.month_for.month, 1),
            method=payload.method,
            status=payload.status,
            note=payload.note,
        )
        self.db.add(payment)
        self.commit()
        created_payment = self.get_payment(str(payment.id))
        TelegramService(self.db).notify_new_payment(created_payment)
        return created_payment

    def get_payment(self, payment_id: str) -> Payment:
        payment = self.db.execute(
            select(Payment)
            .options(joinedload(Payment.student).joinedload(User.student_profile))
            .where(Payment.id == parse_uuid(payment_id, "payment id"))
        ).scalar_one_or_none()
        if not payment:
            raise self.not_found("To'lov")
        return payment

    def update_payment(self, payment_id: str, payload: PaymentUpdate, current_user: User) -> Payment:
        payment = self.get_payment(payment_id)
        self.ensure_same_course_center(current_user, payment.group.course_center_id, "To'lov")
        if self.is_teacher_limited(current_user) and payment.group.teacher_id != current_user.id:
            raise self.forbidden("Siz faqat o'zingizga biriktirilgan guruhlar to'lovini yangilay olasiz")
        data = payload.model_dump(exclude_unset=True)
        if "month_for" in data and data["month_for"] is not None:
            data["month_for"] = date(data["month_for"].year, data["month_for"].month, 1)
        for field, value in data.items():
            setattr(payment, field, value)
        self.db.add(payment)
        self.commit()
        return self.get_payment(str(payment.id))


def get_payment_service(db: Session) -> PaymentService:
    return PaymentService(db)
