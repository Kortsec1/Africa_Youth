from __future__ import annotations

import json
import select
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


def wait_for_stdout(proc: subprocess.Popen[str], expected: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    output = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            if proc.stdout is not None:
                output += proc.stdout.read()
            raise RuntimeError(f"process exited before {expected!r}: {output}")
        if proc.stdout is not None:
            ready, _, _ = select.select([proc.stdout], [], [], 0.05)
            if ready:
                line = proc.stdout.readline()
                output += line
                if expected in line:
                    return
    raise RuntimeError(f"process did not print {expected!r}: {output}")


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
        [sys.executable, "-u", "-m", "server.https_server", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_port(port)
    except RuntimeError as exc:
        output = proc.stdout.read() if proc.stdout is not None else ""
        terminate(proc)
        raise RuntimeError(f"server did not start: {output}") from exc
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
            "-u",
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
    wait_for_stdout(proc, "Policy proxy listening")
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


def wait_for_events(log_path: Path, count: int, timeout: float = 5.0) -> list[dict]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            events = read_events(log_path)
            if len(events) >= count:
                return events
        time.sleep(0.05)
    raise RuntimeError(f"log did not reach {count} events: {log_path}")


def build_client_hello(server_name: str) -> bytes:
    name = server_name.encode("idna")
    server_name_list = b"\x00" + len(name).to_bytes(2, "big") + name
    ext_body = len(server_name_list).to_bytes(2, "big") + server_name_list
    extensions = b"\x00\x00" + len(ext_body).to_bytes(2, "big") + ext_body
    hello = (
        b"\x03\x03"
        + (b"\x00" * 32)
        + b"\x00"
        + b"\x00\x02\x13\x01"
        + b"\x01\x00"
        + len(extensions).to_bytes(2, "big")
        + extensions
    )
    handshake = b"\x01" + len(hello).to_bytes(3, "big") + hello
    return b"\x16\x03\x03" + len(handshake).to_bytes(2, "big") + handshake


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
    allowed_event = next(event for event in events if event["extracted_sni"] == "allowed.test")
    assert allowed_event["connection_outcome"] == "allowed_success"
    assert allowed_event["has_sni"] is True
    assert allowed_event["tls_record_version"] in {"TLS 1.0", "TLS 1.2"}
    assert allowed_event["client_hello_version"] == "TLS 1.2"
    assert allowed_event["handshake_type"] == 1


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
    assert event["connection_outcome"] == "upstream_error"
    assert event["error"]


def test_fragmented_client_hello_is_accumulated_before_policy_decision(tmp_path, certs):
    server_port = free_port()
    proxy_port = free_port()
    log_path = tmp_path / "proxy.jsonl"
    policy_path = tmp_path / "policy.yaml"
    proxy_proc = start_proxy(proxy_port, server_port, policy_path, log_path)
    client_hello = build_client_hello("blocked.test")
    try:
        with socket.create_connection(("127.0.0.1", proxy_port), timeout=5) as sock:
            sock.sendall(client_hello[:3])
            time.sleep(0.05)
            sock.sendall(client_hello[3:])
            sock.shutdown(socket.SHUT_WR)
        event = wait_for_events(log_path, 1)[-1]
    finally:
        terminate(proxy_proc)

    assert event["extracted_sni"] == "blocked.test"
    assert event["decision"] == "block"
    assert event["connection_outcome"] == "blocked"
    assert event["parse_error_type"] is None


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
