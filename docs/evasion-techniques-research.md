# SNI 기반 필터링 우회·회피 기법 조사

## 1. 조사 목적

본 문서는 TLS/SNI 기반 필터링 테스트베드의 한계를 설명하기 위해 관련 우회·회피 기법을 조사한 자료다. 목적은 실제 인터넷 차단 우회 방법을 제공하는 것이 아니라, SNI 기반 정책이 어떤 가정에 의존하고 어떤 상황에서 정확도가 떨어지는지 방어적 관점에서 분석하는 것이다.

다루는 범위:

- SNI 기반 필터링의 관찰 지점
- SNI 부재, 기본 정책, 파싱 실패에 따른 한계
- ECH, QUIC, 암호화 DNS 등 프로토콜 변화의 영향
- 도메인 프론팅, 단편화, 트래픽 형태 변화 같은 연구 사례의 개념적 분류
- 로컬 테스트베드에서 안전하게 관찰 가능한 항목

다루지 않는 범위:

- 실제 차단 사이트 우회 절차
- 공용 프록시, VPN, 터널링 도구 설정법
- 특정 검열 시스템을 대상으로 한 우회 명령, 코드, 자동화
- 외부 서비스나 CDN을 이용한 재현 방법

## 2. 배경: SNI 기반 필터링의 전제

SNI(Server Name Indication)는 TLS ClientHello에 포함될 수 있는 확장 필드다. RFC 6066은 클라이언트가 이름 기반 서버에 접속할 때 `server_name` 확장을 포함할 것을 권장하며, 서버가 이를 인증서 선택이나 보안 정책 판단에 활용할 수 있다고 설명한다.

SNI 기반 필터링은 다음 전제에 의존한다.

| 전제 | 설명 | 약해지는 경우 |
| --- | --- | --- |
| 클라이언트가 SNI를 보낸다 | ClientHello에 대상 도메인이 들어 있다 | SNI 없음, IP 직접 접속, 특수 클라이언트 |
| SNI가 평문으로 보인다 | 중간 장비가 ClientHello를 읽을 수 있다 | ECH, QUIC/ECH 조합 |
| SNI와 실제 목적지가 일치한다 | TLS 계층 이름과 애플리케이션 계층 요청이 일치한다 | 도메인 프론팅 계열, Host/SNI 불일치 |
| ClientHello를 정상 파싱할 수 있다 | 프록시가 TCP/TLS 스트림을 재조립하고 파싱한다 | TCP/TLS/QUIC 단편화, 비정상 입력 |
| 도메인 단위 정책으로 충분하다 | URL 경로, 사용자, API 동작까지 보지 않아도 된다 | 세부 URL 정책, 앱 내부 트래픽, CDN 공유 인프라 |

## 3. 관련 우회·회피 기법 분류

### 3.1 SNI 미제공

SNI가 없는 TLS 연결은 도메인 기반 정책 장비가 대상을 직접 식별하기 어렵다. 이 경우 정책은 보통 기본 정책에 의존한다.

정책 선택지는 다음과 같다.

| 기본 정책 | 장점 | 단점 |
| --- | --- | --- |
| SNI 없음 차단 | 우회 가능성을 줄임 | 일부 정상 레거시 클라이언트가 차단될 수 있음 |
| SNI 없음 허용 | 호환성이 높음 | 도메인 기반 차단 회피 가능성이 커짐 |
| 별도 격리/로그 | 분석 가능성 확보 | 운영 정책이 복잡해짐 |

본 프로젝트의 기본 정책은 `block`이므로 SNI 없는 연결은 차단된다. 실제 테스트에서도 `openssl s_client -connect 127.0.0.1:9443` 실행 시 `extracted_sni=null`, `decision=block`으로 기록되었다.

### 3.2 알 수 없는 SNI

정책 파일에 없는 SNI가 들어오면 명시적 규칙을 적용할 수 없다. allow-list 방식에서는 알 수 없는 SNI를 차단하는 것이 일반적으로 더 안전하다.

본 프로젝트에서는 `unknown.test`를 통해 이 상황을 관찰했다. 결과는 `decision=block`, `reason=알 수 없는 SNI: 기본 정책 적용`이었다.

