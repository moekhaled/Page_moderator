import hashlib
import hmac
import json
from datetime import datetime, timezone

from app.config import settings
from app.schemas import NormalizedMessage


def verify_meta_signature(signature_header: str | None, body: bytes) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(settings.meta_app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_messages(payload: dict) -> list[NormalizedMessage]:
    normalized: list[NormalizedMessage] = []
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            message = event.get("message", {})
            sender_id = str(event.get("sender", {}).get("id", ""))
            recipient_id = str(event.get("recipient", {}).get("id", ""))
            ts_ms = int(event.get("timestamp", 0))
            event_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms else datetime.now(timezone.utc)
            attachments = []
            for item in message.get("attachments", []) or []:
                payload_data = item.get("payload", {}) if isinstance(item, dict) else {}
                attachments.append(
                    {
                        "type": item.get("type") if isinstance(item, dict) else None,
                        "url": payload_data.get("url"),
                    }
                )
            platform_mid = message.get("mid")
            if sender_id and recipient_id:
                event_key = f"{platform_mid or 'nomid'}:{sender_id}:{recipient_id}:{ts_ms}"
                normalized.append(
                    NormalizedMessage(
                        event_key=event_key,
                        platform_message_id=platform_mid,
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        event_timestamp=event_dt,
                        text=message.get("text"),
                        attachments=attachments,
                    )
                )
    return normalized
