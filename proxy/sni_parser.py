from __future__ import annotations


class ClientHelloParseError(ValueError):
    pass


def extract_sni(data: bytes) -> str | None:
    if len(data) < 5:
        raise ClientHelloParseError("incomplete TLS record header")
    content_type = data[0]
    if content_type != 0x16:
        raise ClientHelloParseError("not a TLS handshake record")
    record_len = int.from_bytes(data[3:5], "big")
    if len(data) < 5 + record_len:
        raise ClientHelloParseError("incomplete TLS record body")
    body = data[5 : 5 + record_len]
    if len(body) < 4 or body[0] != 0x01:
        raise ClientHelloParseError("not a ClientHello")
    hello_len = int.from_bytes(body[1:4], "big")
    hello = body[4 : 4 + hello_len]
    if len(hello) < hello_len:
        raise ClientHelloParseError("incomplete ClientHello")

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
        return None
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
            return _parse_server_name(ext_data)
        pos += ext_len
    return None


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
