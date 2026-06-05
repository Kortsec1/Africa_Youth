from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import time

from proxy.logging_config import JsonLineLogger
from proxy.policy import PolicyError, load_policy
from proxy.relay import relay_streams
from proxy.sni_parser import ClientHelloParseError, extract_sni


READ_LIMIT = 65536


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, policy, logger: JsonLineLogger, timeout: float) -> None:
    started = time.perf_counter()
    peer = writer.get_extra_info("peername")
    client_address = f"{peer[0]}:{peer[1]}" if peer else "unknown"
    sni = None
    decision = None
    error = None
    c2u = 0
    u2c = 0
    upstream_writer = None
    try:
        first = await asyncio.wait_for(reader.read(READ_LIMIT), timeout=timeout)
        if not first:
            raise ClientHelloParseError("empty client stream")
        try:
            sni = extract_sni(first)
        except ClientHelloParseError as exc:
            error = str(exc)
        decision = policy.decide(sni)
        if decision.action == "allow":
            upstream_reader, upstream_writer = await asyncio.wait_for(
                asyncio.open_connection(policy.upstream_host, policy.upstream_port),
                timeout=timeout,
            )
            upstream_writer.write(first)
            await upstream_writer.drain()
            c2u, u2c = await asyncio.wait_for(
                relay_streams(reader, writer, upstream_reader, upstream_writer),
                timeout=timeout,
            )
            c2u += len(first)
        else:
            writer.close()
            await writer.wait_closed()
    except Exception as exc:
        error = error or str(exc)
        if upstream_writer is not None:
            upstream_writer.close()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_address": client_address,
            "extracted_sni": sni,
            "decision": decision.action if decision else "error",
            "reason": decision.reason if decision else "정책 결정 실패",
            "upstream_host": policy.upstream_host,
            "upstream_port": policy.upstream_port,
            "elapsed_ms": elapsed_ms,
            "bytes_client_to_upstream": c2u,
            "bytes_upstream_to_client": u2c,
            "error": error,
        }
        logger.write(event)
        print(f"{event['timestamp']} {client_address} sni={sni} decision={event['decision']} error={error}")


async def run_proxy(args: argparse.Namespace) -> None:
    try:
        policy = load_policy(args.policy)
    except PolicyError as exc:
        raise SystemExit(f"Policy error: {exc}") from exc
    logger = JsonLineLogger(args.log_file)
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, policy, logger, args.timeout),
        args.listen_host,
        args.listen_port,
    )
    addr = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Policy proxy listening on {addr}; upstream={policy.upstream_host}:{policy.upstream_port}")
    async with server:
        await server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local SNI policy proxy")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=9443)
    parser.add_argument("--policy", default="configs/policy.yaml")
    parser.add_argument("--log-file", default="logs/proxy.jsonl")
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    try:
        asyncio.run(run_proxy(parse_args()))
    except OSError as exc:
        raise SystemExit(f"Proxy startup error: {exc}") from exc


if __name__ == "__main__":
    main()
