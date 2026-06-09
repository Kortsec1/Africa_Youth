# 최종 시연 스크립트

## 1. 시연 목표

로컬 폐쇄형 환경에서 TLS ClientHello의 SNI를 기준으로 HTTPS 연결이 허용 또는 차단되는 과정을 보여준다. 시연은 실제 외부 사이트나 공용 프록시를 대상으로 하지 않고, `allowed.test`, `blocked.test`, `unknown.test` 로컬 테스트 도메인만 사용한다.

## 2. 사전 준비

```bash
source .venv/bin/activate
./scripts/generate-cert.sh
```

## 3. 서버 실행

터미널 1:

```bash
python -m server.https_server
```

설명:

- 자체 서명 인증서를 사용하는 로컬 HTTPS 테스트 서버를 `127.0.0.1:8443`에서 실행한다.
- 실제 인터넷 서버가 아니라 실험용 JSON 응답 서버다.

## 4. 정책 프록시 실행

터미널 2:

```bash
python -m proxy.main
```

설명:

- 프록시는 `127.0.0.1:9443`에서 TLS 연결을 받는다.
- ClientHello에서 SNI를 추출하고 `configs/policy.yaml`에 따라 `allow` 또는 `block`을 결정한다.

## 5. 허용 테스트

터미널 3:

```bash
./scripts/test-allowed.sh
```

예상 설명:

- `allowed.test`가 SNI로 전달된다.
- 정책 파일의 allow 규칙과 매칭된다.
- 프록시는 테스트 HTTPS 서버로 TCP 스트림을 중계한다.
- 클라이언트는 HTTP 200 JSON 응답을 받는다.

## 6. 차단 테스트

```bash
./scripts/test-blocked.sh
```

예상 설명:

- `blocked.test`가 SNI로 전달된다.
- 정책 파일의 block 규칙과 매칭된다.
- 프록시는 upstream 서버로 연결하지 않고 TLS 연결을 종료한다.
- 클라이언트에서는 TLS EOF 또는 handshake 실패가 보인다.

## 7. 기본 정책 테스트

```bash
./scripts/test-unknown.sh
```

예상 설명:

- `unknown.test`는 정책 파일에 없는 SNI다.
- 기본 정책 `default_action: block`이 적용된다.
- allow-list 방식의 기본 차단 동작을 확인할 수 있다.

## 8. 로그 확인

```bash
tail -n 20 logs/proxy.jsonl
```

설명할 필드:

- `extracted_sni`: ClientHello에서 추출한 SNI
- `decision`: `allow` 또는 `block`
- `reason`: 정책 판단 이유
- `elapsed_ms`: 처리 시간
- `bytes_client_to_upstream`, `bytes_upstream_to_client`: 실제 중계 여부
- `error`: 파싱 오류 또는 upstream 연결 오류

## 9. 마무리 문장

이 테스트베드는 TLS 내용을 복호화하지 않고도 ClientHello의 SNI만으로 제한적인 도메인 단위 정책을 적용할 수 있음을 보여준다. 동시에 SNI 없음, ECH, QUIC/HTTP3, 애플리케이션 계층 정보 비가시성 같은 구조적 한계도 함께 확인할 수 있다.
