from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_port(port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError(f"port did not open: {port}")


def terminate(proc: subprocess.Popen[str]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture()
def certs():
    subprocess.run(["bash", "scripts/generate-cert.sh"], cwd=ROOT, check=True, stdout=subprocess.PIPE)


def start_server(port: int) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [sys.executable, "-m", "server.https_server", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    wait_for_port(port)
    return proc


def start_proxy(proxy_port: int, server_port: int, policy_path: Path, log_path: Path) -> subprocess.Popen[str]:
    policy_path.write_text(
        f"""
default_action: block
upstream:
  host: 127.0.0.1
  port: {server_port}
rules:
  - sni: allowed.test
    action: allow
    reason: allowed
  - sni: blocked.test
    action: block
    reason: blocked
""",
        encoding="utf-8",
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "proxy.main",
            "--listen-host",
            "127.0.0.1",
            "--listen-port",
            str(proxy_port),
            "--policy",
            str(policy_path),
            "--log-file",
            str(log_path),
            "--timeout",
            "3",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    wait_for_port(proxy_port)
    return proc


def curl_for(host: str, port: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "curl",
            "--noproxy",
            "*",
            "-sk",
            "--resolve",
            f"{host}:{port}:127.0.0.1",
            f"https://{host}:{port}/",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=8,
    )


def read_events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_allowed_and_blocked_connections(tmp_path, certs):
    server_port = free_port()
    proxy_port = free_port()
    log_path = tmp_path / "proxy.jsonl"
    policy_path = tmp_path / "policy.yaml"
    server_proc = start_server(server_port)
    proxy_proc = start_proxy(proxy_port, server_port, policy_path, log_path)
    try:
        allowed = curl_for("allowed.test", proxy_port)
        blocked = curl_for("blocked.test", proxy_port)
        unknown = curl_for("unknown.test", proxy_port)
    finally:
        terminate(proxy_proc)
        terminate(server_proc)

    assert allowed.returncode == 0
    assert "Local TLS test server" in allowed.stdout
    assert blocked.returncode != 0
    assert unknown.returncode != 0
    events = read_events(log_path)
    decisions = {event["extracted_sni"]: event["decision"] for event in events}
    assert decisions["allowed.test"] == "allow"
    assert decisions["blocked.test"] == "block"
    assert decisions["unknown.test"] == "block"


def test_allowed_when_upstream_is_down_logs_error(tmp_path, certs):
    server_port = free_port()
    proxy_port = free_port()
    log_path = tmp_path / "proxy.jsonl"
    policy_path = tmp_path / "policy.yaml"
    proxy_proc = start_proxy(proxy_port, server_port, policy_path, log_path)
    try:
        result = curl_for("allowed.test", proxy_port)
    finally:
        terminate(proxy_proc)

    assert result.returncode != 0
    event = read_events(log_path)[-1]
    assert event["decision"] == "allow"
    assert event["error"]


def test_proxy_port_collision(tmp_path, certs):
    proxy_port = free_port()
    server_port = free_port()
    log_path = tmp_path / "proxy.jsonl"
    policy_path = tmp_path / "policy.yaml"
    server_proc = start_server(server_port)
    proxy_proc = start_proxy(proxy_port, server_port, policy_path, log_path)
    try:
        duplicate = subprocess.run(
            [
                sys.executable,
                "-m",
                "proxy.main",
                "--listen-host",
                "127.0.0.1",
                "--listen-port",
                str(proxy_port),
                "--policy",
                str(policy_path),
                "--log-file",
                str(tmp_path / "duplicate.jsonl"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
    finally:
        terminate(proxy_proc)
        terminate(server_proc)

    assert duplicate.returncode != 0
    assert "Proxy startup error" in duplicate.stderr
