# 캡스톤디자인 팀별 결과보고서 초안

> 이 문서는 `붙임1. 캡스톤디자인 팀별 결과보고서 양식.hwp`에 옮겨 작성하기 위한 초안이다. 팀명, 팀원, 지도교수, 제출일 등 행정 정보는 실제 양식에 맞춰 추가 작성한다.

## 1. 과제 기본 정보

| 항목 | 내용 |
| --- | --- |
| 과제명 | TLS 기반 HTTPS 필터링 환경에서의 SNI 기반 정책 프록시와 한계 분석 |
| 팀명 | 작성 필요 |
| 팀원 | 작성 필요 |
| 지도교수 | 작성 필요 |
| 수행 기간 | 2026학년도 1학기 |
| 개발 형태 | 로컬 폐쇄형 테스트베드 및 경량 정책 프록시 프로토타입 |
| 주요 기술 | Python, asyncio, TLS ClientHello, SNI, YAML 정책, pytest, curl, OpenSSL |
| 저장소 | `https://github.com/Kortsec1/Africa_Youth` |

## 2. 과제 개요

본 과제는 TLS 기반 HTTPS 필터링 환경에서 관찰 가능한 정보인 TLS ClientHello와 SNI(Server Name Indication)를 분석하고, 이를 기반으로 연결 허용 또는 차단을 실험할 수 있는 경량 정책 프록시 프로토타입을 개발하는 것을 목표로 한다.

HTTPS는 TLS를 통해 HTTP 요청 내용, 헤더, 본문 등을 암호화하므로 중간 네트워크 장비가 애플리케이션 계층의 세부 내용을 직접 확인하기 어렵다. 그러나 일반적인 ECH 미적용 환경에서는 TLS Handshake 초기에 전송되는 ClientHello 안의 SNI 값이 평문으로 관찰될 수 있다. 이 때문에 일부 네트워크 정책 장비는 SNI를 기반으로 도메인 단위 허용 또는 차단 정책을 적용한다.

본 프로젝트는 실제 인터넷 차단 우회 도구를 제작하는 것이 아니라, SNI 기반 필터링이 어떤 정보에 의존하고 어떤 상황에서 한계를 가지는지 방어적 관점에서 분석한다. 실험은 `allowed.test`, `blocked.test`, `unknown.test`와 같은 로컬 테스트 도메인만 사용하며, 외부 사이트 우회, 범용 프록시, VPN, 터널링 기능은 구현하지 않는다.

## 3. 결과보고 내용

### 3.1 과제선택(과제명)

본 팀은 "TLS 기반 HTTPS 필터링 환경에서의 SNI 기반 정책 프록시와 한계 분석"을 과제명으로 선정하였다. HTTPS 트래픽이 일반화되면서 네트워크 보안 장비가 암호화된 트래픽을 어떻게 판단할 수 있는지에 대한 이해가 중요해졌고, 그중 TLS ClientHello에 포함될 수 있는 SNI는 복호화 없이 관찰 가능한 대표적인 정보이다.

따라서 본 과제는 TLS Handshake와 SNI 기반 동작 방식을 분석하고, 이를 실험할 수 있는 로컬 경량 프록시 프로토타입을 구현하는 방향으로 진행하였다. 과제의 초점은 실제 인터넷 차단 우회 도구 제작이 아니라, SNI 기반 필터링의 원리와 한계를 안전한 로컬 환경에서 확인하는 데 있다.

### 3.2 팀구성(팀명) 간단한 설명

팀명은 `작성 필요`이다. 본 팀은 TLS/SNI 기술 조사, 프록시 프로토타입 구현, 테스트 및 결과 정리, 최종 보고서·발표 자료 작성 역할을 나누어 과제를 수행하였다.

팀 구성은 다음과 같은 역할 체계를 기준으로 운영하였다.

