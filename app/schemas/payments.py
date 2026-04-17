from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.enums import PaymentMethod, PaymentStatus
from app.schemas.profiles import StudentDetailResponse


class PaymentBase(ORMModel):
    student_id: UUID
    group_id: UUID
    enrollment_id: UUID | None = None
    amount: Decimal = Field(ge=0)
    paid_at: datetime
    month_for: date
    method: PaymentMethod
    status: PaymentStatus
    note: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(ORMModel):
    amount: Decimal | None = Field(default=None, ge=0)
    paid_at: datetime | None = None
    month_for: date | None = None
    method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    note: str | None = None


class PaymentResponse(TimestampedSchema, PaymentBase):
    student: StudentDetailResponse
