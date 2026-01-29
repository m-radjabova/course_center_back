import os
import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.product import Product
from app.models.review import Review
from app.schemas.product import ReviewCreate 

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


def _product_to_out(product: Product, avg_rating: float, rating_count: int) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "category_id": product.category_id,
        "image": product.image,
        "weight": product.weight,
        "created_at": product.created_at,
        "rating": float(avg_rating or 0),
        "rating_count": int(rating_count or 0),
    }


def create_product(db: Session, data, image: UploadFile | None):
    image_url = save_image(image) if image else None

    product = Product(
        id=uuid.uuid4().hex,
        name=data.name,
        description=data.description,
        price=data.price,
        category_id=data.category_id,
        weight=data.weight,
        image=image_url,
        # rating=0  # shart emas, default bor
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    # yangi product => hali review yo‘q
    return _product_to_out(product, 0, 0)


def get_products(db: Session, category_id: int | None = None):
    q = (
        db.query(
            Product,
            func.coalesce(func.avg(Review.rating), 0).label("avg_rating"),
            func.count(Review.id).label("rating_count"),
        )
        .outerjoin(Review, Review.product_id == Product.id)
    )

    if category_id is not None:
        q = q.filter(Product.category_id == category_id)

    rows = q.group_by(Product.id).all()

    return [
        _product_to_out(product, avg_rating, rating_count)
        for product, avg_rating, rating_count in rows
    ]

def get_product(db: Session, product_id: str):
    row = (
        db.query(
            Product,
            func.coalesce(func.avg(Review.rating), 0).label("avg_rating"),
            func.count(Review.id).label("rating_count"),
        )
        .outerjoin(Review, Review.product_id == Product.id)
        .filter(Product.id == product_id)
        .group_by(Product.id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    product, avg_rating, rating_count = row
    return _product_to_out(product, avg_rating, rating_count)


def update_product(db: Session, product_id: str, data, image: UploadFile | None):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if image:
        product.image = save_image(image)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)

    # update dan keyin ham rating reviewsdan olinadi
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.product_id == product_id).scalar() or 0
    rating_count = db.query(func.count(Review.id)).filter(Review.product_id == product_id).scalar() or 0

    return _product_to_out(product, avg_rating, rating_count)


def delete_product(db: Session, product_id: str):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

def get_product_reviews(db: Session, product_id: str):
    exists = db.query(Product.id).filter(Product.id == product_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Product not found")

    return (
        db.query(Review)
        .filter(Review.product_id == product_id)
        .order_by(Review.created_at.desc())
        .all()
    )



def create_review(
    db: Session,
    product_id: str,
    user_id,
    data: ReviewCreate
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    exists = (
        db.query(Review)
        .filter(
            Review.product_id == product_id,
            Review.user_id == user_id
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="You already reviewed this product")

    review = Review(
        title=data.title,
        rating=data.rating,
        user_id=user_id,
        product_id=product_id,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return review
