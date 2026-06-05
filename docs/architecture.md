# 아키텍처

## 전체 구성

```text
Client(curl, openssl)
  -> Policy Proxy(:9443)
  -> Test HTTPS Server(:8443)
```

## 로컬 프로세스 구조

서버와 프록시는 같은 호스트에서 별도 Python 프로세스로 실행된다. 프록시는 `127.0.0.1:9443`에서 클라이언트를 받고, 허용된 경우에만 `127.0.0.1:8443`으로 연결한다.

## Docker Compose 구조

`policy-proxy`와 `test-server` 컨테이너가 같은 Compose 네트워크에서 실행된다. 호스트 클라이언트는 `localhost:9443`으로 접속한다.

## 허용 흐름

1. 클라이언트가 ClientHello를 전송한다.
2. 프록시가 SNI를 추출한다.
3. 정책이 `allow`이면 고정 업스트림에 연결한다.
4. 최초 ClientHello를 그대로 전달하고 이후 TCP 스트림을 중계한다.
5. JSON Lines 로그에 결정과 전송 바이트 수를 기록한다.

## 차단 흐름

정책이 `block`이면 업스트림 연결을 만들지 않고 클라이언트 연결을 종료한다. 로그에는 차단 사유를 기록한다.

## 신뢰 경계와 외부 연결 차단

정책 로더는 업스트림을 loopback 또는 Compose 내부 `test-server` 이름으로 제한한다. 이 프로젝트는 오픈 프록시가 아니며 외부 목적지로 임의 연결하지 않는다.
