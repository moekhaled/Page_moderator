from datetime import datetime

from pydantic import BaseModel


class NormalizedMessage(BaseModel):
    event_key: str
    platform_message_id: str | None
    sender_id: str
    recipient_id: str
    event_timestamp: datetime
    text: str | None
    attachments: list[dict]


class MessageView(BaseModel):
    id: int
    direction: str
    author_type: str
    author_id: str
    text: str | None
    created_at: datetime
