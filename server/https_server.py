from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import errno
import ssl
import threading


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalTLSTestServer/0.1"

    def do_GET(self) -> None:
        body = json.dumps(
            {
                "status": "ok",
                "message": "Local TLS test server",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{datetime.now(timezone.utc).isoformat()} {self.client_address[0]} {format % args}")


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local HTTPS test server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--cert", default="server/certs/server.crt")
    parser.add_argument("--key", default="server/certs/server.key")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cert = Path(args.cert)
    key = Path(args.key)
    if not cert.exists() or not key.exists():
        raise SystemExit("Certificate files are missing. Run ./scripts/generate-cert.sh first.")

    try:
        httpd = ReusableThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise SystemExit(
                f"Server startup error: {args.host}:{args.port} is already in use. "
                "Stop the existing process or pass a different --port."
            ) from exc
        raise SystemExit(f"Server startup error: {exc}") from exc
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert, keyfile=key)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    def stop(_signum: int, _frame: object) -> None:
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"HTTPS test server listening on https://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
