import os

from fastapi.testclient import TestClient

os.environ["SESSION_SECRET_KEY"] = "test-secret"
os.environ["META_VERIFY_TOKEN"] = "verify-me"
os.environ["META_APP_SECRET"] = "app-secret"

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

settings.meta_verify_token = "verify-me"

client = TestClient(app)


def test_webhook_verify_success():
    response = client.get(
        "/webhook/meta",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "12345",
            "hub.verify_token": "verify-me",
        },
    )
    assert response.status_code == 200
    assert response.text == "12345"