| 역할 | 주요 담당 내용 |
| --- | --- |
| 프로젝트 총괄 및 문서 정리 | 주제 범위 정리, 결과보고서 작성, 발표 자료 구성 |
| TLS/SNI 분석 | TLS Handshake, ClientHello, SNI, ECH 관련 자료 조사 |
| 프록시 구현 | SNI 파서, 정책 로더, TCP 릴레이, 로그 기능 구현 |
| 테스트 및 검증 | curl/OpenSSL/pytest 기반 시나리오 검증, 결과 정리 |

### 3.3 과제수행과정 및 내용

과제는 분석, 설계, 구현, 검증, 정리 단계로 나누어 수행하였다. 먼저 TLS Handshake와 ClientHello 구조, SNI의 역할을 조사하고, SNI 기반 필터링이 어떤 가정에 의존하는지 정리하였다. 이후 SNI 부재, 알 수 없는 SNI, ECH, QUIC/HTTP/3, 암호화 DNS 등 SNI 기반 정책의 한계가 되는 요소를 비교 분석하였다.

구현 단계에서는 외부 네트워크를 대상으로 하지 않는 폐쇄형 로컬 테스트베드를 설계하였다. 클라이언트는 curl 또는 OpenSSL을 사용하고, 정책 프록시는 `127.0.0.1:9443`에서 TLS 연결을 받은 뒤 ClientHello의 SNI를 추출한다. 정책상 허용된 요청은 `127.0.0.1:8443`의 로컬 HTTPS 테스트 서버로 중계하고, 차단 대상은 업스트림 연결 없이 종료하도록 구현하였다.

추진방법은 다음과 같다.

| 단계 | 추진 내용 |
| --- | --- |
| 분석 | TLS Handshake, ClientHello, SNI, ECH, QUIC/HTTP/3 개념 조사 |
| 설계 | 클라이언트-정책 프록시-로컬 HTTPS 서버 구조 설계 |
| 구현 | Python `asyncio` 기반 SNI 정책 프록시와 테스트 서버 구현 |
| 검증 | 허용, 차단, unknown, SNI 없음, 비정상 입력, 서버 장애, 동시 연결 테스트 |
| 정리 | 분석 문서, 테스트 결과 보고서, 시연 스크립트, 발표 구성안 작성 |

수행 일정은 1주차 주제 확정과 TLS/SNI 조사에서 시작하여, 5~6주차에 테스트 환경과 프록시 구조를 설계하고, 7~8주차에 프로토타입 구현과 허용·차단 동작 검증을 진행하는 방식으로 구성하였다. 지도교수 지도체계는 `작성 필요`이며, 보고서에는 정기 회의, 구현 범위 점검, 중간 산출물 피드백, 최종 결과 검토 등의 형태로 정리하면 된다.

### 3.4 도출결과 내용

본 과제를 통해 SNI 기반 정책 프록시 프로토타입, 분석 문서, 테스트 결과 자료, 최종 시연 및 발표 자료를 도출하였다.

구현 결과, 정책 프록시는 TLS ClientHello에서 SNI를 추출하고 YAML 정책에 따라 연결을 허용하거나 차단할 수 있었다. `allowed.test` 요청은 로컬 HTTPS 서버로 정상 중계되어 HTTP 200 JSON 응답을 받았고, `blocked.test`와 `unknown.test` 요청은 정책에 따라 차단되었다. SNI가 없는 연결과 비정상 ClientHello 입력도 기본 정책에 따라 차단되었으며, 처리 결과는 JSON Lines 로그로 기록되었다.

주요 실험 결과는 다음과 같다.

| 시나리오 | 결과 | 판정 |
| --- | --- | --- |
| `allowed.test` 허용 | HTTP 200 JSON 응답, `decision=allow` 기록 | 성공 |
| `blocked.test` 차단 | TLS EOF, `decision=block` 기록 | 성공 |
| `unknown.test` 기본 차단 | 기본 정책 `block` 적용 | 성공 |
| SNI 없는 연결 | `extracted_sni=null`, `decision=block` 기록 | 성공 |
| 비정상 ClientHello | 파싱 오류 기록 후 차단 | 성공 |
| 업스트림 서버 장애 | 정책 판단과 연결 실패 오류를 구분하여 로그 기록 | 성공 |
| 동시 연결 | 요청별 독립 정책 처리 확인 | 성공 |
| pytest 자동 테스트 | 12개 테스트 통과 | 성공 |

