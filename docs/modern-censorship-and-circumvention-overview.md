# 현대 인터넷 검열 방식과 우회 기법 개요

이 문서는 캡스톤디자인 보고서의 배경 지식을 확장하기 위한 자료다. 목적은 실제 차단 회피 절차를 제공하는 것이 아니라, 현대 인터넷 검열이 어느 계층에서 이루어지고 기존 우회 기법이 어떤 원리와 한계를 가지는지 개념적으로 정리하는 것이다.

## 정리 범위

다루는 내용:

- DNS, IP, TCP, HTTP, TLS/SNI, QUIC, 애플리케이션 계층에서의 검열 방식
- 각 방식이 관찰하는 정보와 정책 적용 지점
- 기존 우회 기법의 개념적 분류
- SNI 기반 필터링 테스트베드와 연결되는 분석 관점
- 방어적·교육적 실험으로 안전하게 다룰 수 있는 항목

다루지 않는 내용:

- 실제 차단 사이트 우회 절차
- 공용 프록시, VPN, 터널링 도구 설정법
- 특정 국가나 기관의 필터링을 회피하기 위한 명령, 코드, 자동화
- 외부 서비스나 CDN을 이용한 재현 방법
- 탐지 회피를 위한 패킷 조작 상세값

## 현대 검열 방식 분류

| 방식 | 관찰 지점 | 동작 원리 | 장점 | 한계 |
| --- | --- | --- | --- | --- |
| DNS 변조/차단 | DNS 질의·응답 | 특정 도메인 질의에 잘못된 IP, 빈 응답, 차단 페이지 IP 등을 반환 | 구현이 쉽고 비용이 낮음 | 암호화 DNS, 외부 리졸버, 캐시 사용 시 가시성 약화 |
| IP 차단 | 목적지 IP | 특정 IP 대역으로 가는 패킷을 차단 | 단순하고 빠름 | CDN·공유 호스팅에서는 정상 서비스까지 함께 차단될 수 있음 |
| TCP 차단/RST 주입 | TCP 연결 | 특정 연결을 강제 종료하거나 세션 성립을 방해 | HTTP/TLS 여부와 무관하게 적용 가능 | 암호화된 내용은 보지 못하며 오탐 가능성 존재 |
| HTTP Host/URL 필터링 | 평문 HTTP | Host 헤더, URL 경로, 키워드 등을 검사 | 세부 URL 정책 가능 | HTTPS에서는 TLS 복호화 없이는 적용 불가 |
| TLS/SNI 필터링 | TLS ClientHello | SNI를 추출해 도메인 단위 allow/block 결정 | TLS 복호화 없이 도메인 정책 가능 | SNI 없음, ECH, QUIC, 단편화, 애플리케이션 계층 불일치에 취약 |
| 인증서 기반 관찰 | TLS 서버 인증서 | 인증서의 주체명, 발급자, 지문 등을 관찰 | SNI와 함께 보조 지표로 활용 가능 | TLS 1.3에서는 인증서가 암호화되어 단순 관찰이 어려움 |
| DPI 기반 분류 | 패킷·흐름 메타데이터 | 프로토콜 특징, 패킷 크기, 타이밍, 지문을 분석 | 복합 정책과 이상 탐지 가능 | 비용이 높고 개인정보·오탐 문제가 큼 |
| QUIC/HTTP/3 제어 | UDP 443, QUIC Initial | QUIC Initial과 TLS 정보를 해석하거나 UDP 443을 제한 | 최신 웹 트래픽 통제에 필요 | TCP 기반 TLS와 다른 파서가 필요하고 암호화 범위가 넓음 |
| 애플리케이션 계층 차단 | 플랫폼·서비스 내부 | 계정, 게시물, API, 앱 내부 정책으로 접근 제한 | 서비스 수준의 세밀한 제어 가능 | 네트워크 장비만으로는 관찰·검증 어려움 |

## 계층별 특징

### 1. DNS 계층

DNS 검열은 도메인 이름을 IP 주소로 바꾸는 단계에 개입한다. 차단 대상 도메인에 대해 조작된 IP를 반환하거나 응답을 실패시키는 방식이 대표적이다. OONI는 검열 측정에서 DNS 응답이 알려진 차단 페이지 IP를 가리키는 경우 등을 차단 증거로 분류한다.

DNS 계층 방식은 비용이 낮지만, DNS over HTTPS(DoH)와 DNS over TLS(DoT)처럼 DNS 질의 자체가 암호화되면 네트워크 중간 장비의 관찰 능력이 줄어든다. DoH는 DNS 질의를 HTTPS로 전달하는 표준이고, DoT는 DNS 질의를 TLS로 보호하는 표준이다.

### 2. 네트워크·전송 계층

IP 차단은 목적지 IP를 기준으로 패킷을 버린다. TCP 차단은 연결 수립을 방해하거나 연결 중간에 종료 신호를 주입하는 방식으로 동작할 수 있다. 이 방식은 도메인 이름을 보지 않아도 적용할 수 있지만, 동일 IP에서 여러 서비스가 제공되는 CDN 환경에서는 정상 트래픽까지 영향을 받을 수 있다.

