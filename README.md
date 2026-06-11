# TLS/SNI 필터링 테스트베드

TLS ClientHello의 SNI(Server Name Indication)를 읽어 로컬 HTTPS 연결을 허용하거나 차단하는 캡스톤디자인 프로젝트입니다. HTTPS 본문을 복호화하지 않고도 도메인 단위 정책을 적용할 수 있는지, 그리고 이 방식이 어떤 한계를 가지는지 폐쇄형 로컬 환경에서 검증합니다.

최종 보고서는 [FINAL_REPORT.md](FINAL_REPORT.md)에 정리했습니다.

## 주요 기능

- TLS ClientHello에서 SNI 추출
- YAML 기반 allow/block 정책 적용
- 허용된 연결만 로컬 HTTPS 테스트 서버로 중계
- 차단, SNI 없음, 알 수 없는 SNI, 업스트림 장애 로그 기록
- 단위 테스트와 통합 테스트 제공

## 구조

```text
Client(curl, openssl)
        |
        v
127.0.0.1:9443
Policy Proxy
        |
        v
127.0.0.1:8443
Test HTTPS Server
```

```text
configs/      YAML 정책 파일
proxy/        SNI 파서, 정책 로더, TCP 릴레이, 프록시 실행 코드
server/       로컬 HTTPS 테스트 서버
scripts/      인증서 생성, 실행, 테스트, 캡처 스크립트
docs/         구조, 실행, 분석 문서
tests/        단위 및 통합 테스트
logs/         프록시 로그 보관 위치
captures/     실험 결과 기록
```

## 준비 사항

- Python 3.11 이상
- OpenSSL
- curl
- Docker 및 Docker Compose 선택 사항
- tcpdump/Wireshark 선택 사항

## 실행

처음 실행할 때:

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

## 문서

- [최종 보고서](FINAL_REPORT.md)
- [아키텍처](docs/architecture.md)
- [핵심 개념](docs/concepts.md)
- [로컬 실행 가이드](docs/local-setup.md)
- [테스트 시나리오](docs/test-scenarios.md)
- [SNI 기반 필터링 한계 분석](docs/filtering-evasion-analysis.md)
- [현대 인터넷 검열 방식과 우회 기법 개요](docs/modern-censorship-and-circumvention-overview.md)
- [Wireshark 및 tcpdump 가이드](docs/wireshark-guide.md)