### 3.3 SNI와 애플리케이션 계층 목적지 불일치

SNI는 TLS 계층의 서버 이름이고, HTTP Host 헤더나 URL 경로는 TLS 암호화 이후 애플리케이션 계층에 위치한다. TLS를 복호화하지 않는 중간 장비는 HTTP Host, URL, 본문을 볼 수 없다.

이 구조적 차이를 이용하는 대표적 개념이 도메인 프론팅이다. 도메인 프론팅은 TLS 계층에서 관찰되는 이름과 애플리케이션 계층에서 처리되는 목적지가 달라질 수 있다는 점을 이용한 것으로 연구되었다. 다만 현재 많은 대형 서비스 제공자는 서비스 약관과 인프라 정책상 이를 제한하거나 비활성화했다.

방어적 시사점:

- SNI만으로 HTTP Host나 URL 경로까지 검증할 수 없다.
- TLS 복호화 없이 가능한 검사는 도메인 단위 정책에 가깝다.
- SNI/인증서/목적지 IP/DNS 기록 간 불일치를 탐지 지표로 사용할 수 있으나, 완전한 애플리케이션 계층 검증은 어렵다.

### 3.4 ECH(Encrypted ClientHello)

ECH는 TLS 1.3에서 ClientHelloInner를 암호화해 SNI 같은 민감 정보를 외부 관찰자로부터 숨기는 기술이다. RFC 9849는 ECH가 서버 이름과 ClientHello 내용에 대한 기밀성 메커니즘을 제공한다고 설명한다. ECH에서는 외부에서 보이는 ClientHelloOuter와 암호화된 ClientHelloInner가 분리된다.

ECH가 적용되면 SNI 기반 장비는 실제 목적지 이름을 직접 읽지 못할 수 있다. 이때 중간 장비는 다음과 같은 제한을 받는다.

| 관찰 가능 정보 | 한계 |
| --- | --- |
| ClientHelloOuter의 공개 이름 | 실제 서비스 이름과 다를 수 있음 |
| 목적지 IP | CDN/공유 호스팅에서는 여러 서비스가 같은 IP 사용 |
| DNS 로그 | DoH/DoT, 캐시, 외부 리졸버 사용 시 가시성 제한 |
| 인증서 정보 | TLS 1.3에서는 서버 인증서가 암호화되어 단순 관찰이 어려움 |

ECH 설정 정보는 DNS HTTPS/SVCB 레코드와 관련된다. RFC 9460은 HTTPS/SVCB 리소스 레코드가 서비스 접속 매개변수를 전달하는 방식을 정의하며, ECH 배포에서도 이 경로가 중요해진다.

방어적 시사점:

- 기존 SNI 기반 allow/block 정책은 ECH 확산에 따라 정확도가 낮아질 수 있다.
- 네트워크 정책은 DNS 정책, 엔드포인트 정책, 프록시 정책, 애플리케이션 제어와 함께 설계해야 한다.
- 단순히 ECH를 차단하는 접근은 개인정보 보호와 호환성 문제를 동반할 수 있다.

### 3.5 ClientHello 단편화와 재조립 한계

일부 검열 회피 연구는 중간 장비가 TCP 스트림이나 TLS record를 충분히 재조립하지 못한다는 점을 다룬다. 예를 들어 TLS ClientHello가 여러 조각으로 나뉘면 단순한 단일 패킷/단일 레코드 파서는 SNI를 놓칠 수 있다.

이 범주는 구현 취약점 또는 중간 장비의 성능·상태관리 한계와 관련된다.

방어적 시사점:

- SNI 파서는 단일 `read()` 결과에만 의존하면 안 된다.
- TCP 스트림 재조립, TLS record 경계 처리, 길이 검증, 타임아웃 정책이 필요하다.
- 지나치게 긴 ClientHello, 과도한 단편화, 비정상 record 구조는 별도 로그로 기록해야 한다.

본 프로젝트의 현재 프록시는 최초 읽기 버퍼에서 ClientHello를 파싱한다. 로컬 테스트에서는 일반 curl/openssl 입력을 대상으로 동작을 확인했지만, 고도화된 단편화 재조립까지 검증하는 구조는 아니다. 향후 방어적 개선 항목으로 볼 수 있다.