전송 계층 검열은 단순하고 빠르지만, 암호화된 애플리케이션 내용을 직접 확인하지 못한다. 따라서 DNS, SNI, 인증서, 트래픽 지문 같은 다른 관찰 지점과 함께 쓰이는 경우가 많다.

### 3. HTTP 계층

평문 HTTP에서는 Host 헤더, URL 경로, 요청 본문 일부를 볼 수 있기 때문에 세밀한 필터링이 가능하다. 하지만 현대 웹은 대부분 HTTPS를 사용하므로, 중간 장비가 TLS를 복호화하지 않는 한 URL 경로와 본문은 볼 수 없다.

이 지점이 본 프로젝트의 핵심 문제의식과 연결된다. HTTPS 환경에서는 내용 기반 필터링보다 TLS 핸드셰이크 메타데이터, 특히 SNI 같은 제한된 정보에 의존하게 된다.

### 4. TLS/SNI 계층

SNI는 TLS ClientHello에 포함될 수 있는 서버 이름 정보다. ECH가 적용되지 않은 일반적인 TLS 연결에서는 중간 장비가 SNI를 읽고 도메인 단위 정책을 적용할 수 있다.

그러나 SNI 기반 필터링은 구조적 한계를 가진다.

- 클라이언트가 SNI를 보내지 않으면 도메인을 식별하기 어렵다.
- 정책에 없는 SNI는 기본 정책에 의존해야 한다.
- SNI는 HTTP Host, URL, 본문과 같은 애플리케이션 계층 목적지를 보장하지 않는다.
- ClientHello 단편화나 비정상 입력은 단순 파서의 한계를 드러낼 수 있다.
- ECH가 적용되면 실제 ClientHelloInner의 민감 정보가 암호화되어 SNI 기반 정책의 정확도가 낮아질 수 있다.

### 5. QUIC/HTTP/3 계층

QUIC은 UDP 기반 전송 프로토콜이며 TLS 1.3을 통합해 보안 연결을 구성한다. TCP 기반 TLS 프록시가 ClientHello를 읽는 방식과 달리, QUIC에서는 Initial packet과 CRYPTO frame 구조를 이해해야 한다.

따라서 TCP 9443을 대상으로 하는 현재 테스트베드는 QUIC/HTTP/3 트래픽을 직접 분석하지 않는다. 보고서에서는 “TCP 기반 TLS/SNI 필터링과 QUIC 기반 관찰 구조가 다르다”는 점을 한계와 확장 방향으로 설명하는 것이 적절하다.

### 6. ECH와 암호화된 메타데이터

ECH(Encrypted Client Hello)는 TLS ClientHello의 민감한 정보를 암호화하는 표준이다. ECH가 널리 적용되면 기존 SNI 기반 장비는 실제 목적지 도메인을 직접 읽기 어려워진다.

이는 사용자 프라이버시 측면에서는 장점이지만, 네트워크 정책과 보안 모니터링 관점에서는 기존 도메인 기반 제어 모델을 약화시킨다. 따라서 향후 정책은 DNS 정책, 엔드포인트 정책, 승인된 프록시, 로그 분석 등과 결합되어야 한다.

## 기존 우회 기법의 개념적 분류

아래 항목은 보고서에서 “왜 단일 계층 검열이 완전하지 않은가”를 설명하기 위한 개념 분류다. 실제 사용 절차나 설정값은 연구 범위 밖이다.

| 분류 | 핵심 아이디어 | 주로 약화시키는 검열 방식 | 방어적 분석 관점 |
| --- | --- | --- | --- |
| 대체 DNS·암호화 DNS | 로컬 네트워크의 DNS 관찰·변조를 줄임 | DNS 변조/차단 | DNS만으로는 정책 완결성이 낮다는 점 설명 |
| 프록시 | 사용자가 직접 목적지와 연결하지 않고 중간 서버를 경유 | IP, DNS, HTTP, SNI 정책 일부 | 목적지 가시성이 프록시 주소로 축소되는 문제 설명 |
| VPN | 트래픽을 암호화된 터널로 묶어 전송 | DNS, SNI, HTTP, 일부 DPI | 네트워크 장비가 내부 목적지를 보기 어려운 구조 설명 |
| Tor/양파 라우팅 | 다중 홉 암호화 경로로 송수신자를 분리 | IP, DNS, 트래픽 출처 식별 | 익명성 네트워크의 목적과 정책 충돌 설명 |
| 도메인 프론팅 계열 | TLS 계층 이름과 애플리케이션 계층 목적지 불일치 활용 | SNI 기반 정책 | SNI와 실제 애플리케이션 목적지가 항상 같지 않다는 한계 설명 |
| 단편화·패킷 변형 계열 | 중간 장비의 재조립·파싱 한계를 이용 | 단순 DPI, 단순 SNI 파서 | 파서가 TCP/TLS 경계를 안정적으로 처리해야 함 |
| 프로토콜 위장 | 트래픽 형태를 허용된 프로토콜처럼 보이게 함 | 지문 기반 탐지 | 메타데이터 탐지의 오탐·회피 가능성 설명 |
| CDN·공유 인프라 경유 | 많은 서비스가 같은 인프라를 공유 | IP 차단 | IP 차단의 부수 피해와 정책 난이도 설명 |
| 미러·대체 도메인 | 차단 대상과 같은 콘텐츠를 다른 이름으로 제공 | 도메인 차단 | 도메인 목록 기반 정책의 유지 비용 설명 |
| 애플리케이션 내부 우회 | 플랫폼 내부 API, 앱 기능, 계정 정책 차이 활용 | 네트워크 계층 정책 | 네트워크 장비만으로 서비스 내부 행위를 판단하기 어렵다는 점 설명 |

