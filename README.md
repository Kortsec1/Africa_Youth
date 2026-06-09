# TLS/SNI 필터링 구조 분석 테스트베드

정보보안학과 캡스톤디자인 프로젝트용 폐쇄형 로컬 테스트베드입니다. TLS Handshake의 ClientHello에 포함될 수 있는 SNI(Server Name Indication)를 추출하고, YAML 정책에 따라 HTTPS 연결을 허용하거나 차단하는 구조를 단일 컴퓨터에서 검증합니다.

## 핵심 목표

- HTTPS 트래픽을 복호화하지 않고 ClientHello에서 SNI를 추출합니다.
- `allowed.test`, `blocked.test`, `unknown.test` 로컬 실험 도메인만 사용합니다.
- SNI 기반 정책 프록시의 동작 방식과 한계를 관찰합니다.
- 모든 실험은 로컬 프로세스 또는 Docker Compose 내부에서만 수행합니다.

## 안전 범위

이 저장소는 교육 및 연구 목적의 로컬 실험 환경입니다.

구현하는 기능:

- 로컬 HTTPS 테스트 서버
- 고정 로컬 업스트림으로만 연결하는 정책 프록시
- SNI 기반 allow/block 정책
- JSON Lines 연결 로그
- Wireshark/tcpdump 분석 가이드

구현하지 않는 기능:

- 실제 차단 사이트 우회
- 범용 프록시, VPN, 터널링 도구
- 외부 상용 서비스 대상 테스트
- 실제 인터넷 트래픽 가로채기
- TLS 복호화, 인증서 위조, MITM 프록시
- 자동 스캔, 대량 요청, 공격 트래픽 생성

## 아키텍처

```text
Client
  curl / openssl s_client
        |
        v
localhost:9443
Policy Proxy
  - TLS ClientHello 수신
  - SNI 추출
  - YAML 정책 평가
  - allow: 고정 로컬 업스트림으로 TCP 중계
  - block: 연결 종료
        |
        v
localhost:8443
Test HTTPS Server
```

## 디렉터리 구조

```text
configs/      YAML 정책 파일
proxy/        SNI 파서, 정책 로더, TCP 릴레이, 프록시 실행 코드
server/       로컬 HTTPS 테스트 서버
scripts/      인증서 생성, 실행, 테스트, 캡처 스크립트
docs/         개념, 구조, 실행, 분석 문서
tests/        단위 및 통합 테스트
logs/         JSON Lines 프록시 로그
captures/     tcpdump/Wireshark 캡처 파일 보관 위치
```

## 준비 사항

- Python 3.9 이상
- OpenSSL
- curl
- Docker 및 Docker Compose 선택 사항
- tcpdump/Wireshark 선택 사항

## 빠른 시작

처음 실행할 때:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
./scripts/generate-cert.sh
```

이미 가상환경을 만든 뒤 새 터미널을 열었다면:

```bash
source .venv/bin/activate
```

터미널 1에서 HTTPS 테스트 서버를 실행합니다.

```bash
python -m server.https_server
```

터미널 2에서 정책 프록시를 실행합니다.

```bash
python -m proxy.main
```

터미널 3에서 테스트합니다.

```bash
./scripts/test-allowed.sh
./scripts/test-blocked.sh
./scripts/test-unknown.sh
```

예상 결과:

- `allowed.test`: 테스트 서버 JSON 응답 수신
- `blocked.test`: 정책 차단으로 TLS 연결 종료
- `unknown.test`: 기본 정책 `block` 적용

## 직접 curl로 테스트

```bash
curl --noproxy "*" -vk --resolve allowed.test:9443:127.0.0.1 https://allowed.test:9443/
curl --noproxy "*" -vk --resolve blocked.test:9443:127.0.0.1 https://blocked.test:9443/
curl --noproxy "*" -vk --resolve unknown.test:9443:127.0.0.1 https://unknown.test:9443/
```

OpenSSL 테스트:

```bash
openssl s_client -connect 127.0.0.1:9443 -servername allowed.test
openssl s_client -connect 127.0.0.1:9443 -servername blocked.test
```

SNI 없이 연결하는 한계 테스트:

```bash
openssl s_client -connect 127.0.0.1:9443
```

## 정책 파일

기본 정책은 [configs/policy.yaml](configs/policy.yaml)에 있습니다.

```yaml
default_action: block
upstream:
  host: 127.0.0.1
  port: 8443