최종적으로 본 과제는 SNI 기반 필터링이 TLS 복호화 없이 도메인 단위 정책을 적용할 수 있음을 확인하였다. 동시에 SNI 부재, ECH, QUIC/HTTP/3, 암호화 DNS, 애플리케이션 계층 정보 비가시성 등으로 인해 단독 통제 수단으로는 한계가 있다는 점도 정리하였다.

### 3.5 과제수행 후기

이번 과제를 통해 HTTPS 트래픽이 암호화되어 있더라도 TLS Handshake 단계의 일부 메타데이터가 네트워크 정책 판단에 활용될 수 있다는 점을 구체적으로 이해할 수 있었다. 특히 SNI는 구현 관점에서는 비교적 단순하게 추출할 수 있지만, 실제 정책에 적용할 때는 SNI 부재, ECH, QUIC/HTTP/3 등 다양한 예외와 한계를 함께 고려해야 한다는 점을 확인하였다.

또한 보안 프로젝트에서는 구현 기능뿐 아니라 안전한 실험 범위 설정이 중요하다는 점을 배웠다. 본 과제는 실제 외부 사이트 우회나 범용 프록시 기능을 제외하고, 로컬 테스트 도메인만 사용하는 폐쇄형 테스트베드로 범위를 제한하였다. 이를 통해 주제의 핵심인 SNI 기반 필터링 구조와 한계 분석에 집중할 수 있었다.

개발 과정에서는 단순히 코드가 동작하는지 확인하는 것을 넘어, curl, OpenSSL, pytest, JSONL 로그를 함께 사용하여 결과를 재현 가능하게 기록하는 방법을 익혔다. 향후에는 반복 테스트를 통한 성능 수치 보강, ClientHello 단편화 대응, QUIC/HTTP/3 분석 확장 등을 추가하여 더 완성도 높은 보안 실험 환경으로 발전시킬 수 있을 것이다.

## 4. 수행 배경 및 필요성

HTTPS 사용이 일반화되면서 네트워크 보안 장비가 트래픽 내용을 직접 확인하기 어려운 환경이 되었다. TLS 복호화를 수행하는 방식은 더 많은 정보를 볼 수 있지만, 인증서 신뢰, 개인정보 보호, 운영 복잡성, 법적·윤리적 문제를 동반한다. 반면 SNI 기반 필터링은 TLS 복호화 없이 도메인 단위 정책을 적용할 수 있어 구조가 단순하고 빠르다는 장점이 있다.

하지만 SNI 기반 방식은 다음과 같은 구조적 한계를 가진다.

- 클라이언트가 SNI를 보내지 않으면 대상 도메인을 식별하기 어렵다.
- 정책에 없는 SNI는 기본 정책에 의존해야 한다.
- SNI는 HTTP Host, URL 경로, 본문 등 애플리케이션 계층 정보를 보장하지 않는다.
- ECH(Encrypted ClientHello)가 적용되면 실제 SNI를 관찰하기 어려워질 수 있다.
- QUIC/HTTP/3 환경에서는 TCP 기반 TLS와 다른 관찰 구조가 필요하다.

따라서 본 과제는 SNI 기반 필터링의 원리와 한계를 실험 가능한 형태로 구현하고, 결과를 분석하여 네트워크 보안 정책 설계 시 고려해야 할 점을 정리하는 데 의의가 있다.

## 5. 과제 목표

본 과제의 세부 목표는 다음과 같다.

