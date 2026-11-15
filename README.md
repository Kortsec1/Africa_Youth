# Shadow AI Forensics

## 프로젝트 개요

본 프로젝트는 Windows 환경에서 발생하는 Shadow AI 사용 행위를 탐지하고, 다양한 디지털 포렌식 아티팩트를 활용하여 사용자 행위를 재구성하는 시스템 개발을 목표로 합니다.

기존의 AI 서비스 접속 여부 중심 탐지에서 확장하여, 파일 접근·수정, Clipboard, 브라우저 및 프로세스 활동을 시간순으로 연결하고 데이터 이동 정황을 분석합니다.

## 주요 기능

### 1. Shadow AI 사용 탐지
- ChatGPT 등 생성형 AI 서비스 접근 탐지
- Clipboard 및 사용자 행위 정보 수집
- AI 사용 관련 이벤트 식별

### 2. Windows 포렌식 아티팩트 분석
- `$MFT`, `$UsnJrnl`
- LNK, JumpList
- Browser History
- Process 및 사용자 활동 정보

### 3. 사용자 행위 재구성
- 서로 다른 아티팩트의 시간 정보 통합
- AI 사용 전후 파일 활동 분석
- 이벤트 간 상관관계 분석
- 증거 기반 Timeline 생성

### 4. 분석 결과 시각화
- Shadow AI 사용 이벤트 조회
- 사용자 행위 Timeline
- 관련 포렌식 증거 확인

## 시스템 구성

```
Windows Endpoint                      분석 PC (Python 3.11+, 외부 의존성 없음)
┌──────────────────────────────┐      ┌─────────────────────────────────────────────────────┐
│ collector/                   │      │ src/shadow_ai_forensics/                            │
│  collect_artifacts.ps1 ──────┼─────▶│  parsers/   형식 자동판별 → 정규화 Event             │
│   · 브라우저 History          │ 수집 │  catalog    AI 서비스·도메인 역할·민감 키워드 태깅    │
│   · LECmd / JLECmd / MFTECmd  │ 폴더 │  correlate/ AI 세션 구성 → 탐지 규칙 9종            │
│   · Sysmon·DNS 로그(JSONL)    │      │  report/    HTML 타임라인 · JSON · CSV · Markdown    │
│  04 RealtimeCollector (C#)    │
│  04 Chrome 붙여넣기 관측 확장  │
│  telemetry_agent.py (보조)    │      └─────────────────────────────────────────────────────┘
│  sysmon-shadowai.xml          │
└──────────────────────────────┘
```

| 입력 (자동 판별) | 생성 도구 | 정규화 행위 |
|---|---|---|
| `$MFT` CSV, `$J` CSV | MFTECmd | 파일 생성·수정·삭제·이름변경, Zone.Identifier |
| LNK CSV / JumpList CSV | LECmd / JLECmd | 파일 열람 |
| `History` / `places.sqlite` | Chrome·Edge·Whale / Firefox | 방문, 다운로드 |
| Sysmon·DNS-Client (EvtxECmd CSV 또는 JSONL) | EvtxECmd / collect_artifacts.ps1 | 프로세스, DNS, 연결, 클립보드, 파일 생성·삭제 |
| RealtimeCollector JSONL (schema v2) | [04 수집기](docs/research/04_endpoint-telemetry/poc/windows-collector/README.md) | 창 전환, 클립보드 변경, 프로세스 시작 |
| `chrome-paste-*.jsonl` | [04 Chrome 붙여넣기 관측 확장](docs/research/04_endpoint-telemetry/tools/chrome-paste-observer/README.md) | AI 페이지 붙여넣기(paste_event) |
| `agent.jsonl` | collector/telemetry_agent.py (보조: 창 클래스로 파일 선택창 식별) | 창 포커스, 파일 대화상자, 클립보드 |

## 빠른 실행

```bash
pip install -e .[dev]                                   # 또는 PYTHONPATH=src
python tools/generate_synthetic.py                      # 가상 시나리오 생성 (samples/synthetic/scenario01)
python -m shadow_ai_forensics analyze samples/synthetic/scenario01 -o out
# → out/report.html (탐지 결과 · 타임라인 · 이벤트 표), findings.json, timeline.csv, summary.md
python -m shadow_ai_forensics rules                     # 탐지 규칙 목록
python -m pytest                                        # 회귀 테스트
```

