# 로컬 실행 가이드

## 준비

macOS와 Linux 모두 Python 3.9 이상, OpenSSL, curl이 필요하다. Docker Compose는 선택 사항이다.

## Python 실행

처음 실행하거나 가상환경이 없는 경우:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
./scripts/generate-cert.sh
```

이미 가상환경이 있다면:

```bash
source .venv/bin/activate
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

로그 확인:

```bash
tail -n 20 logs/proxy.jsonl
```

pytest 실행:

```bash
python -m pytest
```

## 포트 확인

기본 포트는 테스트 서버 `8443`, 정책 프록시 `9443`이다.

```bash
lsof -nP -iTCP:8443 -sTCP:LISTEN
lsof -nP -iTCP:9443 -sTCP:LISTEN
```

포트가 이미 사용 중이면 기존 프로세스를 종료하거나 다른 포트를 지정한다.

```bash
python -m server.https_server --port 18443
python -m proxy.main --listen-port 19443
```

프록시가 다른 업스트림 포트로 연결해야 한다면 `configs/policy.yaml`의 `upstream.port`도 같은 값으로 변경해야 한다.

## 종료

`Ctrl-C`로 각 프로세스를 종료하거나 `./scripts/stop-local.sh`를 사용한다.

## 문제 해결

- `Address already in use`: 8443 또는 9443 포트를 쓰는 프로세스를 종료한다.
- 인증서 없음: `./scripts/generate-cert.sh`를 실행한다.
- 정책 오류: `configs/policy.yaml` 형식을 확인한다.