1. TLS Handshake와 ClientHello, SNI의 동작 방식을 정리한다.
2. SNI 기반 HTTPS 필터링의 기본 원리와 정책 적용 방식을 분석한다.
3. SNI 부재, 알 수 없는 SNI, ECH, QUIC/HTTP/3, 암호화 DNS 등 관련 회피·한계 요인을 비교한다.
4. 로컬 환경에서 동작하는 경량 SNI 정책 프록시를 구현한다.
5. 허용, 차단, 기본 정책, 비정상 입력, 업스트림 장애, 동시 연결 시나리오를 검증한다.
6. 연결 성공 여부, 차단 결과, 처리 시간, 송수신 바이트 수 등을 로그와 보고서로 정리한다.
7. 최종 발표 및 시연에 사용할 자료를 구성한다.

## 6. 수행 범위

### 6.1 포함 범위

- 로컬 HTTPS 테스트 서버 구현
- TLS ClientHello에서 SNI 추출
- YAML 기반 allow/block 정책 처리
- 허용된 연결의 TCP 스트림 중계
- 차단 대상 연결 종료
- JSON Lines 형식의 연결 로그 기록
- curl, OpenSSL, pytest 기반 실험 검증
- SNI 기반 필터링의 한계 및 관련 기술 분석

### 6.2 제외 범위

- 실제 차단 사이트 우회
- 외부 상용 서비스 대상 실험
- 범용 프록시, VPN, 터널링 기능
- TLS 복호화, 인증서 위조, MITM 프록시
- 자동 스캔, 대량 요청, 공격 트래픽 생성
- 특정 검열 시스템 회피를 위한 설정값 또는 자동화 제공

본 프로젝트는 교육 및 연구 목적의 폐쇄형 로컬 테스트베드이며, 모든 실험은 단일 컴퓨터 또는 Docker Compose 내부 환경에서 수행되도록 설계하였다.

## 7. 이론 및 기술 분석

### 7.1 TLS Handshake와 ClientHello

TLS는 서버 인증, 암호화 키 합의, 통신 무결성 보호를 제공하는 보안 프로토콜이다. HTTPS는 HTTP를 TLS 위에서 전송하여 중간자가 요청 경로, 헤더, 본문 등을 읽기 어렵게 만든다.

TLS Handshake는 실제 애플리케이션 데이터를 주고받기 전에 수행되는 절차이며, 클라이언트는 처음에 ClientHello 메시지를 전송한다. ClientHello에는 지원 TLS 버전, 암호군, 확장 정보 등이 포함된다. SNI는 이 확장 정보 중 하나로, 클라이언트가 접속하려는 서버 이름을 서버에 알려주는 역할을 한다.

### 7.2 SNI 기반 필터링 원리

일반적인 ECH 미적용 환경에서 SNI는 ClientHello에 평문으로 포함될 수 있다. 따라서 중간 정책 장비는 TLS 내용을 복호화하지 않고도 ClientHello를 파싱하여 대상 도메인 이름을 확인할 수 있다. 이후 정책 파일 또는 정책 데이터베이스와 비교하여 연결을 허용하거나 차단한다.

본 프로젝트의 정책 프록시는 다음 절차로 동작한다.

1. 클라이언트가 프록시로 TLS 연결을 시작한다.
2. 프록시가 최초 데이터를 읽고 TLS ClientHello인지 확인한다.
3. ClientHello 내부의 SNI 확장을 파싱한다.
4. YAML 정책 파일의 규칙과 비교한다.
5. 정책이 `allow`이면 로컬 HTTPS 테스트 서버로 연결을 중계한다.
6. 정책이 `block`이면 업스트림 연결 없이 클라이언트 연결을 종료한다.
7. 처리 결과를 JSON Lines 로그로 기록한다.

### 7.3 관련 우회·한계 요인 분석

본 과제에서는 실제 우회 절차가 아니라 SNI 기반 정책의 구조적 한계를 분석 대상으로 삼았다.

