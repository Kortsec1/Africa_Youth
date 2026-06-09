from __future__ import annotations

from dataclasses import dataclass


class ClientHelloParseError(ValueError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code or message.replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class ClientHelloMetadata:
    sni: str | None
    tls_record_version: str
    tls_record_length: int
    handshake_type: int
    client_hello_version: str
    has_sni: bool


def extract_sni(data: bytes) -> str | None:
    return parse_client_hello(data).sni


def parse_client_hello(data: bytes) -> ClientHelloMetadata:
    if len(data) < 5:
        raise ClientHelloParseError("incomplete TLS record header")
    content_type = data[0]
    if content_type != 0x16:
        raise ClientHelloParseError("not a TLS handshake record")
    tls_record_version = _format_tls_version(data[1:3])
    record_len = int.from_bytes(data[3:5], "big")
    if len(data) < 5 + record_len:
        raise ClientHelloParseError("incomplete TLS record body")
    body = data[5 : 5 + record_len]
    if len(body) < 4 or body[0] != 0x01:
        raise ClientHelloParseError("not a ClientHello")
    handshake_type = body[0]
    hello_len = int.from_bytes(body[1:4], "big")
    hello = body[4 : 4 + hello_len]
    if len(hello) < hello_len:
        raise ClientHelloParseError("incomplete ClientHello")
    if len(hello) < 2:
        raise ClientHelloParseError("ClientHello missing version")
    client_hello_version = _format_tls_version(hello[:2])

    pos = 34
    if len(hello) < pos + 1:
        raise ClientHelloParseError("ClientHello missing session id")
    session_id_len = hello[pos]
    pos += 1 + session_id_len
    if len(hello) < pos + 2:
        raise ClientHelloParseError("ClientHello missing cipher suites")
    cipher_len = int.from_bytes(hello[pos : pos + 2], "big")
    pos += 2 + cipher_len
    if len(hello) < pos + 1:
        raise ClientHelloParseError("ClientHello missing compression methods")
    compression_len = hello[pos]
    pos += 1 + compression_len
    if len(hello) == pos:
        return ClientHelloMetadata(
            sni=None,
            tls_record_version=tls_record_version,
            tls_record_length=record_len,
            handshake_type=handshake_type,
            client_hello_version=client_hello_version,
            has_sni=False,
        )
    if len(hello) < pos + 2:
        raise ClientHelloParseError("ClientHello missing extensions length")

    extensions_len = int.from_bytes(hello[pos : pos + 2], "big")
    pos += 2
    end = pos + extensions_len
    if len(hello) < end:
        raise ClientHelloParseError("incomplete extensions")

    while pos + 4 <= end:
        ext_type = int.from_bytes(hello[pos : pos + 2], "big")
        ext_len = int.from_bytes(hello[pos + 2 : pos + 4], "big")
        pos += 4
        ext_data = hello[pos : pos + ext_len]
        if len(ext_data) < ext_len:
            raise ClientHelloParseError("incomplete extension")
        if ext_type == 0x0000:
            sni = _parse_server_name(ext_data)
            return ClientHelloMetadata(
                sni=sni,
                tls_record_version=tls_record_version,
                tls_record_length=record_len,
                handshake_type=handshake_type,
                client_hello_version=client_hello_version,
                has_sni=sni is not None,
            )
        pos += ext_len
    return ClientHelloMetadata(
        sni=None,
        tls_record_version=tls_record_version,
        tls_record_length=record_len,
        handshake_type=handshake_type,
        client_hello_version=client_hello_version,
        has_sni=False,
    )


def _parse_server_name(data: bytes) -> str | None:
    if len(data) < 2:
        raise ClientHelloParseError("invalid server_name extension")
    list_len = int.from_bytes(data[:2], "big")
    pos = 2
    end = pos + list_len
    if len(data) < end:
        raise ClientHelloParseError("incomplete server_name list")
    while pos + 3 <= end:
        name_type = data[pos]
        name_len = int.from_bytes(data[pos + 1 : pos + 3], "big")
        pos += 3
        name = data[pos : pos + name_len]
        if len(name) < name_len:
            raise ClientHelloParseError("incomplete server name")
        if name_type == 0:
            return name.decode("idna").lower()
        pos += name_len
    return None


def _format_tls_version(raw: bytes) -> str:
    if len(raw) != 2:
        return "unknown"
    known = {
        b"\x03\x00": "SSL 3.0",
        b"\x03\x01": "TLS 1.0",
        b"\x03\x02": "TLS 1.1",
        b"\x03\x03": "TLS 1.2",
        b"\x03\x04": "TLS 1.3",
    }
    return known.get(raw, f"0x{raw.hex()}")
