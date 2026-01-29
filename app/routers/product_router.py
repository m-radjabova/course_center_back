from typing import List
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ReviewCreate, ReviewOut, ReviewOut
from app.services import product_service
from app.dependencies.roles import require_admin

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    name: str = Form(...),
    price: int = Form(...),
    category_id: int = Form(...),
    description: str | None = Form(None),
    weight: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    data = ProductCreate(
        name=name,
        price=price,
        category_id=category_id,
        description=description,
        weight=weight
    )
    return product_service.create_product(db, data, image)


@router.post("/{product_id}/reviews")
def add_review(
    product_id: str,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return product_service.create_review(db, product_id, user.id, data)


@router.get("/", response_model=list[ProductOut])
def list_products(
    category_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    return product_service.get_products(db, category_id=category_id)

@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    return product_service.get_product(db, product_id)


@router.get("/{product_id}/reviews", response_model=List[ReviewOut],)
def get_reviews(
    product_id: str,
    db: Session = Depends(get_db),
):
    return product_service.get_product_reviews(db, product_id)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    name: str | None = Form(None),
    price: int | None = Form(None),
    category_id: int | None = Form(None),
    description: str | None = Form(None),
    weight: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    data = ProductUpdate(
        name=name,
        price=price,
        category_id=category_id,
        description=description,
        weight=weight,
    )
    return product_service.update_product(db, product_id, data, image)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    product_service.delete_product(db, product_id)
    return