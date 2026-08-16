from datetime import datetime, timezone

import httpx
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from app.config import settings


class MetaSendClient:
    async def send_text(self, recipient_platform_id: str, text_message: str) -> dict:
        if not settings.meta_page_access_token:
            raise RuntimeError("META_PAGE_ACCESS_TOKEN is required for outbound send")

        url = (
            f"https://graph.facebook.com/{settings.meta_graph_version}/"
            f"{settings.instagram_business_account_id}/messages"
        )
        payload = {
            "recipient": {"id": recipient_platform_id},
            "message": {"text": text_message},
            "messaging_type": "RESPONSE",
        }

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.outbound_max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=20),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(
                        url,
                        params={"access_token": settings.meta_page_access_token},
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    return {
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                        "status_code": response.status_code,
                        "payload": response.json(),
                    }

        raise RuntimeError("Send retry loop exhausted")