### 3.6 QUIC/HTTP/3 기반 변화

QUIC은 UDP 기반 전송 프로토콜이며 TLS 1.3을 보안 구성요소로 사용한다. RFC 9001은 QUIC이 TLS를 사용해 보안 연결을 구성한다고 설명한다. QUIC의 첫 Initial packet에는 TLS ClientHello의 시작 또는 전체가 포함될 수 있으며, 서버가 SNI나 ALPN을 보기 위해 전체 ClientHello를 파싱해야 할 수 있다.

QUIC 환경에서의 관찰 지점은 TCP 기반 TLS와 다르다.

| 항목 | TCP 기반 TLS | QUIC/HTTP/3 |
| --- | --- | --- |
| 전송 계층 | TCP | UDP |
| 핸드셰이크 운반 | TLS record over TCP | QUIC CRYPTO frame |
| 중간 장비 파싱 | TCP 재조립 필요 | QUIC Initial 해석 필요 |
| 정책 영향 | SNI 파서 중심 | QUIC/TLS 통합 파서 필요 |

방어적 시사점:

- TCP 9443만 관찰하는 현재 테스트베드는 QUIC/HTTP/3 트래픽을 다루지 않는다.
- 실제 네트워크 정책에서는 UDP 443 기반 QUIC 트래픽을 별도로 고려해야 한다.
- ECH와 QUIC이 함께 확산되면 도메인 기반 가시성은 더 줄어들 수 있다.

### 3.7 암호화 DNS: DoH/DoT

SNI 필터링은 DNS 필터링과 함께 쓰이는 경우가 많다. 그러나 DNS over HTTPS(DoH)와 DNS over TLS(DoT)는 DNS 질의를 암호화된 채널로 전송한다. RFC 8484는 DNS 질의를 HTTPS로 전달하는 방식을 정의하고, RFC 7858은 DNS over TLS를 정의한다.

암호화 DNS 자체가 SNI를 직접 우회하는 것은 아니지만, 네트워크 관리자가 DNS 질의를 통해 목적 도메인을 관찰하거나 차단하는 능력을 줄일 수 있다.

방어적 시사점:

- DNS 로그와 SNI 로그를 함께 분석하던 정책은 가시성이 낮아질 수 있다.
- 승인된 DNS 리졸버 정책, 엔드포인트 DNS 설정 관리, 네트워크 출구 정책이 중요하다.
- 개인정보 보호 목적의 암호화 DNS와 조직 보안 정책 사이의 균형이 필요하다.

### 3.8 트래픽 형태·지문 변화

SNI 외에도 TLS 버전, cipher suite 목록, extension 순서, ALPN, record 크기, 타이밍 같은 메타데이터가 트래픽 지문으로 사용될 수 있다. 일부 회피 연구는 이런 지문을 바꾸거나 정상 트래픽과 비슷하게 보이도록 만드는 방향을 다룬다.

방어적 시사점:

- SNI 하나만으로 정책을 결정하면 우회 가능성과 오탐 가능성이 함께 커진다.
- 메타데이터 기반 탐지는 개인정보와 오탐 문제를 동반한다.
- 정책은 차단보다 관찰, 위험 점수화, 사후 분석과 결합하는 것이 안정적이다.

## 4. 프로젝트와의 관련성

현재 테스트베드에서 직접 안전하게 관찰 가능한 항목은 다음과 같다.

| 항목 | 현재 재현 여부 | 관련 파일 |
| --- | --- | --- |
| 허용 SNI | 가능 | `scripts/test-allowed.sh` |
| 차단 SNI | 가능 | `scripts/test-blocked.sh` |
| 알 수 없는 SNI | 가능 | `scripts/test-unknown.sh` |
| SNI 없음 | 가능 | `openssl s_client -connect 127.0.0.1:9443` |
| 비정상 ClientHello | 가능 | `printf ... | nc 127.0.0.1 9443` |
| 업스트림 장애 | 가능 | 서버 종료 후 허용 SNI 요청 |
| 동시 연결 | 가능 | 병렬 curl 실행 |
| ECH | 현재 미지원 | 향후 개념 분석 또는 별도 실험 필요 |
| QUIC/HTTP/3 | 현재 미지원 | UDP/QUIC 파서 필요 |
| TLS record 단편화 | 현재 미검증 | ClientHello 재조립 로직 개선 필요 |
| 실제 도메인 프론팅 | 범위 밖 | 외부 서비스 대상 실험 금지 |