| 항목 | 설명 | 본 프로젝트에서의 처리 |
| --- | --- | --- |
| SNI 없음 | ClientHello에 SNI가 없으면 도메인 식별이 어렵다. | 기본 정책 `block` 적용 |
| 알 수 없는 SNI | 정책 파일에 없는 SNI는 명시적 규칙을 적용할 수 없다. | 기본 정책 `block` 적용 |
| SNI와 HTTP 계층 불일치 | SNI만으로 HTTP Host, URL, 본문을 확인할 수 없다. | 한계 분석 문서에 정리 |
| ECH | ClientHello의 민감 정보를 암호화하여 SNI 관찰을 어렵게 한다. | 개념 및 정책 영향 분석 |
| QUIC/HTTP/3 | TCP 기반 TLS와 다른 UDP 기반 관찰 구조가 필요하다. | 향후 개선 항목으로 정리 |
| 암호화 DNS | DNS 기반 보조 관찰 지점을 약화시킬 수 있다. | 분석 문서에 정리 |
| ClientHello 단편화 | 단순 파서가 전체 ClientHello를 받지 못할 수 있다. | 현재 한계 및 개선 항목으로 정리 |

## 8. 시스템 설계

### 8.1 전체 구조

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

### 8.2 주요 구성 요소

| 구성 요소 | 경로 | 역할 |
| --- | --- | --- |
| 정책 프록시 | `proxy/main.py` | 클라이언트 연결 수신, SNI 추출, 정책 판단, 로그 기록 |
| SNI 파서 | `proxy/sni_parser.py` | TLS ClientHello에서 SNI 추출 |
| 정책 로더 | `proxy/policy.py` | YAML 정책 파일 로드 및 allow/block 결정 |
| TCP 릴레이 | `proxy/relay.py` | 허용된 연결의 양방향 스트림 중계 |
| 로그 모듈 | `proxy/logging_config.py` | JSON Lines 로그 저장 |
| 테스트 서버 | `server/https_server.py` | 자체 서명 인증서를 사용하는 로컬 HTTPS 서버 |
| 정책 파일 | `configs/policy.yaml` | 허용/차단 SNI와 기본 정책 정의 |
| 테스트 스크립트 | `scripts/test-*.sh` | 허용, 차단, unknown 테스트 실행 |

### 8.3 정책 설계

기본 정책 파일은 다음 구조를 가진다.

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

정책은 allow-list 성격을 가진다. 명시적으로 허용된 `allowed.test`만 로컬 테스트 서버로 중계되고, `blocked.test`, `unknown.test`, SNI 없는 연결은 기본적으로 차단된다. 업스트림은 loopback 또는 Docker Compose 내부 테스트 서버로 제한하여 오픈 프록시로 동작하지 않도록 설계하였다.

## 9. 구현 내용

### 9.1 SNI 파서 구현

SNI 파서는 입력 바이트가 TLS Handshake record인지 확인한 뒤, ClientHello 구조를 따라 session id, cipher suites, compression methods, extensions 영역을 순차적으로 파싱한다. 이후 extension type이 `server_name`인 항목을 찾아 SNI 값을 추출한다.

비정상 입력에 대해서는 예외를 발생시키고, 프록시는 해당 오류를 로그에 남긴 뒤 기본 정책에 따라 연결을 차단한다. 이를 통해 임의 바이트나 불완전한 TLS record가 입력되어도 프로그램이 비정상 종료되지 않도록 하였다.

### 9.2 정책 프록시 구현

정책 프록시는 Python `asyncio` 기반으로 구현하였다. 클라이언트 연결마다 독립적으로 최초 데이터를 읽고 SNI를 추출한 후 정책을 판단한다. 허용된 연결은 고정된 로컬 HTTPS 테스트 서버로 최초 ClientHello를 전달하고 이후 양방향 TCP 스트림을 중계한다. 차단된 연결은 업스트림 연결을 생성하지 않고 종료한다.

로그에는 다음 항목을 기록한다.

