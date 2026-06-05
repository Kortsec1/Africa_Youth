# Wireshark 및 tcpdump 가이드

## 인터페이스 선택

로컬 통신은 loopback 인터페이스에서 캡처한다. macOS는 보통 `lo0`, Linux는 보통 `lo`를 선택한다.

## 표시 필터

```text
tls
tcp.port == 9443
tls.handshake.type == 1
tls.handshake.extensions_server_name
```

## SNI 위치

```text
TCP
└─ TLS Record
   └─ Handshake Protocol: Client Hello
      └─ Extensions
         └─ server_name
            └─ Server Name
```

## tcpdump

macOS:

```bash
sudo tcpdump -i lo0 port 9443 -w captures/tls-local-test.pcap
```

Linux:

```bash
sudo tcpdump -i lo port 9443 -w captures/tls-local-test.pcap
```

Docker 환경에서는 호스트 포트 `9443`을 캡처하거나 Docker 네트워크 인터페이스를 확인해 해당 인터페이스에서 캡처한다. 캡처 파일은 Git에 커밋하지 않는다.
