from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class TelegramLinkResponse(ORMModel):
    bot_username: str | None = None
    link_token: str | None = None
    telegram_link_url: str | None = None
    token_expires_at: datetime | None = None
    is_connected: bool
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_connected_at: datetime | None = None


class TelegramSendCredentialsRequest(ORMModel):
    temporary_password: str | None = Field(default=None, min_length=6, max_length=128)


class TelegramSendCredentialsResponse(ORMModel):
    delivered: bool
    chat_id: str
    sent_at: datetime


class TelegramWebhookSetupRequest(ORMModel):
    public_base_url: str = Field(min_length=1, max_length=500)


class TelegramWebhookSetupResponse(ORMModel):
    ok: bool
    description: str | None = None
    webhook_url: str