- 접속 시각
- 클라이언트 주소
- 추출된 SNI
- 정책 결정 결과
- 정책 판단 사유
- 업스트림 주소 및 포트
- 처리 시간
- 클라이언트-업스트림 송수신 바이트 수
- 오류 메시지

### 9.3 테스트 서버 및 실행 스크립트

테스트 HTTPS 서버는 자체 서명 인증서를 사용하여 `127.0.0.1:8443`에서 실행된다. 클라이언트 테스트는 curl과 OpenSSL을 사용하며, `--resolve` 옵션으로 로컬 테스트 도메인을 `127.0.0.1`에 매핑한다. 이를 통해 실제 외부 도메인이나 공용 프록시를 사용하지 않고도 SNI 기반 정책 동작을 재현할 수 있다.

## 10. 실험 및 검증

### 10.1 실험 환경

| 항목 | 내용 |
| --- | --- |
| 실행 환경 | macOS |
| Python | 3.9.6 |
| curl | 8.16.0 |
| pytest | 8.4.2 |
| 정책 프록시 | `127.0.0.1:9443` |
| 테스트 HTTPS 서버 | `127.0.0.1:8443` |
| 실험 도메인 | `allowed.test`, `blocked.test`, `unknown.test` |

### 10.2 실험 시나리오 및 결과

| 번호 | 시나리오 | 입력/명령 | 예상 결과 | 실제 결과 | 판정 |
| --- | --- | --- | --- | --- | --- |
| 1 | 정상 허용 | `./scripts/test-allowed.sh` | `allowed.test` 허용 및 JSON 응답 | HTTP 200 JSON 응답, `decision=allow` | 성공 |
| 2 | 정상 차단 | `./scripts/test-blocked.sh` | `blocked.test` 차단 | TLS EOF, `decision=block` | 성공 |
| 3 | 알 수 없는 SNI | `./scripts/test-unknown.sh` | 기본 정책 차단 | TLS EOF, `decision=block` | 성공 |
| 4 | SNI 없는 연결 | `openssl s_client -connect 127.0.0.1:9443` | SNI 없음으로 차단 | `extracted_sni=null`, `decision=block` | 성공 |
| 5 | 비정상 ClientHello | `printf "not tls client hello" \| nc 127.0.0.1 9443` | 파싱 실패 후 차단 | `error=not a TLS handshake record` | 성공 |
| 6 | 테스트 서버 장애 | 서버 종료 후 `allowed.test` 요청 | 정책은 허용, 연결 실패 기록 | 업스트림 연결 실패 오류 기록 | 성공 |
| 7 | pytest 통합 테스트 | `.venv/bin/python -m pytest -q` | 전체 테스트 통과 | 12개 테스트 통과 | 성공 |
| 8 | 동시 연결 | 5개 요청 병렬 실행 | 각 SNI별 독립 처리 | 허용 2건, 차단 3건 처리 | 성공 |

### 10.3 테스트 결과 요약

2026-06-09 점검에서 전체 테스트를 재실행한 결과는 다음과 같다.

```text
12 passed in 1.79s
```

정적 컴파일 확인도 통과하였다.

```text
python3 -m py_compile proxy/*.py server/*.py tests/*.py
```

실험 결과, 정책 프록시는 ClientHello에서 SNI를 정상 추출하고 정책에 따라 연결을 허용 또는 차단하였다. 허용된 요청은 로컬 HTTPS 서버의 JSON 응답을 받았고, 차단된 요청은 업스트림으로 전달되지 않았다. 비정상 입력과 서버 장애 상황에서도 오류가 로그로 기록되어 원인 분석이 가능했다.

### 10.4 로그 분석

허용 정책의 경우 `allowed.test`가 SNI로 추출되고, `decision=allow`로 기록되었다. 이때 클라이언트와 업스트림 사이의 송수신 바이트 수가 0보다 크게 기록되어 실제 중계가 이루어졌음을 확인할 수 있었다.

