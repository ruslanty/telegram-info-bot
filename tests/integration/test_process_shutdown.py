"""Real localhost process: in-flight request completes before session cleanup."""

import os
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

SERVER = """
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Message
from telegram_info_bot.app import create_app
from telegram_info_bot.config import Settings

async def send(*args, **kwargs):
    Path("started").touch()
    await asyncio.sleep(0.5)
    return Message.model_validate({"message_id": 2, "date": 1,
                                   "chat": {"id": 42, "type": "private"}})
async def close():
    Path("closed").touch()
session = AiohttpSession()
session.make_request = AsyncMock(side_effect=send)
session.close = close
app = create_app(Settings("123456789:" + "a" * 35, "b" * 64),
                 bot=Bot("123456789:" + "a" * 35, session=session))
"""


def wait_until(check, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        assert process.poll() is None, "Server exited before the check completed"
        try:
            if check():
                return
        except httpx.TransportError:
            pass
        time.sleep(0.02)
    raise AssertionError("Server check timed out")


def test_graceful_shutdown_drains_request_and_restart_works(tmp_path):
    (tmp_path / "fixture_app.py").write_text(SERVER)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "fixture_app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--timeout-graceful-shutdown",
        "3",
    ]
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = f"http://127.0.0.1:{port}"
    for stop_signal in (signal.SIGTERM, signal.SIGINT):
        for marker in ("started", "closed"):
            (tmp_path / marker).unlink(missing_ok=True)
        process = subprocess.Popen(
            command, cwd=tmp_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            with httpx.Client(timeout=10, trust_env=False) as client:
                wait_until(lambda: client.get(base + "/health/ready").status_code == 200, process)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    pending = executor.submit(
                        client.post,
                        base + "/telegram/webhook",
                        headers={"X-Telegram-Bot-Api-Secret-Token": "b" * 64},
                        json={
                            "update_id": 1,
                            "message": {
                                "message_id": 1,
                                "date": 1,
                                "chat": {"id": 42, "type": "private"},
                                "text": "/start",
                                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                            },
                        },
                    )
                    wait_until(lambda: (tmp_path / "started").exists(), process)
                    process.send_signal(stop_signal)
                    assert pending.result().status_code == 200
            assert process.wait(timeout=10) in (0, -stop_signal)
            assert (tmp_path / "closed").exists()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
