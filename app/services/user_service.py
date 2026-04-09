import os
import uuid
import shutil
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

UPLOAD_DIR = "app/static/uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def save_image(image: UploadFile) -> str:
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are allowed",
        )

    ext = ALLOWED_TYPES[image.content_type]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    try:
        with open(path, "wb") as f:
            shutil.copyfileobj(image.file, f)  
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save image")

    return f"/static/uploads/avatars/{filename}"


def delete_old_avatar_if_exists(avatar: str | None):
    if not avatar:
        return
    old_path = avatar.replace("/static/", "app/static/")
    if os.path.exists(old_path):
        try:
            os.remove(old_path)
        except Exception:
            pass


def update_current_user(db: Session, current_user: User, user_data: UserUpdate):
    if user_data.username is not None:
        current_user.username = user_data.username.strip()
    if user_data.email is not None:
        normalized_email = normalize_email(user_data.email)
        existing_user = db.query(User).filter(User.email == normalized_email, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = normalized_email

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user



def update_user_avatar(db: Session, user: User, image: UploadFile):
    delete_old_avatar_if_exists(user.avatar)

    avatar = save_image(image)
    user.avatar = avatar

    db.commit()
    db.refresh(user)
    return user


def check_email(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == normalize_email(email)).first() is not None


def check_name(db: Session, username: str) -> bool:
    return db.query(User).filter(User.username == username).first() is not None


def create_user(db: Session, user: UserCreate):
    normalized_email = normalize_email(user.email)

    if check_email(db, normalized_email):
        raise HTTPException(status_code=400, detail="Email already registered")

    if check_name(db, user.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        email=normalized_email,
        username=user.username,
        hashed_password=hash_password(user.password),
        roles=["teacher"],
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str):
    normalized_email = normalize_email(email)
    user = db.query(User).filter(User.email == normalized_email).first()
    print("EMAIL KELDI:", email)
    print("USER TOPILDI:", bool(user))
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def save_refresh_token_hash(db: Session, user: User, refresh_token_hash: str):
    user.refresh_token_hash = refresh_token_hash
    db.commit()
    db.refresh(user)
    return user


def get_users(db: Session):
    return db.query(User).all()


def get_user_by_id(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: UUID, user_data: UserUpdate):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_data.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != db_user.email:
        normalized_email = normalize_email(update_data["email"])
        if check_email(db, normalized_email):
            raise HTTPException(status_code=400, detail="Email already registered")
        update_data["email"] = normalized_email

    if "username" in update_data and update_data["username"] != db_user.username:
        if check_name(db, update_data["username"]):
            raise HTTPException(status_code=400, detail="Username already taken")

    for key, value in update_data.items():
        if key == "password":
            db_user.hashed_password = hash_password(value)
        else:
            setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_roles(db: Session, user_id: UUID, roles: list[str]):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.roles = roles
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: UUID):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return None


def change_password(db: Session, user: User, new_password: str):
    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def change_my_password(db: Session, user: User, current_password: str, new_password: str):
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user
