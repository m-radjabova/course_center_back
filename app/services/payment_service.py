from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enrollment import Enrollment
from app.models.group import Group
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payments import PaymentCreate, PaymentUpdate
from app.services.base import BaseService, parse_uuid
from app.services.telegram_service import TelegramService


class PaymentService(BaseService):
    def list_payments(self, student_id: str | None = None, group_id: str | None = None) -> list[Payment]:
        statement = select(Payment).options(joinedload(Payment.student).joinedload(User.student_profile)).order_by(
            Payment.paid_at.desc()
        )
        if student_id:
            statement = statement.where(Payment.student_id == parse_uuid(student_id, "student id"))
        if group_id:
            statement = statement.where(Payment.group_id == parse_uuid(group_id, "group id"))
        return list(self.db.execute(statement).scalars().unique())

    def add_payment(self, payload: PaymentCreate) -> Payment:
        group_id = parse_uuid(payload.group_id, "group id")
        student_id = parse_uuid(payload.student_id, "student id")
        group = self.db.get(Group, group_id)
        if not group:
            raise self.bad_request("Group not found")
        enrollment = None
        if payload.enrollment_id:
            enrollment = self.db.get(Enrollment, parse_uuid(payload.enrollment_id, "enrollment id"))
            if not enrollment:
                raise self.bad_request("Enrollment not found")
            if enrollment.group_id != group_id or enrollment.student_id != student_id:
                raise self.bad_request("Payment payload does not match enrollment")
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
            raise self.not_found("Payment")
        return payment

    def update_payment(self, payment_id: str, payload: PaymentUpdate) -> Payment:
        payment = self.get_payment(payment_id)
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
