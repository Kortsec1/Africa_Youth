# TLS/SNI 기반 HTTPS 필터링 구조 분석 및 로컬 테스트베드 구현

## 1. 연구 개요

본 프로젝트는 HTTPS 환경에서 네트워크 중간 장비가 어떤 정보를 기준으로 도메인 단위 정책을 적용할 수 있는지 확인하기 위해 수행했다. HTTPS는 애플리케이션 데이터가 암호화되므로 URL 경로, 요청 본문, 로그인 상태 같은 세부 정보는 중간에서 직접 확인하기 어렵다. 반면 ECH가 적용되지 않은 일반적인 TLS 연결에서는 ClientHello에 포함된 SNI(Server Name Indication)를 관찰할 수 있다.

프로젝트의 목표는 SNI를 이용해 HTTPS 연결을 허용하거나 차단하는 과정을 직접 구현하고, 이 방식의 장점과 한계를 로컬 환경에서 검증하는 것이다. 모든 실험은 `allowed.test`, `blocked.test`, `unknown.test` 같은 로컬 테스트 도메인과 loopback 주소에서만 수행했다.

## 2. 연구 범위

구현 범위는 다음과 같다.

- TLS ClientHello 수신 및 SNI 추출
- YAML 정책 파일 기반 allow/block 판단
- 허용된 연결을 로컬 HTTPS 테스트 서버로 TCP 중계
- 차단, SNI 없음, 알 수 없는 SNI, 업스트림 장애 로그 기록
- 단위 테스트와 통합 테스트를 통한 기능 검증

범위에서 제외한 항목은 다음과 같다.

- 실제 차단 사이트 우회
- 범용 프록시, VPN, 터널링 도구 구현
- 외부 상용 서비스 대상 실험
- TLS 복호화, 인증서 위조, MITM 프록시 구현
- 대량 요청, 자동 스캔, 공격 트래픽 생성

## 3. 시스템 구조

전체 구조는 클라이언트, 정책 프록시, 로컬 HTTPS 테스트 서버로 구성된다.

```text
Client(curl, openssl)
        |
        v
127.0.0.1:9443
Policy Proxy
  - TLS ClientHello 수신
  - SNI 추출
  - YAML 정책 평가
  - allow: 로컬 업스트림으로 TCP 중계
  - block: 연결 종료
        |
        v
127.0.0.1:8443
Test HTTPS Server
```

정책 프록시는 `proxy/main.py`에서 실행된다. 최초 TLS record를 읽고 `proxy/sni_parser.py`로 SNI를 추출한 뒤, `proxy/policy.py`의 정책 로더가 반환한 규칙에 따라 연결을 허용하거나 차단한다. 허용된 연결은 `proxy/relay.py`를 통해 테스트 서버로 중계된다. 테스트 서버는 `server/https_server.py`에 구현되어 있으며 자체 서명 인증서를 사용한다.

정책 파일은 `configs/policy.yaml`에 정의되어 있다.

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

업스트림은 loopback 또는 Docker Compose 내부 테스트 서버로 제한했다. 따라서 이 프로그램은 외부 목적지로 임의 연결을 열어주는 오픈 프록시로 동작하지 않는다.

## 4. 구현 내용

SNI 파서는 TLS record header, handshake header, ClientHello body, extension 영역을 순서대로 해석한다. `server_name` extension이 있으면 도메인을 IDNA 기준으로 디코딩하고 소문자로 정규화한다. SNI가 없거나 ClientHello가 비정상이면 예외 또는 `None`으로 처리해 기본 정책을 적용할 수 있게 했다.

정책 로더는 다음 항목을 검증한다.

- `default_action`은 `allow` 또는 `block`만 허용
- `upstream.host`는 로컬 주소 또는 `test-server`만 허용
- `upstream.port`는 1부터 65535 사이 정수만 허용
- 중복 SNI 규칙과 잘못된 action을 오류로 처리

로그는 JSON Lines 형식으로 기록한다. 주요 필드는 `extracted_sni`, `decision`, `reason`, `connection_outcome`, TLS 메타데이터, 처리 시간, 중계 바이트 수, 오류 정보다. 이 로그를 통해 정책 결정과 연결 결과를 분리해서 분석할 수 있다.

## 5. 실험 및 검증

실험은 로컬 테스트 서버와 정책 프록시를 실행한 뒤 `curl`, `openssl s_client`, pytest 통합 테스트로 수행했다.

