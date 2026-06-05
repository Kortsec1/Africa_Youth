# Git 운영 규칙

- Git 저장소가 아니면 초기화한다.
- 기존 저장소에서는 상태와 브랜치를 먼저 확인한다.
- 기능 단위 영문 브랜치를 사용한다.
- 커밋 메시지는 한글로 작성한다.
- 하나의 커밋에는 하나의 목적만 담는다.
- 강제 푸시를 사용하지 않는다.
- 원격 저장소가 없으면 임의로 만들거나 푸시하지 않는다.

예시 브랜치:

```text
feature/project-skeleton
feature/https-test-server
feature/sni-parser
feature/policy-loader
feature/policy-proxy
feature/docker-compose
test/proxy-integration
```

예시 커밋:

```text
초기 프로젝트 구조와 기본 문서 추가
로컬 테스트 HTTPS 서버 구현
ClientHello SNI 파서와 단위 테스트 추가
SNI 기반 정책 프록시 기본 기능 구현
```