## 5. 방어적 개선 아이디어

본 프로젝트를 확장한다면 다음 개선을 고려할 수 있다.

| 개선 항목 | 목적 |
| --- | --- |
| ClientHello 누적 읽기 | 단일 read에 들어오지 않는 ClientHello 처리 |
| TLS record 경계 파싱 | 여러 record로 나뉜 ClientHello 탐지 |
| 최대 길이·시간 제한 | 과도한 단편화나 지연 입력으로 인한 자원 소모 방지 |
| 로그 필드 확장 | TLS 버전, ALPN, SNI 존재 여부, 파싱 오류 유형 기록 |
| 정책 모드 분리 | `allow-list`, `block-list`, `monitor-only` 모드 비교 |
| QUIC 트래픽 별도 문서화 | TCP 기반 TLS와 QUIC 기반 TLS의 차이 정리 |
| ECH 영향 분석 문서화 | SNI 기반 정책의 장기적 한계 설명 |

주의할 점은, 위 개선은 방어적 관찰과 정책 정확도 향상을 위한 것이며 실제 외부 차단 회피 실험을 목적으로 하지 않는다.

## 6. 요약

SNI 기반 필터링은 TLS 복호화 없이 도메인 단위 정책을 적용할 수 있다는 장점이 있다. 하지만 다음과 같은 구조적 한계를 가진다.

- SNI가 없으면 도메인을 식별하기 어렵다.
- 정책에 없는 SNI는 기본 정책에 의존한다.
- SNI는 HTTP Host, URL, 본문과 같은 애플리케이션 계층 정보를 보장하지 않는다.
- ECH가 적용되면 실제 SNI를 직접 관찰하기 어려워진다.
- 단순 파서는 ClientHello 단편화나 비정상 입력에 취약할 수 있다.
- QUIC/HTTP/3은 TCP 기반 SNI 파서와 다른 관찰 구조를 요구한다.
- DoH/DoT는 DNS 기반 보조 관찰 지점을 약화시킬 수 있다.

따라서 SNI 기반 정책은 단독 통제 수단이 아니라 로컬 정책, DNS 정책, 엔드포인트 보안, 로그 분석, 사용자 고지와 함께 설계해야 한다.

## 7. 참고 자료

- RFC 6066, Transport Layer Security Extensions: Extension Definitions: https://datatracker.ietf.org/doc/html/rfc6066
- RFC 8446, The Transport Layer Security Protocol Version 1.3: https://datatracker.ietf.org/doc/html/rfc8446
- RFC 9849, TLS Encrypted Client Hello: https://datatracker.ietf.org/doc/html/rfc9849
- RFC 9460, Service Binding and Parameter Specification via the DNS: https://datatracker.ietf.org/doc/html/rfc9460
- RFC 9001, Using TLS to Secure QUIC: https://www.rfc-editor.org/info/rfc9001/
- RFC 8484, DNS Queries over HTTPS: https://www.rfc-editor.org/info/rfc8484
- RFC 7858, Specification for DNS over Transport Layer Security: https://www.rfc-editor.org/rfc/rfc7858
- Fifield et al., Blocking-resistant communication through domain fronting: https://www.bamsoftware.com/papers/fronting/
- Bock et al., Geneva: Evolving Censorship Evasion Strategies: https://kevinbock.phd/publication/2019-geneva/
- Niere et al., Circumventing the GFW with TLS Record Fragmentation: https://upb-syssec.github.io/blog/2023/record-fragmentation/
- Niere et al., Transport Layer Obscurity: Circumventing SNI Censorship on the TLS-Layer: https://ris.uni-paderborn.de/record/59824
