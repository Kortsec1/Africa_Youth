# PoC 실행 방법

## 환경

- Python 3.10 이상을 대상으로 작성
- 실제 검증: Python 3.14.6
- 외부 패키지 설치 불필요

저장소 루트에서 실행한다.

```sh
cd docs/research/01_detection/poc
python3 analyze.py sample_events.json > output.json
python3 test_analyze.py
```

Windows에서 python3 명령이 없으면 python 또는 py를 사용한다.

시간 범위 비교:

```sh
python3 analyze.py sample_events.json 30 > output_30.json
python3 analyze.py sample_events.json 300 > output_300.json
```

## 파일

- analyze.py: 정규화된 가상 이벤트를 정렬하고 규칙 R01~R05 적용
- test_analyze.py: 13개 시나리오와 추가 경계 조건 검증
- sample_events.json: 기존 예시와 같은 가상 이벤트 4건
- output.json: 기본 시간 범위 60초로 실제 실행한 결과

## 정책

analyze.py 상단의 POLICY는 연구용 정책이다.
AI-DEMO는 unapproved, AI-OK는 approved이며 나머지는 unknown이다.
2026-11-01 00:00:00 UTC 이전 이벤트에는 이 정책을 적용하지 않는다.
정책 버전은 demo-v1이다. 실제 조직 정책이 아니다.

## 출력

- timeline: 발생 시각순 이벤트 ID
- events: 근거 추적용 원본 이벤트
- alerts: 규칙별 판정, 근거 ID, 관찰 속성 및 추론
- policy_version, parameters, limitation: 실행 전체에 적용되는 메타데이터

기본 샘플 결과: R01 3건, R02 1건, R05 1건.
같은 이벤트가 여러 규칙에 사용되므로 사용자 행위 5건을 뜻하지 않는다.

## 구현 범위

코드를 단순하게 유지하기 위해 다음은 후속 작업으로 남긴다.

- 전체 필드·자료형·이벤트 유형의 엄격한 검증
- 실제 수집원별 변환기와 사용자 식별자 매핑
- 별도 정책 파일과 다중 정책 버전 처리
- 대용량 데이터 성능 개선

입력은 poc/README.md에 정의한 구조를 따른다고 가정한다.
시간대, 이벤트 ID 충돌, 가상 데이터 여부 및 장치 ID를 일부 검사한다.
시각 비교는 시간대가 반영된 datetime으로 수행하고 원본 시각 표기는 보존한다.
프로세스 식별자는 보존하지만 현재 5개 규칙의 연결 키로 사용하지 않는다.
신뢰도는 rules.md의 정성적 판단 수준이며 확률 점수가 아니다.
