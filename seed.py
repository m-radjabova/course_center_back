from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import UserRole, UserStatus
from app.models.room import Room
from app.models.user import User


def upsert_user(
    db,
    *,
    email: str,
    full_name: str,
    phone: str,
    password: str,
    roles: list[UserRole],
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user is None:
        user = User(email=normalized_email)
        db.add(user)

    user.full_name = full_name
    user.phone = phone
    user.email = normalized_email
    user.password_hash = hash_password(password)
    user.roles = roles
    user.status = status
    return user


def seed_data() -> None:
    db = SessionLocal()
    try:
        # Admin
        admin = upsert_user(
            db,
            email="muslima@gmail.com",
            full_name="Muslima Radjabova",
            phone="+998912345678",
            password="12345678",
            roles=[UserRole.ADMIN, UserRole.TEACHER],
        )

        # Hasan Rasulov
        hasan = upsert_user(
            db,
            email="rasulov420@gmail.com",
            full_name="Hasan Rasulov",
            phone="+998931373027",
            password="qwerty123",
            roles=[UserRole.ADMIN, UserRole.TEACHER],  # xohlasang USER yoki boshqa role qilamiz
        )

        db.commit()

        print("Seed completed successfully.")
        print("Admin: muslima@gmail.com / 12345678")
        print("Hasan: rasulov42@gmail.com / qwerty123")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()