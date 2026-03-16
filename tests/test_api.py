from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import MessageSchema

client = TestClient(app)


def test_whatsapp_webhook_bad_payload():
    response = client.post("/webhooks/whatsapp", json={"foo": "bar"})
    assert response.status_code == 400


def test_whatsapp_webhook_success(monkeypatch):
    # stub task
    called = {}

    def fake_delay(data):
        called["data"] = data

    from app.tasks import message_tasks

    monkeypatch.setattr(message_tasks.process_incoming_message, "delay", fake_delay)

    payload = MessageSchema(phone="+123", text="I want to sell apples").model_dump()
    response = client.post(
        "/webhooks/whatsapp",
        json=payload,
        headers={"x-api-key": ""},
    )
    assert response.status_code == 200
    assert called["data"] == payload


def test_whatsapp_webhook_invalid_key():
    payload = MessageSchema(phone="+123", text="testing").model_dump()
    response = client.post(
        "/webhooks/whatsapp",
        json=payload,
        headers={"x-api-key": "wrong"},
    )
    assert response.status_code == 403
