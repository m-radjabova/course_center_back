from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_teacher_or_admin
from app.models.user import User
from app.schemas.payments import PaymentCreate, PaymentResponse, PaymentUpdate
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/", response_model=list[PaymentResponse])
def list_payments(
    student_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PaymentService(db).list_payments(current_user, student_id, group_id)


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def add_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return PaymentService(db).add_payment(payload, current_user)


@router.patch("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: str,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return PaymentService(db).update_payment(payment_id, payload, current_user)
