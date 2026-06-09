# TLS/SNI 필터링 테스트 결과 보고서

## 1. 개요

본 보고서는 로컬 TLS/SNI 필터링 테스트베드에서 수행한 정책 프록시 동작 검증 결과를 정리한 것이다. 테스트 대상 시스템은 HTTPS 트래픽을 복호화하지 않고 TLS ClientHello에 포함된 SNI(Server Name Indication)를 추출한 뒤, YAML 정책에 따라 연결을 허용하거나 차단한다.

이번 테스트의 목적은 다음과 같다.

- `allowed.test` 요청이 정책에 따라 정상적으로 허용되는지 확인한다.
- `blocked.test` 요청이 정책에 따라 차단되는지 확인한다.
- 정책에 없는 SNI, SNI가 없는 연결, 비정상 ClientHello에 대해 기본 차단 정책이 적용되는지 확인한다.
- 업스트림 테스트 서버 장애 상황에서 오류가 로그에 기록되는지 확인한다.
- 여러 연결이 동시에 들어와도 각 요청이 독립적으로 정책 처리되는지 확인한다.

## 2. 테스트 환경

| 항목 | 내용 |
| --- | --- |
| 실행 날짜 | 2026-06-07 |
| 실행 경로 | `/Users/handonghun/capstonedesign` |
| 대상 커밋 | `e186364` 기준 수동 결과, 2026-06-09 점검 보완 포함 |
| OS | macOS |
| Python | `.venv/bin/python` 3.9.6 |
| curl | 8.16.0 |
| pytest | 8.4.2 |
| 정책 프록시 주소 | `127.0.0.1:9443` |
| 테스트 HTTPS 서버 주소 | `127.0.0.1:8443` |

실제 실행 환경의 가상환경은 Python 3.9.6이다. 2026-06-07 수동 시나리오 실행에는 문제가 없었고, 2026-06-09 점검에서 테스트 타입 표기 호환성을 보완한 뒤 pytest 전체 통과를 확인했다.

## 3. 테스트 대상 구조

테스트베드는 클라이언트, 정책 프록시, 로컬 HTTPS 테스트 서버로 구성된다.

```text
Client
  curl / openssl / nc
        |
        v
127.0.0.1:9443
Policy Proxy
  - TLS ClientHello 수신
  - SNI 추출
  - YAML 정책 평가
  - allow: 127.0.0.1:8443으로 TCP 중계
  - block: 연결 종료
        |
        v
127.0.0.1:8443
Test HTTPS Server
```

기본 정책은 다음과 같다.

| SNI | 정책 | 설명 |
| --- | --- | --- |
| `allowed.test` | `allow` | 허용된 로컬 테스트 도메인 |
| `blocked.test` | `block` | 차단 동작 확인용 로컬 테스트 도메인 |
| 그 외 SNI | `block` | 기본 정책 적용 |
| SNI 없음 | `block` | 기본 정책 적용 |

## 4. 테스트 산출물

| 산출물 | 경로 |
| --- | --- |
| 상세 테스트 결과 기록 | `docs/test-results.md` |
| 명령 출력 캡처 | `captures/test-run-20260607/` |
| 프록시 로그 복사본 | `captures/test-run-20260607/proxy-log.jsonl` |
| tcpdump 캡처 시도 기록 | `captures/test-run-20260607/00-tcpdump.txt` |
| 원본 프록시 로그 | `logs/test-run-20260607-212353.jsonl` |

`logs/*.jsonl` 파일은 `.gitignore` 대상이므로, 보고서 검토용으로 같은 내용을 `captures/test-run-20260607/proxy-log.jsonl`에 복사했다.

## 5. 시나리오별 결과

