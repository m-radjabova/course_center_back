from collections.abc import Generator
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(override=True)


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value is not None else None


def get_database_url() -> str:
    database_url = _get_env("DATABASE_URL")
    if database_url:
        return database_url

    required_env_vars = ["DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME"]
    env_values = {name: _get_env(name) for name in required_env_vars}
    missing_env_vars = [name for name, value in env_values.items() if not value]
    if missing_env_vars:
        missing = ", ".join(missing_env_vars)
        raise ValueError(
            f"Database configuration is incomplete. Set DATABASE_URL or these env vars: {missing}"
        )

    return (
        f"postgresql+psycopg2://{env_values['DB_USER']}:{env_values['DB_PASS']}"
        f"@{env_values['DB_HOST']}:{env_values['DB_PORT']}/{env_values['DB_NAME']}"
    )


class Base(DeclarativeBase):
    pass


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
