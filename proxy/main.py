from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import time

from proxy.logging_config import JsonLineLogger
from proxy.policy import PolicyError, load_policy
from proxy.relay import relay_streams
from proxy.sni_parser import ClientHelloMetadata, ClientHelloParseError, parse_client_hello


READ_LIMIT = 65536


async def read_initial_tls_record(reader: asyncio.StreamReader, timeout: float, max_size: int = READ_LIMIT) -> bytes:
    try:
        header = await asyncio.wait_for(reader.readexactly(5), timeout=timeout)
    except asyncio.IncompleteReadError as exc:
        if not exc.partial:
            raise ClientHelloParseError("empty client stream", "empty_client_stream") from exc
        raise ClientHelloParseError("incomplete TLS record header", "incomplete_tls_record_header") from exc
    if header[0] != 0x16:
        return header
    record_len = int.from_bytes(header[3:5], "big")
    total_len = 5 + record_len
    if total_len > max_size:
        raise ClientHelloParseError("TLS record too large", "tls_record_too_large")
    try:
        body = await asyncio.wait_for(reader.readexactly(record_len), timeout=timeout)
    except asyncio.IncompleteReadError as exc:
        raise ClientHelloParseError("incomplete TLS record body", "incomplete_tls_record_body") from exc
    return header + body


def classify_outcome(decision_action: str | None, error: str | None, parse_error_type: str | None) -> str:
    if parse_error_type:
        return "parse_error"
    if decision_action == "block":
        return "blocked"
    if decision_action == "allow" and error:
        return "upstream_error"
    if decision_action == "allow":
        return "allowed_success"
    return "parse_error"


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, policy, logger: JsonLineLogger, timeout: float) -> None:
    started = time.perf_counter()
    peer = writer.get_extra_info("peername")
    client_address = f"{peer[0]}:{peer[1]}" if peer else "unknown"
    sni = None
    metadata: ClientHelloMetadata | None = None
    decision = None
    error = None
    parse_error_type = None
    c2u = 0
    u2c = 0
    upstream_writer = None
    try:
        first = await read_initial_tls_record(reader, timeout)
        try:
            metadata = parse_client_hello(first)
            sni = metadata.sni
        except ClientHelloParseError as exc:
            error = str(exc)
            parse_error_type = exc.code
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
    except ClientHelloParseError as exc:
        error = error or str(exc)
        parse_error_type = parse_error_type or exc.code
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
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
        decision_action = decision.action if decision else "error"
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_address": client_address,
            "extracted_sni": sni,
            "has_sni": metadata.has_sni if metadata else False,
            "decision": decision_action,
            "reason": decision.reason if decision else "정책 결정 실패",
            "connection_outcome": classify_outcome(decision_action, error, parse_error_type),
            "upstream_host": policy.upstream_host,
            "upstream_port": policy.upstream_port,
            "tls_record_version": metadata.tls_record_version if metadata else None,
            "tls_record_length": metadata.tls_record_length if metadata else None,
            "client_hello_version": metadata.client_hello_version if metadata else None,
            "handshake_type": metadata.handshake_type if metadata else None,
            "elapsed_ms": elapsed_ms,
            "bytes_client_to_upstream": c2u,
            "bytes_upstream_to_client": u2c,
            "parse_error_type": parse_error_type,
            "error": error,
        }
        logger.write(event)
        print(f"{event['timestamp']} {client_address} sni={sni} decision={event['decision']} outcome={event['connection_outcome']} error={error}")


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
