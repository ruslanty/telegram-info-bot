"""Build-independent Docker smoke check; uses synthetic credentials, never .env."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


def docker(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True, stderr=subprocess.STDOUT).strip()


def main() -> None:
    image = sys.argv[1] if len(sys.argv) > 1 else "telegram-info-bot:local"
    name = "telegram-info-smoke-" + uuid.uuid4().hex[:12]
    secret = "b" * 64
    docker(
        "run",
        "-d",
        "--name",
        name,
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "-p",
        "127.0.0.1::8000",
        "-e",
        "BOT_TOKEN=123456789:" + "a" * 35,
        "-e",
        "WEBHOOK_SECRET=" + secret,
        image,
    )
    try:
        ports = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", name))
        base = "http://127.0.0.1:" + ports["8000/tcp"][0]["HostPort"]

        def request(path: str, body: bytes | None = None, authenticated: bool = False) -> int:
            headers = {"Content-Type": "application/json"}
            if authenticated:
                headers["X-Telegram-Bot-Api-Secret-Token"] = secret
            req = urllib.request.Request(base + path, data=body, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=2) as response:
                    return response.status
            except urllib.error.HTTPError as error:
                return error.code

        def wait_ready() -> None:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    if request("/health/ready") == 200:
                        return
                except OSError:
                    pass
                time.sleep(0.2)
            raise RuntimeError("Container readiness timed out")

        wait_ready()
        assert request("/health/live") == 200
        assert request("/telegram/webhook", b"{}") == 403
        assert request("/telegram/webhook", b"not json", True) == 400
        assert request("/telegram/webhook", b"{}", True) == 422
        assert request("/telegram/webhook", b'{"update_id": 1}', True) == 200
        docker(
            "exec",
            name,
            "python",
            "-c",
            "import os, pathlib, importlib.util; "
            "assert os.getuid() == 10001; "
            'assert not pathlib.Path("/app/.env").exists(); '
            'assert importlib.util.find_spec("pytest") is None; '
            'assert importlib.util.find_spec("telegram_info_bot") is not None',
        )
        deadline = time.monotonic() + 30
        while docker("inspect", "--format", "{{.State.Health.Status}}", name) != "healthy":
            if time.monotonic() > deadline:
                raise RuntimeError("Docker HEALTHCHECK did not become healthy")
            time.sleep(0.2)
        docker("stop", "--time", "25", name)
        assert docker("inspect", "--format", "{{.State.ExitCode}}", name) in {"0", "143"}
        assert "Application shutdown complete." in docker("logs", name)
        docker("start", name)
        # Docker may allocate another ephemeral host port after restart.
        ports = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", name))
        base = "http://127.0.0.1:" + ports["8000/tcp"][0]["HostPort"]
        wait_ready()
        print(
            "PASS: readiness, webhook, non-root, no dev dependencies/.env, HEALTHCHECK, "
            "SIGTERM and restart"
        )
    finally:
        docker("rm", "-f", name)


if __name__ == "__main__":
    main()
