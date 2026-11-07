import runpy
from pathlib import Path

from fastapi.testclient import TestClient


def test_vercel_entrypoint_starts_and_accepts_webhooks(monkeypatch):
    secret = "b" * 64
    monkeypatch.setenv("BOT_TOKEN", "123456789:" + "a" * 35)
    monkeypatch.setenv("WEBHOOK_SECRET", secret)
    path = Path(__file__).resolve().parents[2] / "app.py"
    app = runpy.run_path(str(path))["app"]
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200
        assert client.post("/telegram/webhook", json={"update_id": 1}).status_code == 403
        response = client.post(
            "/telegram/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        )
        assert response.status_code == 200
    assert app.state.ready is False