실제 PC 분석: 관리자 PowerShell 에서 `collector\collect_artifacts.ps1 -Out D:\case01` → `analyze D:\case01`.

## 탐지 규칙

| ID | 내용 | ID | 내용 |
|---|---|---|---|
| SAI-001 | AI 사용 세션 식별 (기준점) | SAI-006 | AI 생성물 실행 |
| SAI-002 | 사용 전후 문서 열람 | SAI-007 | 비인가 AI 앱 / 로컬 LLM |
| SAI-003 | 복사 → AI 창 전환 / 붙여넣기 관측 | SAI-008 | 사용 전 압축(Staging) |
| SAI-004 | 브라우저 파일 선택 → 업로드 정황 | SAI-009 | 사용 후 흔적 삭제 |
| SAI-005 | AI 생성물 다운로드 | | |

모든 탐지는 **확인된 사실(원본 파일:행 참조)** / **추론** / **다른 가능성(오탐 요인)** / **확정에 필요한 추가 증거** 로 분리해 출력합니다. 설계 근거는 [docs/research/01_detection/results.md](docs/research/01_detection/results.md).

## 현재 진행 단계

**1단계: 기술 조사 및 구현 가능성 검증** — 조사 완료, PoC 구현 완료, **실측 실험 대기**

- [x] 분야별 기술 조사 (01~05 `README.md`)
- [x] 정규화 스키마 · 파서 7종 · 상관분석 엔진 · HTML 리포트 PoC
- [x] 실제 도구 출력 형식의 가상 시나리오로 엔진 검증 + 04 실측 증거 파싱 검증 (회귀 테스트 18개)
- [x] 04 Endpoint Telemetry 실측 (수집기·Chrome 확장, [결과](docs/research/04_endpoint-telemetry/results.md)) → 엔진 연동, SAI-003 신뢰도 보정
- [x] 수집 스크립트 · 텔레메트리 에이전트 · Sysmon 설정 초안
- [ ] 실측 실험 (02 W-1~8, 03 A-1~7, 05 N-1~6) — 각 `results.md` 에 절차·기록 양식 준비됨
- [ ] 04 미완료 항목(창·탭 횟수 대조, 파일·전송 통합 실험) — 04 results 참고
- [ ] 실측 결과로 규칙 시간창·도메인 카탈로그 보정, ComDlg32(RECmd)·SRUM 파서 추가

> ⚠ `samples/synthetic/` 은 **가상 데이터**입니다. 실험 결과로 인용하지 마세요.
> `collector/` 의 PowerShell 수집 스크립트·Python 에이전트는 아직 실제 Windows 에서 검증 전입니다. 실측 검증된 수집기는 04 폴더의 RealtimeCollector 입니다.

## 디렉터리

```
src/shadow_ai_forensics/   분석 엔진 (parsers, correlate, report, data/ai_services.toml)
collector/                 Windows 수집 스크립트·에이전트·Sysmon 설정
tools/generate_synthetic.py  가상 시나리오 생성기
samples/synthetic/         가상 시나리오 데이터
tests/                     회귀 테스트
docs/research/0x_*/        분야별 조사(README) · 실험(results)
```

## 연구 분야

| 분야 | 주요 내용 |
|---|---|
| Windows Forensics | 파일 시스템 및 사용자 활동 아티팩트 |
| Browser / AI Forensics | AI 서비스 접근 및 사용 흔적 |
| Endpoint Telemetry | Clipboard, Process, Foreground Window |
| Shadow AI Detection | 기존 탐지 기술 및 사용 시나리오 |
| Correlation | Timeline 및 이벤트 상관분석 |

## 프로젝트 목표

단순히 AI 서비스에 접속했는지를 탐지하는 것이 아니라,

**AI 서비스 사용 전후에 사용자가 어떤 행동을 했는지 포렌식 증거를 기반으로 설명할 수 있는 시스템을 구현하는 것**이 최종 목표입니다.

## Endpoint Telemetry 조사·PoC 결과

[Windows 실시간 사용자 행동 수집](docs/research/04_endpoint-telemetry/README.md)에 조사, 학생용 보고서, PoC 코드와 공유용 실험 증거를 정리했습니다. 기본 기능 검증 단계이며 전체 유출 탐지 구현 완료를 의미하지 않습니다.
