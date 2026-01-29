from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def check_email(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None


def check_name(db: Session, name: str) -> bool:
    return db.query(User).filter(User.name == name).first() is not None


def create_user(db: Session, user: UserCreate):
    if check_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    if check_name(db, user.name):
        raise HTTPException(status_code=400, detail="Name already taken")

    new_user = User(
        email=user.email,
        name=user.name,
        hashed_password=hash_password(user.password),
        roles=["user"],
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
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
        if check_email(db, update_data["email"]):
            raise HTTPException(status_code=400, detail="Email already registered")

    if "name" in update_data and update_data["name"] != db_user.name:
        if check_name(db, update_data["name"]):
            raise HTTPException(status_code=400, detail="Name already taken")

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