차단 정책의 경우 `blocked.test` 또는 `unknown.test`가 `decision=block`으로 기록되었고, 업스트림으로 전달된 바이트 수는 0이었다. 이는 프록시가 정책에 따라 업스트림 연결을 생성하지 않았음을 의미한다.

SNI 없는 연결은 `extracted_sni=null`로 기록되었고 기본 정책에 따라 차단되었다. 비정상 ClientHello 입력은 파싱 오류 메시지와 함께 차단되었다.

## 11. 결과물

| 결과물 | 경로 또는 설명 |
| --- | --- |
| 분석 보고서 | `docs/concepts.md`, `docs/filtering-evasion-analysis.md`, `docs/evasion-techniques-research.md` |
| 경량 프록시 프로토타입 | `proxy/` 디렉터리 |
| 로컬 HTTPS 테스트 서버 | `server/https_server.py` |
| 정책 파일 | `configs/policy.yaml` |
| 테스트 스크립트 | `scripts/test-allowed.sh`, `scripts/test-blocked.sh`, `scripts/test-unknown.sh` |
| 실험 결과 보고서 | `docs/test-report.md`, `docs/test-results.md` |
| 로그 및 캡처 자료 | `captures/test-run-20260607/`, `logs/` |
| 최종 시연 자료 | `docs/demo-script.md` |
| 최종 발표 구성안 | `docs/presentation-outline.md` |
| 실행 및 운영 문서 | `README.md`, `docs/local-setup.md`, `docs/git-workflow.md` |

## 12. 수행 일정

| 주차 | 수행 내용 |
| --- | --- |
| 1주차 | 캡스톤 주제 확정, 팀 역할 초안 작성, TLS/SNI 기반 프로젝트 방향 정리 |
| 2주차 | TLS Handshake 조사, SNI 동작 방식 조사, HTTPS 필터링 기본 원리 조사 |
| 3주차 | 국내외 SNI 차단 사례 조사, HTTPS 필터링 방식 조사, 선행 연구 분류 |
| 4주차 | SNI 기반 필터링의 한계 분석, ECH 및 ESNI 조사, 최신 기술 동향 검토 |
| 5주차 | 폐쇄형 테스트 환경 설계, 클라이언트·프록시·테스트 서버 구조 정의 |
| 6주차 | 프록시 기능 세분화, SNI 확인, 정책 처리, 로그 구조 정의 |
| 7주차 | 프록시 프로토타입 1차 구현, 요청 흐름과 연결 제어 로직 구현 |
| 8주차 | 프록시 기본 동작 점검, 허용 및 차단 연결 확인, 보완 기능 및 측정 항목 정리 |

## 13. 팀원 역할

> 실제 팀 구성에 맞춰 수정 필요

| 이름 | 역할 | 주요 수행 내용 |
| --- | --- | --- |
| 작성 필요 | 프로젝트 총괄 및 문서 정리 | 주제 범위 정리, 결과보고서 작성, 발표 자료 구성 |
| 작성 필요 | TLS/SNI 분석 | TLS Handshake, ClientHello, SNI, ECH 관련 자료 조사 |
| 작성 필요 | 프록시 구현 | SNI 파서, 정책 로더, TCP 릴레이, 로그 기능 구현 |
| 작성 필요 | 테스트 및 검증 | curl/OpenSSL/pytest 기반 시나리오 검증, 결과 정리 |

## 14. 기대 효과

본 과제를 통해 HTTPS 필터링 환경에서 TLS 복호화 없이 활용 가능한 정보와 그 한계를 실험적으로 이해할 수 있었다. 특히 SNI 기반 정책은 구현이 단순하고 처리 비용이 낮지만, SNI 부재, ECH, QUIC/HTTP/3, 암호화 DNS 등 최신 프로토콜 변화에 따라 정책 정확도가 달라질 수 있음을 확인하였다.

또한 로컬 테스트베드를 통해 보안 정책을 안전하게 재현하고 로그 기반으로 분석하는 방법을 익힐 수 있었다. 이는 실제 네트워크 보안 장비의 정책 설계, 트래픽 가시성 분석, 개인정보 보호와 보안 정책 사이의 균형을 이해하는 데 도움이 된다.

