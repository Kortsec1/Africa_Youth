# TLS 기반 HTTPS 필터링 구조 분석 및 경량 정책 프록시 테스트베드

이 저장소는 정보보안학과 캡스톤디자인 프로젝트를 위한 폐쇄형 로컬 TLS/SNI 필터링 테스트베드입니다. HTTPS 통신의 TLS Handshake 중 ClientHello에 포함될 수 있는 SNI(Server Name Indication)를 관찰하고, SNI 기반 정책 프록시가 허용 또는 차단 결정을 내리는 구조와 한계를 단일 컴퓨터 안에서 검증합니다.

## 안전 범위

이 프로젝트는 교육 및 연구 목적의 로컬 실험 환경입니다.

- 외부 서버, 클라우드 서버, 실제 상용 서비스에 연결하지 않습니다.
- 테스트 도메인은 `allowed.test`, `blocked.test`, `unknown.test`만 사용합니다.
- TLS 복호화, 인증서 위조, MITM 프록시, VPN, 우회 기능, 스캔 기능을 구현하지 않습니다.
- 프록시는 정책 파일에 있는 고정 로컬 업스트림 HTTPS 서버로만 연결합니다.

## 아키텍처

```text
curl / openssl s_client
        |
        v
localhost:9443
Policy Proxy
  - TLS ClientHello 읽기
  - SNI 추출
  - YAML 정책 평가
  - allow이면 로컬 HTTPS 서버로 TCP 중계
  - block이면 연결 종료
        |
        v
localhost:8443
Test HTTPS Server
```

## 디렉터리 구조

```text
configs/              YAML 정책 파일
proxy/                SNI 파서, 정책 로더, TCP 릴레이, 프록시 실행 코드
server/               로컬 HTTPS 테스트 서버
scripts/              인증서 생성, 실행, 테스트, 캡처 스크립트
docs/                 개념, 구조, 실행, 분석 문서
tests/                단위 및 통합 테스트
logs/                 JSON Lines 프록시 로그
captures/             tcpdump/Wireshark 캡처 파일 보관 위치
```

## 필수 프로그램

- Python 3.11 이상
- OpenSSL
- curl
- Docker 및 Docker Compose 선택 사항
- tcpdump/Wireshark 선택 사항

## 로컬 실행 빠른 시작

처음 실행하거나 새 터미널을 열었을 때는 아래 순서대로 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
./scripts/generate-cert.sh
```

터미널 1에서 HTTPS 테스트 서버를 실행합니다.

```bash
python -m server.https_server
```

터미널 2에서 정책 프록시를 실행합니다.

```bash
python -m proxy.main
```

터미널 3에서 허용, 차단, 알 수 없는 SNI 테스트를 실행합니다.

```bash
./scripts/test-allowed.sh
./scripts/test-blocked.sh
./scripts/test-unknown.sh
```

로그는 다음 명령으로 확인합니다.

```bash
tail -n 20 logs/proxy.jsonl
```

전체 테스트는 다음 명령으로 실행합니다.

```bash
python -m pytest
```

포트가 이미 사용 중이면 점유 프로세스를 확인합니다.

```bash
lsof -nP -iTCP:8443 -sTCP:LISTEN
lsof -nP -iTCP:9443 -sTCP:LISTEN
```

다른 포트를 쓰려면 서버 포트, 프록시 포트, 정책 파일의 `upstream.port`, curl 테스트 포트를 함께 맞춰야 합니다.

```bash
python -m server.https_server --port 18443
python -m proxy.main --listen-port 19443
```

## Python 환경 설정

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## 인증서 생성

```bash
./scripts/generate-cert.sh
```

생성 위치:

- `server/certs/server.crt`
- `server/certs/server.key`

## 로컬 프로세스 방식 실행

터미널 1:

```bash
python -m server.https_server --host 127.0.0.1 --port 8443
```

터미널 2:

```bash
python -m proxy.main --listen-host 127.0.0.1 --listen-port 9443 --policy configs/policy.yaml
```

터미널 3:

```bash
./scripts/test-allowed.sh
./scripts/test-blocked.sh
./scripts/test-unknown.sh
```

`allowed.test`는 JSON 응답을 받아야 하고, `blocked.test`와 `unknown.test`는 정책에 따라 연결이 종료되어야 합니다.

## Docker Compose 실행

```bash
docker compose up --build
```

호스트에서 테스트:

```bash
curl -vk --resolve allowed.test:9443:127.0.0.1 https://allowed.test:9443/
curl -vk --resolve blocked.test:9443:127.0.0.1 https://blocked.test:9443/
```

## 로그 확인

```bash
tail -n 20 logs/proxy.jsonl
```

각 로그는 JSON Lines 형식이며 `timestamp`, `client_address`, `extracted_sni`, `decision`, `reason`, `upstream_host`, `upstream_port`, `elapsed_ms`, 전송 바이트 수, `error`를 포함합니다. 전체 패킷 내용과 민감정보는 기록하지 않습니다.

## 테스트 실행

```bash
python -m pytest
```

## Wireshark 및 tcpdump

macOS loopback 캡처:

```bash
sudo tcpdump -i lo0 port 9443 -w captures/tls-local-test.pcap
```

Linux loopback 캡처:

```bash
sudo tcpdump -i lo port 9443 -w captures/tls-local-test.pcap
```

Wireshark 표시 필터:

```text
tls
tcp.port == 9443
tls.handshake.type == 1
tls.handshake.extensions_server_name
```

## 알려진 한계

- ECH가 적용되면 기존 SNI 기반 정책은 대상 도메인을 확인하지 못할 수 있습니다.
- 이 프록시는 TLS 내용을 복호화하지 않으므로 HTTP 경로나 본문 기반 정책을 적용하지 않습니다.
- 정책 업스트림은 로컬 테스트 서버로 제한됩니다.
- 자체 서명 인증서를 사용하므로 curl에는 `-k`가 필요합니다.

## 문제 해결

- 인증서 오류: `./scripts/generate-cert.sh`를 다시 실행합니다.
- 포트 충돌: 8443 또는 9443을 사용하는 프로세스를 종료하거나 다른 포트를 지정합니다.
- 정책 오류: `configs/policy.yaml`의 `default_action`, `rules[].action`, 중복 SNI, 업스트림 주소를 확인합니다.
- Docker 테스트 실패: Docker Desktop 실행 상태와 `docker compose version`을 확인합니다.

## 향후 확장 계획

- 테스트 결과 자동 리포트 생성
- 성능 측정 항목 추가
- Docker 네트워크 캡처 절차 보강
- ECH 적용 환경에서 정책 변화 분석 문서화
