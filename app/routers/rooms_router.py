from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.rooms import RoomCreate, RoomResponse, RoomUpdate
from app.services.catalog_service import RoomService

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("/", response_model=list[RoomResponse])
def list_rooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return RoomService(db).list_rooms(current_user)


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return RoomService(db).create_room(payload, current_user)


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return RoomService(db).get_room(room_id, current_user)


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(room_id: str, payload: RoomUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return RoomService(db).update_room(room_id, payload, current_user)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    RoomService(db).delete_room(room_id, current_user)
