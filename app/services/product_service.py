import os
import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.product import Product

UPLOAD_DIR = "app/static/uploads/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_image(image: UploadFile) -> str:
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    ext = os.path.splitext(image.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(image.file.read())

    return f"/static/uploads/products/{filename}"


def create_product(
    db: Session,
    data,
    image: UploadFile | None
):
    image_url = save_image(image) if image else None

    product = Product(
        id=uuid.uuid4().hex,
        name=data.name,
        description=data.description,
        price=data.price,
        category_id=data.category_id,
        weight=data.weight,
        image=image_url
    )

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_products(db: Session):
    return db.query(Product).all()


def get_product(db: Session, product_id: str):
    return db.query(Product).filter(Product.id == product_id).first()


def update_product(
    db: Session,
    product_id: str,
    data,
    image: UploadFile | None
):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if image:
        product.image = save_image(image)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: str):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