rules:
  - sni: allowed.test
    action: allow
    reason: 허용된 로컬 테스트 도메인
  - sni: blocked.test
    action: block
    reason: 차단 동작 확인용 로컬 테스트 도메인
```

업스트림은 로컬 테스트 서버로 제한됩니다. 외부 목적지로 임의 연결하는 오픈 프록시로 동작하지 않습니다.

## 로그 확인

```bash
tail -n 20 logs/proxy.jsonl
```

로그는 JSON Lines 형식이며 다음 필드를 포함합니다.

- `timestamp`
- `client_address`
- `extracted_sni`
- `decision`
- `reason`
- `upstream_host`
- `upstream_port`
- `elapsed_ms`
- `bytes_client_to_upstream`
- `bytes_upstream_to_client`
- `error`

전체 패킷 내용과 민감정보는 기록하지 않습니다.

## 테스트

```bash
python -m pytest
```

샌드박스가 있는 환경에서는 통합 테스트가 로컬 포트 바인딩 권한을 요구할 수 있습니다.

## Docker Compose

```bash
docker compose up --build
```

호스트에서 테스트:

```bash
curl --noproxy "*" -vk --resolve allowed.test:9443:127.0.0.1 https://allowed.test:9443/
curl --noproxy "*" -vk --resolve blocked.test:9443:127.0.0.1 https://blocked.test:9443/
```

종료:

```bash
docker compose down
```

## 패킷 분석

macOS:

```bash
sudo tcpdump -i lo0 port 9443 -w captures/tls-local-test.pcap
```

Linux:

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

SNI 위치:

```text
TCP
└─ TLS Record
   └─ Handshake Protocol: Client Hello
      └─ Extensions
         └─ server_name
            └─ Server Name
```

## 문제 해결

포트 충돌 확인:

```bash
lsof -nP -iTCP:8443 -sTCP:LISTEN
lsof -nP -iTCP:9443 -sTCP:LISTEN
```

다른 포트 사용:

```bash
python -m server.https_server --port 18443
python -m proxy.main --listen-port 19443
```

프록시가 다른 서버 포트로 연결해야 한다면 `configs/policy.yaml`의 `upstream.port`도 함께 변경해야 합니다.

인증서가 없거나 만료된 경우:

```bash
./scripts/generate-cert.sh
```

## 알려진 한계

- SNI가 없거나 파싱에 실패하면 기본 정책이 적용됩니다.
- ECH가 적용되면 기존 SNI 기반 정책은 대상 도메인을 확인하지 못할 수 있습니다.
- 이 프록시는 TLS 내용을 복호화하지 않으므로 HTTP 경로, 헤더, 본문 기반 정책을 적용하지 않습니다.
- 자체 서명 인증서를 사용하므로 curl 테스트에는 `-k`가 필요합니다.

## 참고 문서

- [로컬 실행 가이드](docs/local-setup.md)
- [개념 정리](docs/concepts.md)
- [SNI 기반 필터링 우회·회피 기법 분석](docs/filtering-evasion-analysis.md)
- [아키텍처](docs/architecture.md)
- [Wireshark 가이드](docs/wireshark-guide.md)
- [테스트 시나리오](docs/test-scenarios.md)
- [테스트 결과 보고서](docs/test-report.md)
- [상세 테스트 결과](docs/test-results.md)
- [최종 결과보고서 초안](docs/final-report-draft.md)
- [최종 시연 스크립트](docs/demo-script.md)
- [최종 발표 구성안](docs/presentation-outline.md)
- [Git 운영 규칙](docs/git-workflow.md)
- [주차별 계획](docs/week-plan.md)