| 번호 | 시나리오 | 입력/명령 | 예상 결과 | 실제 결과 | 판정 |
| --- | --- | --- | --- | --- | --- |
| 1 | 정상 허용 | `./scripts/test-allowed.sh` | `allowed.test` 허용 및 JSON 응답 | HTTP 200 JSON 응답, `decision=allow` | 성공 |
| 2 | 정상 차단 | `./scripts/test-blocked.sh` | `blocked.test` 차단 | TLS EOF, `decision=block` | 성공 |
| 3 | 알 수 없는 SNI | `./scripts/test-unknown.sh` | 기본 정책 차단 | TLS EOF, `decision=block` | 성공 |
| 4 | SNI 없는 연결 | `openssl s_client -connect 127.0.0.1:9443 < /dev/null` | SNI 없음으로 차단 | `extracted_sni=null`, `decision=block` | 성공 |
| 5 | 비정상 ClientHello | `printf "not tls client hello" \| nc 127.0.0.1 9443` | 파싱 실패 후 차단 | `error=not a TLS handshake record`, `decision=block` | 성공 |
| 6 | 테스트 서버 장애 | 서버 종료 후 `allowed.test` 요청 | 정책은 허용, 업스트림 오류 기록 | `decision=allow`, 연결 실패 오류 기록 | 성공 |
| 7 | pytest 통합 테스트 | `.venv/bin/python -m pytest -q` | 통합 테스트 통과 | 12개 테스트 통과 | 성공 |
| 8 | 동시 연결 | 5개 요청 병렬 실행 | 각 SNI별 독립 처리 | 허용 2건, 차단 3건 모두 정책대로 처리 | 성공 |

## 6. 주요 로그 분석

### 6.1 허용 정책 동작

`allowed.test` 요청은 정책상 `allow`로 판단되었고, 업스트림 테스트 서버와 실제 데이터 교환이 발생했다.

```text
extracted_sni=allowed.test
decision=allow
error=null
bytes_client_to_upstream=1750
bytes_upstream_to_client=1545
```

이는 프록시가 ClientHello에서 SNI를 정상 추출하고, 허용 정책에 따라 `127.0.0.1:8443` 테스트 서버로 TCP 중계를 수행했음을 의미한다. curl 출력에서도 HTTP 200 응답과 테스트 서버 JSON 메시지가 확인되었다.

### 6.2 차단 정책 동작

`blocked.test` 요청은 정책상 `block`으로 판단되었으며, 업스트림으로 전달된 바이트 수가 0으로 기록되었다.

```text
extracted_sni=blocked.test
decision=block
error=null
bytes_client_to_upstream=0
bytes_upstream_to_client=0
```

curl에서는 TLS handshake 중 `unexpected eof while reading` 오류가 발생했다. 이는 프록시가 연결을 의도적으로 종료했기 때문에 나타나는 예상 가능한 클라이언트 측 결과다.

### 6.3 기본 정책 적용

정책에 등록되지 않은 `unknown.test`는 기본 정책에 따라 차단되었다.

```text
extracted_sni=unknown.test
decision=block
reason=알 수 없는 SNI: 기본 정책 적용
```

SNI가 없는 연결 역시 `extracted_sni=null`로 기록되었고, 기본 정책에 따라 차단되었다.

```text
extracted_sni=null
decision=block
reason=SNI 없음: 기본 정책 적용
```

이를 통해 정책 프록시가 허용 목록에 없는 요청을 안전하게 차단하는 기본 동작을 수행함을 확인했다.

### 6.4 비정상 입력 처리

TLS ClientHello 형식이 아닌 임의 바이트를 전송했을 때, 프록시는 파싱 오류를 로그에 기록하고 차단 정책을 적용했다.

```text
extracted_sni=null
decision=block
error=not a TLS handshake record
```

이 결과는 비정상 입력이 들어와도 프록시가 예외 상황을 로그로 남기고 안전한 기본 정책으로 처리한다는 점을 보여준다.

### 6.5 업스트림 장애 처리

테스트 HTTPS 서버를 종료한 상태에서 `allowed.test`를 요청하면, 정책 판단 자체는 `allow`로 기록되었다. 하지만 업스트림 서버에 연결할 수 없기 때문에 오류가 함께 남았다.

```text
extracted_sni=allowed.test
decision=allow
error=[Errno 61] Connect call failed ('127.0.0.1', 8443)
```

