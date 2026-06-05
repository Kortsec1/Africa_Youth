# 테스트 시나리오

## 사전 조건

인증서 생성, 테스트 서버 실행, 정책 프록시 실행이 완료되어야 한다.

## 정상 허용 테스트

명령:

```bash
curl -vk --resolve allowed.test:9443:127.0.0.1 https://allowed.test:9443/
```

예상 결과: SNI `allowed.test`, 정책 `allow`, 테스트 서버 JSON 응답.

## 정상 차단 테스트

명령:

```bash
curl -vk --resolve blocked.test:9443:127.0.0.1 https://blocked.test:9443/
```

예상 결과: SNI `blocked.test`, 정책 `block`, 업스트림 연결 없음.

## 추가 테스트

- 알 수 없는 SNI: `unknown.test`는 기본 정책 `block`.
- SNI 없는 연결: `openssl s_client -connect 127.0.0.1:9443`.
- 비정상 ClientHello: 임의 바이트 전송 후 기본 정책 적용.
- 테스트 서버 장애: 서버 중지 후 `allowed.test` 요청 시 오류 로그 기록.
- 순차 및 동시 연결: pytest 통합 테스트로 확인.

## 결과 기록 양식

```text
날짜:
테스트:
명령:
예상 결과:
실제 결과:
로그 파일:
비고:
```