| 실험 | 입력 | 예상 결과 | 확인 결과 |
| --- | --- | --- | --- |
| 허용 SNI | `allowed.test` | 업스트림 중계 및 JSON 응답 | HTTP 200 응답 수신 |
| 차단 SNI | `blocked.test` | 업스트림 연결 없이 종료 | TLS 연결 실패 |
| 알 수 없는 SNI | `unknown.test` | 기본 정책 `block` 적용 | TLS 연결 실패 |
| SNI 없음 | `openssl s_client` without `-servername` | 기본 정책 `block` 적용 | TLS 연결 실패 |
| 업스트림 장애 | 서버 중지 후 `allowed.test` | allow 결정 후 upstream error 기록 | 오류 로그 기록 |
| 단편화된 ClientHello | ClientHello를 나누어 전송 | 전체 record 수신 후 정책 판단 | `blocked.test` 차단 |

실험 결과 파일은 `captures/test-run-20260607/`에 보관했다. `01-allowed.txt`는 허용된 연결에서 테스트 서버의 JSON 응답을 확인한 결과이고, `02-blocked.txt`, `03-unknown.txt`, `04-no-sni.txt`는 정책에 의해 TLS 연결이 종료되는 결과를 보여준다.

자동화 테스트는 `tests/`에 구성했다. 단위 테스트는 SNI 파서와 정책 로더를 검증하고, 통합 테스트는 실제 서버와 프록시 프로세스를 띄운 뒤 허용, 차단, 알 수 없는 SNI, 업스트림 장애, 단편화된 ClientHello, 포트 충돌 처리를 확인한다.

## 6. 분석

SNI 기반 필터링은 TLS 본문을 복호화하지 않고 도메인 단위 정책을 적용할 수 있다는 장점이 있다. 구현이 비교적 단순하고, 개인정보 침해가 큰 TLS 복호화 없이도 기본적인 allow/block 정책을 검증할 수 있다.

그러나 구조적 한계도 분명하다.

- SNI가 없으면 대상 도메인을 직접 식별할 수 없다.
- 정책에 없는 SNI는 기본 정책에 의존한다.
- SNI만으로 HTTP Host, URL 경로, 요청 본문을 확인할 수 없다.
- ClientHello 형식 변화나 비정상 입력에 대비한 파서 검증이 필요하다.
- ECH(Encrypted ClientHello)가 적용되면 실제 SNI 관찰 가능성이 줄어든다.
- QUIC/HTTP/3는 TCP 기반 TLS 프록시와 다른 분석 구조가 필요하다.

따라서 SNI 기반 정책은 단독 완성형 보안 수단이라기보다, DNS 정책, 엔드포인트 정책, 로그 분석, 승인된 프록시 구조와 함께 사용해야 하는 제한적 도메인 단위 제어 방식으로 보는 것이 적절하다.

## 7. 결론

본 프로젝트는 TLS ClientHello에서 SNI를 추출하고 정책에 따라 로컬 HTTPS 연결을 허용 또는 차단하는 테스트베드를 구현했다. 구현 결과 `allowed.test`는 정상 중계되고, `blocked.test`, `unknown.test`, SNI 없는 연결은 기본 정책에 따라 차단됨을 확인했다. 또한 업스트림 장애와 단편화된 ClientHello 같은 예외 상황도 로그와 테스트로 검증했다.

결론적으로 SNI 기반 필터링은 HTTPS를 복호화하지 않고 도메인 단위 제어를 수행할 수 있지만, SNI 부재, ECH, 애플리케이션 계층 비가시성 때문에 적용 범위가 제한된다. 본 테스트베드는 이러한 동작 원리와 한계를 안전한 로컬 환경에서 재현하고 설명하는 교육용·연구용 산출물이다.

## 8. 제출 파일 안내

- `README.md`: 프로젝트 실행 및 문서 안내
- `FINAL_REPORT.md`: 최종 보고서
- `proxy/`: 정책 프록시 구현
- `server/`: 로컬 HTTPS 테스트 서버
- `configs/`: 정책 설정
- `scripts/`: 실행 및 실험 보조 스크립트
- `tests/`: 단위 및 통합 테스트
- `docs/`: 보조 설명 문서
- `captures/test-run-20260607/`: 실험 결과 기록