이 결과는 정책 판단과 실제 연결 성공 여부가 구분되어 기록됨을 의미한다. 즉, 정책상 허용된 요청이라도 업스트림 서버 장애가 발생하면 오류 로그를 통해 원인을 추적할 수 있다.

### 6.6 동시 연결 처리

5개의 요청을 병렬로 실행한 결과, 각 연결은 독립적으로 정책 판단되었다.

| SNI | 요청 수 | 정책 결과 |
| --- | ---: | --- |
| `allowed.test` | 2 | `allow` 2건 |
| `blocked.test` | 2 | `block` 2건 |
| `unknown.test` | 1 | `block` 1건 |

동시 요청에서도 허용 요청은 HTTP 200 응답을 받았고, 차단 요청은 업스트림으로 전달되지 않았다. 이를 통해 비동기 기반 프록시가 여러 연결을 동시에 처리하면서도 정책 결정을 독립적으로 수행함을 확인했다.

## 7. pytest 결과

2026-06-09 점검에서 pytest를 재실행한 결과 전체 테스트가 통과했다.

```text
12 passed in 1.73s
```

실행 명령:

```bash
.venv/bin/python -m pytest -q
```

참고로 샌드박스 내부에서는 로컬 포트 바인딩 권한 제한으로 통합 테스트가 `PermissionError`를 낼 수 있다. 이 경우 샌드박스 밖 또는 로컬 포트 바인딩이 허용된 환경에서 실행해야 한다.

## 8. 패킷 캡처 결과

tcpdump를 이용한 pcap 캡처는 시도했으나 실패했다.

```bash
sudo -n tcpdump -i lo0 port 9443 -w captures/tls-local-test.pcap
```

실패 사유:

```text
sudo: a password is required
```

현재 실행 환경은 비대화형이므로 macOS sudo 비밀번호를 입력할 수 없었다. 따라서 pcap 파일은 생성하지 못했다. 대신 각 시나리오의 curl, openssl, nc 명령 출력과 프록시 JSONL 로그를 증거 자료로 보관했다.

수동 패킷 캡처가 필요하면 로컬 터미널에서 다음 명령을 직접 실행하면 된다.

```bash
sudo tcpdump -i lo0 port 9443 -w captures/tls-local-test.pcap
```

## 9. 종합 평가

이번 테스트에서 정책 프록시는 핵심 요구사항을 대부분 만족했다.

- TLS 복호화 없이 ClientHello의 SNI를 기준으로 정책을 판단했다.
- 허용된 SNI는 로컬 업스트림 서버로 정상 중계했다.
- 차단 대상 SNI, 알 수 없는 SNI, SNI 없는 연결은 기본 정책에 따라 차단했다.
- 비정상 ClientHello 입력에 대해 오류를 기록하고 안전하게 차단했다.
- 업스트림 서버 장애 상황에서 정책 판단과 연결 실패 오류를 로그로 구분해 기록했다.
- 동시 연결 상황에서도 각 요청을 독립적으로 처리했다.

제한 사항은 다음과 같다.

- 샌드박스 내부에서는 로컬 포트 바인딩 권한 제한으로 통합 테스트가 실패할 수 있다.
- sudo 권한 입력이 필요한 tcpdump pcap 캡처는 비대화형 환경에서 수행하지 못했다.
- 실험은 로컬 테스트 도메인과 로컬 업스트림 서버에 한정되므로 실제 인터넷 트래픽 차단 성능을 평가하는 실험은 아니다.

## 10. 결론

수동 시나리오와 프록시 로그 분석 결과, 본 TLS/SNI 필터링 테스트베드는 로컬 환경에서 SNI 기반 allow/block 정책을 의도대로 수행했다. 특히 허용, 차단, 기본 차단, 비정상 입력, 업스트림 장애, 동시 연결 상황이 모두 로그로 확인되었으므로, 교육 및 구조 분석 목적의 테스트베드로서 핵심 기능은 정상 동작한다고 판단된다.

다만 최종 검증 완성도를 높이기 위해서는 로컬 터미널에서 sudo 권한으로 tcpdump pcap 캡처를 추가 수행하는 것이 필요하다.
