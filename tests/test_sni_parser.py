import pytest

from proxy.sni_parser import ClientHelloParseError, extract_sni


def build_client_hello(server_name: str | None = "allowed.test") -> bytes:
    extensions = b""
    if server_name is not None:
        name = server_name.encode("idna")
        server_name_list = b"\x00" + len(name).to_bytes(2, "big") + name
        ext_body = len(server_name_list).to_bytes(2, "big") + server_name_list
        extensions += b"\x00\x00" + len(ext_body).to_bytes(2, "big") + ext_body
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


def test_extract_sni_from_client_hello():
    assert extract_sni(build_client_hello("Allowed.Test")) == "allowed.test"


def test_extract_sni_returns_none_without_sni_extension():
    assert extract_sni(build_client_hello(None)) is None


def test_rejects_non_tls_handshake():
    with pytest.raises(ClientHelloParseError):
        extract_sni(b"GET / HTTP/1.1\r\n\r\n")


def test_rejects_incomplete_client_hello():
    with pytest.raises(ClientHelloParseError):
        extract_sni(build_client_hello("allowed.test")[:12])
