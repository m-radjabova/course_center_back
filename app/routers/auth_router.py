from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel
from uuid import uuid4

from app.core.database import get_db
from app.core.config import settings
from app.core.jwt import create_token, decode_token
from app.core.security import hash_password, verify_password
from app.services.user_service import authenticate_user, normalize_email, save_refresh_token_hash
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.core import firebase  

from firebase_admin import auth

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginSchema(BaseModel):
    email: str
    password: str


class RefreshSchema(BaseModel):
    refresh_token: str


class GoogleAuthSchema(BaseModel):
    id_token: str


def _make_unique_username(db: Session, base_username: str) -> str:
    clean_base = (base_username or "user").strip().lower().replace(" ", "")
    if not clean_base:
        clean_base = "user"

    candidate = clean_base
    counter = 1

    while db.query(User).filter(User.username == candidate).first():
        candidate = f"{clean_base}{counter}"
        counter += 1

    return candidate


@router.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_token(
        payload={"sub": str(user.id), "type": "access", "roles": user.roles},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    refresh_token = create_token(
        payload={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    save_refresh_token_hash(db, user, hash_password(refresh_token))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/google")
def google_login(data: GoogleAuthSchema, db: Session = Depends(get_db)):

    try:
        decoded_token = auth.verify_id_token(data.id_token)
        email = normalize_email(decoded_token["email"])
        display_name = decoded_token.get("name")
        avatar = decoded_token.get("picture")

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        username_seed = display_name or email.split("@")[0]
        username = _make_unique_username(db, username_seed)

        user = User(
            email=email,
            username=username,
            avatar=avatar,
            hashed_password=hash_password(uuid4().hex),
            roles=["teacher"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_token(
        payload={"sub": str(user.id), "type": "access", "roles": user.roles},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    refresh_token = create_token(
        payload={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    save_refresh_token_hash(db, user, hash_password(refresh_token))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh")
def refresh_token(data: RefreshSchema, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.refresh_token_hash or not verify_password(data.refresh_token, user.refresh_token_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_token(
        payload={"sub": str(user.id), "type": "access", "roles": user.roles},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    save_refresh_token_hash(db, current_user, "")
    return {"msg": "Successfully logged out"}