## 본 프로젝트와 연결되는 부분

현재 테스트베드는 전체 검열 생태계를 구현하는 것이 아니라, 그중 TLS/SNI 기반 정책을 좁고 안전하게 재현한다.

직접 구현·검증한 항목:

- TLS ClientHello에서 SNI 추출
- `allowed.test` 허용
- `blocked.test` 차단
- `unknown.test` 기본 차단
- SNI 없는 연결 기본 차단
- 비정상 ClientHello 처리
- 업스트림 장애 로그 기록
- 동시 연결 처리

문서로 분석할 수 있는 확장 항목:

- DNS 차단과 SNI 차단의 차이
- IP 차단과 CDN 공유 인프라 문제
- HTTP 필터링과 HTTPS 필터링의 차이
- QUIC/HTTP/3에서 TCP 기반 SNI 파서가 그대로 적용되지 않는 이유
- ECH가 SNI 기반 정책에 주는 영향
- 기존 우회 기법이 어느 관찰 지점을 약화시키는지

현재 범위 밖으로 두는 항목:

- 외부 인터넷 대상 우회 실험
- 공용 VPN·프록시·Tor 연결 실험
- 실제 검열 시스템 회피 패킷 생성
- 도메인 프론팅 재현
- QUIC 파서 구현

## 보고서에 넣기 좋은 서술 구조

최종 보고서에서는 다음 흐름이 자연스럽다.

1. HTTPS 확산으로 콘텐츠 기반 중간 검사가 어려워졌다.
2. 검열·필터링은 DNS, IP, HTTP, TLS/SNI, QUIC, 애플리케이션 계층 등 여러 지점에서 이루어진다.
3. 각 방식은 관찰 가능한 정보가 다르며, 그만큼 한계도 다르다.
4. 기존 우회 기법은 대부분 특정 관찰 지점을 숨기거나, 우회하거나, 신뢰하기 어렵게 만드는 방식이다.
5. 본 프로젝트는 이 중 TLS/SNI 관찰 지점에 집중해, 폐쇄형 로컬 테스트베드에서 allow/block 정책을 구현하고 한계를 검증했다.
6. 결과적으로 SNI 기반 필터링은 간단하고 빠르지만, SNI 부재, ECH, QUIC, 애플리케이션 계층 비가시성 때문에 단독 정책으로는 한계가 있다.

## 참고 자료

- RFC 6066, Transport Layer Security Extensions: Extension Definitions: https://datatracker.ietf.org/doc/html/rfc6066
- RFC 8446, The Transport Layer Security Protocol Version 1.3: https://datatracker.ietf.org/doc/html/rfc8446
- RFC 8484, DNS Queries over HTTPS: https://datatracker.ietf.org/doc/html/rfc8484
- RFC 7858, Specification for DNS over Transport Layer Security: https://www.rfc-editor.org/rfc/rfc7858
- RFC 9000, QUIC: A UDP-Based Multiplexed and Secure Transport: https://www.rfc-editor.org/rfc/rfc9000
- RFC 9001, Using TLS to Secure QUIC: https://www.rfc-editor.org/rfc/rfc9001
- RFC 9460, Service Binding and Parameter Specification via the DNS: https://datatracker.ietf.org/doc/html/rfc9460
- RFC 9849, TLS Encrypted Client Hello: https://www.rfc-editor.org/rfc/rfc9849.html
- OONI, Interpreting OONI data: https://ooni.github.io/support/interpreting-ooni-data/
- OONI, Internet Censorship Fact Sheet: https://ooni.org/support/ooni-outreach-kit/files/Internet%20Censorship%20Fact%20Sheet%20for%20printing.pdf
- Fifield et al., Blocking-resistant communication through domain fronting: https://www.bamsoftware.com/papers/fronting/
- Bock et al., Geneva: Evolving Censorship Evasion Strategies: https://kevinbock.phd/publication/2019-geneva/
- Niere et al., Circumventing the GFW with TLS Record Fragmentation: https://upb-syssec.github.io/blog/2023/record-fragmentation/