## 15. 한계 및 향후 개선 방향

현재 프로토타입은 캡스톤 실험 목적에 맞춰 경량으로 구현되었기 때문에 다음 한계가 있다.

- 단일 로컬 업스트림만 사용하며 실제 네트워크 프록시로 확장하지 않는다.
- TLS 복호화를 수행하지 않으므로 HTTP Host, URL, 본문 기반 정책은 적용할 수 없다.
- ECH가 적용된 실제 환경에서는 실제 SNI를 직접 확인하기 어렵다.
- QUIC/HTTP/3 트래픽은 UDP 기반 구조이므로 현재 TCP 프록시로는 분석할 수 없다.
- ClientHello가 고의적으로 단편화되는 상황에 대한 고도화된 재조립 검증은 포함하지 않았다.
- pcap 캡처는 macOS sudo 권한 문제로 자동 생성하지 못했으며, 수동 캡처 절차만 문서화하였다.

향후 개선 방향은 다음과 같다.

1. 반복 테스트를 통한 평균 지연시간, 최소/최대 지연시간, 표준편차 측정
2. TLS 버전, ALPN, ClientHello 길이 등 로그 필드 확장
3. ClientHello 누적 읽기 및 TLS record 경계 처리 강화
4. 정책 모드를 allow-list, block-list, monitor-only로 분리하여 비교
5. QUIC/HTTP/3와 ECH 환경의 정책 적용 한계에 대한 별도 분석 문서 보강
6. Wireshark 또는 tcpdump 기반 pcap 증거 자료 추가

## 16. 결론

본 프로젝트는 TLS 기반 HTTPS 필터링 환경에서 SNI가 어떤 방식으로 정책 판단에 활용될 수 있는지 분석하고, 이를 실험할 수 있는 경량 정책 프록시 프로토타입을 구현하였다. 구현된 프록시는 ClientHello에서 SNI를 추출하고 YAML 정책에 따라 연결을 허용하거나 차단하며, 처리 결과를 JSON Lines 로그로 기록한다.

실험 결과 `allowed.test`는 정상적으로 허용되어 로컬 HTTPS 서버의 응답을 받았고, `blocked.test`, `unknown.test`, SNI 없는 연결, 비정상 ClientHello는 정책에 따라 차단되었다. 또한 업스트림 서버 장애와 동시 연결 상황에서도 로그를 통해 상태를 확인할 수 있었다. pytest 기반 자동 테스트도 전체 통과하여 기본 기능의 안정성을 확인하였다.

이를 통해 SNI 기반 필터링은 TLS 복호화 없이 도메인 단위 정책을 적용할 수 있는 실용적인 방법이지만, ECH, QUIC/HTTP/3, 암호화 DNS, 애플리케이션 계층 정보 비가시성 등으로 인해 단독 통제 수단으로는 한계가 있음을 확인하였다. 따라서 실제 보안 정책에서는 SNI 기반 판단을 DNS 정책, 엔드포인트 보안, 로그 분석, 사용자 고지와 함께 종합적으로 설계해야 한다.

## 17. 참고 자료

- RFC 6066, Transport Layer Security Extensions: Extension Definitions
- RFC 8446, The Transport Layer Security Protocol Version 1.3
- RFC 9849, TLS Encrypted Client Hello
- RFC 9460, Service Binding and Parameter Specification via the DNS
- RFC 9001, Using TLS to Secure QUIC
- RFC 8484, DNS Queries over HTTPS
- RFC 7858, Specification for DNS over Transport Layer Security
- Fifield et al., Blocking-resistant communication through domain fronting
- Bock et al., Geneva: Evolving Censorship Evasion Strategies
- 프로젝트 저장소 내부 문서: `README.md`, `docs/concepts.md`, `docs/filtering-evasion-analysis.md`, `docs/test-report.md`
