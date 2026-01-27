import os
import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.carousel import Carousel

UPLOAD_DIR = "app/static/uploads/carousels"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_carousel_image(image: UploadFile) -> str:
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only jpg/png/webp images allowed")

    ext = os.path.splitext(image.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(image.file.read())

    return f"/static/uploads/carousels/{filename}"


def get_carousels(db: Session):
    return db.query(Carousel).order_by(Carousel.created_at.desc()).all()


def get_carousel(db: Session, carousel_id: str):
    return db.query(Carousel).filter(Carousel.id == carousel_id).first()


def create_carousel(db: Session, data, image: UploadFile):
    if not image:
        raise HTTPException(status_code=400, detail="Image is required")

    img_url = save_carousel_image(image)

    carousel = Carousel(
        id=uuid.uuid4().hex,   # sizda id String, shuning uchun uuid.hex
        title1=data.title1,
        title2=data.title2,
        description=data.description,
        img=img_url,
    )
    db.add(carousel)
    db.commit()
    db.refresh(carousel)
    return carousel


def update_carousel(db: Session, carousel_id: str, data, image: UploadFile | None):
    carousel = get_carousel(db, carousel_id)
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found")

    if image:
        carousel.img = save_carousel_image(image)

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(carousel, k, v)

    db.commit()
    db.refresh(carousel)
    return carousel


def delete_carousel(db: Session, carousel_id: str):
    carousel = get_carousel(db, carousel_id)
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found")

    db.delete(carousel)
    db.commit()
