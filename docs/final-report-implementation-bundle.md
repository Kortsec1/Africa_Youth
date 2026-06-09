# 최종 보고서용 구현 확장 묶음

이 문서는 현재 구현에 추가된 보완 기능을 최종 보고서에서 하나의 완성된 작업 단위로 설명하기 위한 정리다. 권장 명칭은 **프록시 개선 및 검증 모듈**이다.

## 묶음의 목적

초기 구현은 SNI 기반 allow/block 정책이 동작하는지 확인하는 데 초점을 둔다. 확장 구현은 여기서 한 단계 더 나아가 다음 질문에 답하기 위한 것이다.

- ClientHello가 한 번에 도착하지 않아도 SNI 정책을 적용할 수 있는가?
- 정책 판단 결과를 보고서에 사용할 수 있는 로그 필드로 남길 수 있는가?
- 허용, 차단, 파싱 실패, 업스트림 장애를 구분해 분석할 수 있는가?
- 반복 요청과 로그 요약을 통해 간단한 성능·결과 표를 만들 수 있는가?

## 구성 요소

| 구성 요소 | 파일 | 보고서에서의 의미 |
| --- | --- | --- |
| ClientHello 누적 읽기 | `proxy/main.py` | 단순 `read()` 의존을 줄이고 TLS record 길이에 따라 초기 핸드셰이크를 수신 |
| ClientHello 메타데이터 파싱 | `proxy/sni_parser.py` | SNI뿐 아니라 TLS record version, ClientHello version, handshake type 등을 추출 |
| 확장 로그 필드 | `proxy/main.py` | `connection_outcome`, `has_sni`, `parse_error_type`, TLS 버전 정보를 JSONL 로그로 기록 |
| 로그 요약 도구 | `scripts/summarize-logs.py` | 실험 로그를 Markdown 표로 변환해 보고서에 바로 활용 |
| 로컬 벤치마크 도구 | `scripts/benchmark-local.py` | 허용/차단/unknown 요청의 성공 수, 실패 수, 평균 처리 시간을 측정 |
| 보강 테스트 | `tests/test_sni_parser.py`, `tests/test_integration.py` | 메타데이터 추출, 분할 ClientHello 수신, 확장 로그 필드 검증 |

## 최종 보고서에 넣는 위치

권장 목차:

1. 연구 배경: HTTPS 확산과 메타데이터 기반 필터링
2. 관련 기술: DNS/IP/HTTP/TLS/SNI/QUIC/ECH 기반 검열 방식
3. 시스템 설계: 로컬 클라이언트, 정책 프록시, HTTPS 테스트 서버
4. **프록시 개선 및 검증 모듈**
5. 실험 결과: 허용, 차단, unknown, SNI 없음, 파싱 실패, 업스트림 장애, 동시 연결
6. 한계 및 확장: ECH, QUIC, ClientHello 단편화 심화, 실제 인터넷 환경 제외

## 구현 설명 예시

보고서 본문에는 다음과 같이 쓸 수 있다.

```text
초기 프록시는 클라이언트로부터 수신한 첫 번째 데이터 조각에서 SNI를 추출하였다.
그러나 TCP 스트림에서는 TLS ClientHello가 항상 하나의 read 호출에 완전히 포함된다고
보장할 수 없다. 따라서 개선 구현에서는 TLS record header 5바이트를 먼저 읽고,
record length 필드에 따라 나머지 body를 누적 수신하도록 변경하였다. 이를 통해
일반적인 ClientHello 분할 수신 상황에서도 정책 판단 전에 필요한 핸드셰이크 데이터를
확보할 수 있다.
```

```text
또한 프록시 로그에는 단순 allow/block 결과뿐 아니라 연결 결과를 구분하는
connection_outcome 필드를 추가하였다. 이 필드는 allowed_success, blocked,
parse_error, upstream_error로 구분되며, 실험 결과 분석에서 정책 판단과 실제 연결
성공 여부를 분리해 해석할 수 있게 한다.
```

## 실험 절차

기본 수동 실험:

```bash
source .venv/bin/activate
./scripts/generate-cert.sh
python -m server.https_server
python -m proxy.main
```

다른 터미널에서:

```bash
./scripts/test-allowed.sh
./scripts/test-blocked.sh
./scripts/test-unknown.sh
```

로그 요약:

```bash
./scripts/summarize-logs.py logs/proxy.jsonl
```

벤치마크:

```bash
./scripts/benchmark-local.py --requests 10 --concurrency 3
```

자동 테스트:

```bash
python -m pytest -q
```

## 보고서 표로 정리할 지표

| 지표 | 의미 |
| --- | --- |
| 총 연결 수 | 실험 중 프록시가 처리한 연결 수 |
| SNI별 요청 수 | `allowed.test`, `blocked.test`, `unknown.test`, SNI 없음 분포 |
| 정책 결정별 건수 | allow/block/error 분포 |
| 연결 결과별 건수 | allowed_success, blocked, parse_error, upstream_error 분포 |
| 평균 처리 시간 | 프록시가 연결 하나를 처리하는 데 걸린 평균 시간 |
| 업스트림 전송 바이트 | 허용된 연결에서 실제 중계가 발생했는지 확인 |
| 파싱 오류 유형 | 비정상 ClientHello, 불완전 TLS record 등 오류 분류 |

## 기대 효과

이 묶음은 프로젝트를 단순 시연에서 분석 가능한 실험 환경으로 확장한다. 특히 최종 보고서에서 다음 강점을 보여줄 수 있다.

- 구현이 TLS record 구조를 고려한다.
- 정책 판단과 연결 성공 여부를 분리해 기록한다.
- 실험 결과를 JSONL 로그와 Markdown 요약표로 재현 가능하게 남긴다.
- 보강 테스트를 통해 구현 변경의 동작을 검증한다.
- 실제 우회 도구 구현 없이도 현대 검열 방식과 SNI 기반 정책의 한계를 설명할 수 있다.
