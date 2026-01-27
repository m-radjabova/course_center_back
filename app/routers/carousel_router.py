from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.carousel import CarouselCreate, CarouselUpdate, CarouselOut
from app.services import carousel_service
from app.dependencies.roles import require_admin

router = APIRouter(prefix="/carousels", tags=["Carousels"])


@router.get("/", response_model=list[CarouselOut])
def list_carousels(db: Session = Depends(get_db)):
    return carousel_service.get_carousels(db)


@router.get("/{carousel_id}", response_model=CarouselOut)
def get_carousel(carousel_id: str, db: Session = Depends(get_db)):
    return carousel_service.get_carousel(db, carousel_id)


@router.post("/", response_model=CarouselOut, status_code=status.HTTP_201_CREATED)
def create_carousel(
    title1: str = Form(...),
    title2: str = Form(...),
    description: str | None = Form(None),
    img: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    data = CarouselCreate(title1=title1, title2=title2, description=description)
    return carousel_service.create_carousel(db, data, img)


@router.put("/{carousel_id}", response_model=CarouselOut)
def update_carousel(
    carousel_id: str,
    title1: str | None = Form(None),
    title2: str | None = Form(None),
    description: str | None = Form(None),
    img: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    data = CarouselUpdate(title1=title1, title2=title2, description=description)
    return carousel_service.update_carousel(db, carousel_id, data, img)


@router.delete("/{carousel_id}", status_code=204)
def delete_carousel(
    carousel_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    carousel_service.delete_carousel(db, carousel_id)
    return
