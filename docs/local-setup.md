# 로컬 실행 가이드

## 준비

macOS와 Linux 모두 Python 3.11 이상, OpenSSL, curl이 필요하다. Docker Compose는 선택 사항이다.

## Python 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
./scripts/generate-cert.sh
```

터미널 1:

```bash
python -m server.https_server
```

터미널 2:

```bash
python -m proxy.main
```

터미널 3:

```bash
./scripts/test-allowed.sh
./scripts/test-blocked.sh
./scripts/test-unknown.sh
```

## 종료

`Ctrl-C`로 각 프로세스를 종료하거나 `./scripts/stop-local.sh`를 사용한다.

## 문제 해결

- `Address already in use`: 8443 또는 9443 포트를 쓰는 프로세스를 종료한다.
- 인증서 없음: `./scripts/generate-cert.sh`를 실행한다.
- 정책 오류: `configs/policy.yaml` 형식을 확인한다.
