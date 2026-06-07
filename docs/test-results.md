# 테스트 결과 기록

## 실행 개요

날짜: 2026-06-07

실행 위치: `/Users/handonghun/capstonedesign`

대상 커밋: `ffb7bd0`

실행 환경:

- OS: macOS
- Python: `.venv/bin/python` 3.9.6
- curl: 8.16.0
- pytest: 8.4.2

산출물:

- 명령 출력 캡처: `captures/test-run-20260607/`
- 프록시 JSONL 로그: `logs/test-run-20260607-212353.jsonl`
- 프록시 JSONL 로그 복사본: `captures/test-run-20260607/proxy-log.jsonl`
- tcpdump 캡처 시도 기록: `captures/test-run-20260607/00-tcpdump.txt`

참고:

- 이 환경에서는 localhost 포트 바인딩과 접속에 권한 승인이 필요했다.
- `sudo tcpdump`는 macOS sudo 비밀번호가 필요해 비대화형 실행으로는 pcap 파일을 생성하지 못했다.
- 프로젝트 요구사항은 Python 3.11 이상이지만 현재 `.venv`는 Python 3.9.6이다.

## 1. 정상 허용 테스트

명령:

```bash
./scripts/test-allowed.sh
```

예상 결과:

SNI `allowed.test`, 정책 `allow`, 테스트 서버 JSON 응답.

실제 결과:

성공. curl exit code는 `0`이며 테스트 서버 JSON 응답을 수신했다.

로그 확인:

- `extracted_sni`: `allowed.test`
- `decision`: `allow`
- `error`: `null`
- `bytes_client_to_upstream`: `1750`
- `bytes_upstream_to_client`: `1545`

캡처 파일:

`captures/test-run-20260607/01-allowed.txt`

## 2. 정상 차단 테스트

명령:

```bash
./scripts/test-blocked.sh
```

예상 결과:

SNI `blocked.test`, 정책 `block`, 업스트림 연결 없음.

실제 결과:

성공. curl은 TLS 연결 중 EOF로 exit code `35`를 반환했다. 이는 프록시가 정책에 따라 연결을 종료한 결과다.

로그 확인:

- `extracted_sni`: `blocked.test`
- `decision`: `block`
- `error`: `null`
- `bytes_client_to_upstream`: `0`
- `bytes_upstream_to_client`: `0`

캡처 파일:

`captures/test-run-20260607/02-blocked.txt`

## 3. 알 수 없는 SNI 테스트

명령:

```bash
./scripts/test-unknown.sh
```

예상 결과:

SNI `unknown.test`, 기본 정책 `block`.

실제 결과:

성공. curl은 TLS 연결 중 EOF로 exit code `35`를 반환했고, 프록시 로그에는 기본 정책 차단으로 기록됐다.

로그 확인:

- `extracted_sni`: `unknown.test`
- `decision`: `block`
- `reason`: `알 수 없는 SNI: 기본 정책 적용`
- `error`: `null`

캡처 파일:

`captures/test-run-20260607/03-unknown.txt`

## 4. SNI 없는 연결 테스트

명령:

```bash
openssl s_client -connect 127.0.0.1:9443 < /dev/null
```

예상 결과:

SNI 없음, 기본 정책 `block`.

실제 결과:

성공. openssl은 EOF로 exit code `1`을 반환했고, 프록시 로그에는 SNI 없음에 따른 차단으로 기록됐다.

로그 확인:

- `extracted_sni`: `null`
- `decision`: `block`
- `reason`: `SNI 없음: 기본 정책 적용`
- `error`: `null`

캡처 파일:

`captures/test-run-20260607/04-no-sni.txt`

## 5. 비정상 ClientHello 테스트

명령:

```bash
printf "not tls client hello" | nc 127.0.0.1 9443
```

예상 결과:

ClientHello 파싱 실패 후 기본 정책 적용.

실제 결과:

성공. 프록시는 TLS handshake record가 아니라고 판단했고 기본 정책 `block`을 적용했다.

로그 확인:

- `extracted_sni`: `null`
- `decision`: `block`
- `error`: `not a TLS handshake record`

캡처 파일:

`captures/test-run-20260607/05-invalid-clienthello.txt`

## 6. 테스트 서버 장애 테스트

절차:

1. HTTPS 테스트 서버 종료
2. 정책 프록시는 유지
3. `allowed.test` 요청 실행

명령:

```bash
./scripts/test-allowed.sh
```

예상 결과:

정책 판단은 `allow`지만 업스트림 연결 실패 오류가 로그에 기록됨.

실제 결과:

성공. curl은 TLS 연결 중 EOF로 exit code `35`를 반환했고, 프록시 로그에는 업스트림 연결 실패가 기록됐다.

로그 확인:

- `extracted_sni`: `allowed.test`
- `decision`: `allow`
- `error`: `[Errno 61] Connect call failed ('127.0.0.1', 8443)`

캡처 파일:

`captures/test-run-20260607/06-upstream-down.txt`

## 7. pytest 통합 테스트

명령:

```bash
.venv/bin/python -m pytest -q
```

예상 결과:

순차 연결, 서버 장애, 포트 충돌 등 통합 테스트 통과.

실제 결과:

실패. 테스트 수집 단계에서 Python 3.9 환경이 `str | None` 타입 표기를 처리하지 못해 중단됐다.

오류 요약:

```text
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

판단:

프로젝트 요구사항인 Python 3.11 이상 환경에서 재실행해야 한다.

캡처 파일:

`captures/test-run-20260607/07-pytest.txt`

## 8. 동시 연결 수동 테스트

명령 요약:

```bash
allowed.test, blocked.test, unknown.test, allowed.test, blocked.test 요청 5개 병렬 실행
```

예상 결과:

동시 요청에서도 각 SNI에 맞는 정책 결정이 독립적으로 기록됨.

실제 결과:

성공. `allowed.test` 2건은 HTTP 200 JSON 응답을 받았고, `blocked.test` 2건과 `unknown.test` 1건은 정책 차단으로 TLS EOF가 발생했다.

로그 확인:

- `allowed.test`: 2건 `allow`, `error=null`
- `blocked.test`: 2건 `block`, `error=null`
- `unknown.test`: 1건 `block`, `error=null`

캡처 파일:

- `captures/test-run-20260607/08-concurrent-1-allowed.test.txt`
- `captures/test-run-20260607/08-concurrent-2-blocked.test.txt`
- `captures/test-run-20260607/08-concurrent-3-unknown.test.txt`
- `captures/test-run-20260607/08-concurrent-4-allowed.test.txt`
- `captures/test-run-20260607/08-concurrent-5-blocked.test.txt`

## tcpdump pcap 캡처

명령:

```bash
sudo -n tcpdump -i lo0 port 9443 -w captures/tls-local-test.pcap
```

예상 결과:

loopback 인터페이스의 9443 포트 트래픽을 pcap 파일로 저장.

실제 결과:

미수행. `sudo: a password is required`로 실패했다. Codex 비대화형 실행 환경에서는 sudo 비밀번호를 입력할 수 없어 pcap 파일을 만들지 못했다.

대체 산출물:

- curl/openssl/nc 명령 출력 캡처
- 프록시 JSONL 정책 결정 로그
