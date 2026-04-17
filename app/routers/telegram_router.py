from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.roles import require_admin, require_teacher_or_admin
from app.models.user import User
from app.schemas.telegram import (
    TelegramLinkResponse,
    TelegramSendCredentialsRequest,
    TelegramSendCredentialsResponse,
    TelegramWebhookSetupRequest,
    TelegramWebhookSetupResponse,
)
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/students/{user_id}/link", response_model=TelegramLinkResponse)
def generate_student_telegram_link(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return TelegramService(db).generate_student_link(user_id)


@router.get("/students/{user_id}/link", response_model=TelegramLinkResponse)
def get_student_telegram_link_status(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return TelegramService(db).get_student_link_status(user_id)


@router.post("/students/{user_id}/send-credentials", response_model=TelegramSendCredentialsResponse)
def send_student_credentials_to_telegram(
    user_id: str,
    payload: TelegramSendCredentialsRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return TelegramService(db).send_credentials(user_id, payload.temporary_password)


@router.post("/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        return {"ok": False}
    update = await request.json()
    return TelegramService(db).handle_webhook(update)


@router.post("/webhook/set", response_model=TelegramWebhookSetupResponse)
def set_telegram_webhook(
    payload: TelegramWebhookSetupRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return TelegramService(db).set_webhook(payload.public_base_url)
