from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.order import OrderCreate, OrderOut, OrderProductOut, OrderProductOutDash, OrderStatusUpdate
from app.services import order_service

from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_roles

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("/", response_model=list[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "chef", "waiter")),
):
    return order_service.get_orders(db) 

@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return order_service.create_order(db, user.id, data)


@router.get("/my", response_model=list[OrderOut])
def my_orders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return order_service.get_my_orders(db, user.id)


@router.get("/{order_id}", response_model=OrderOut)
def order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return order_service.get_order_for_user(db, order_id, user.id)


@router.patch("/{order_id}/status", response_model=OrderOut)
def change_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "chef", "waiter")),
):
    return order_service.update_order_status(db, order_id, body.status, user)


@router.get("/products/all", response_model=list[OrderProductOutDash])
def all_order_products(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "chef", "waiter")),
):
    return order_service.get_all_order_products(db)