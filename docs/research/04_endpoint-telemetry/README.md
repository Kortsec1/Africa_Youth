# 연구 주제
Endpoint Telemetry — Clipboard, Process, Foreground Window

## 1. 연구 목표
- 사후 포렌식 아티팩트로는 남지 않는 **"복사 → 붙여넣기", "어느 창을 보고 있었는가"** 를 기록하는 텔레메트리 수집 방법을 조사·구현한다.
- 수집 범위를 개인정보 보호와 균형 있게 설계한다 (내용이 아닌 메타데이터 중심).

## 2. 기술 조사

### 2.1 클립보드
| 방법 | 수집 정보 | 장점 | 한계 |
|---|---|---|---|
| **Sysmon EID 24 (ClipboardChange)** | 시각, 복사한 프로세스(Image), 세션, 내용 해시; 내용은 ArchiveDirectory 에 별도 보관 | 표준 도구, 중앙 수집 용이 | Sysmon 12.0(스키마 4.40)부터, `<CaptureClipboard/>` 필요. 텍스트만 대상. 아카이브 폴더가 빠르게 커질 수 있음 |
| Windows 클립보드 기록 (Win+V) | 최근 항목 | OS 기본 | 사용자가 켜야 함, 사후 분석 경로 제한적 |
| ActivitiesCache.db (Timeline) | 구버전 Win10 에서 클립보드 활동 기록 사례 | 사후 아티팩트 | Win11 에서 Timeline 기능 축소 → 신뢰 어려움 |
| **자체 에이전트** (`collector/telemetry_agent.py`) | 시퀀스 번호 변경 시각, 소유/포그라운드 프로세스, 창 제목, 텍스트 길이·SHA-256 | 창 제목(=원본 문서명)까지 연결 | 상시 실행 필요, 폴링 간격 내 누락 가능 |

- 핵심 API: `GetClipboardSequenceNumber`(변경 감지), `GetClipboardOwner`(소유 창), `AddClipboardFormatListener`(이벤트 방식, 개선 과제).
- **붙여넣기(Ctrl+V)는 어떤 방식으로도 일반적으로 기록되지 않는다.** → "복사 후 N초 내 AI 창 전환"을 정황으로 사용 (SAI-003).

### 2.2 포그라운드 창
| 방법 | 수집 정보 | 한계 |
|---|---|---|
| 자체 에이전트 `GetForegroundWindow` 폴링 | 창 전환 시각, 제목, 클래스, 프로세스 | 상시 실행 필요 |
| `SetWinEventHook(EVENT_SYSTEM_FOREGROUND)` | 전환 이벤트 즉시 수신 | 메시지 루프 필요 (개선 과제) |
| SRUM (Win11 App Timeline) | 앱별 포그라운드 사용량 | 시간 단위(1시간) 집계 — 분 단위 재구성 불가 |
| UserAssist / BAM | 앱 실행 횟수·마지막 실행 | 창 단위 정보 없음 |

- 창 클래스 **`#32770`** 은 표준 대화상자이다. 브라우저가 소유한 `#32770` 창(제목 '열기'/'Open')은 **파일 업로드 선택창**일 가능성이 높아 SAI-004 의 핵심 단서로 쓴다.
- 브라우저 창 제목에는 활성 탭 제목이 들어간다 (예: `재무 데이터 요약 - ChatGPT - Chrome`) → 어느 AI 서비스·어느 대화였는지 식별.

### 2.3 프로세스
| 방법 | 수집 정보 | 비고 |
|---|---|---|
| Sysmon EID 1 | 이미지, 명령줄, 부모, 해시, ProcessGuid | AI 생성물 실행(SAI-006), 로컬 LLM(SAI-007) |
| Security 4688 | 프로세스 생성 (명령줄은 GPO 설정 필요) | Sysmon 미설치 환경 대안 |
| Prefetch / Amcache | 사후 실행 흔적 | 02 와 공동 |

### 2.4 개인정보 보호 설계
- 클립보드 **내용 미저장**(길이·해시만). 해시는 사후에 원본 문서 일부와 대조하는 용도.
- 창 제목에는 문서명·메일 제목이 들어가므로 **수집 고지·동의**가 전제. 보존 기간 제한(예: 30일).
- Sysmon EID 24 아카이브(원문 저장)는 실험 환경에서만 사용, 운영 시 대상 프로세스 한정 또는 비활성화.

## 3. 프로젝트 적용 가능성
- 구현: `collector/telemetry_agent.py` (ctypes, 표준 라이브러리만) → `agent.jsonl` → 엔진 `parsers/agent.py`.
- Sysmon 설정: `collector/sysmon-shadowai.xml` (EID 1/3/11/15/22/24/26).
- 엔진은 Agent 와 Sysmon EID 24 가 같은 복사를 기록하면 하나로 병합하고 교차 확인으로 신뢰도를 올린다.
- 에이전트는 리눅스에서 작성되어 **Windows 실측 검증이 필요**하다 → results.md 실험 T-1~T-5.

## 4. 참고 자료
- O. Hartong, *Sysmon 12.0 — EventID 24* https://medium.com/falconforce/sysmon-12-0-eventid-24-31e0109c78e3
- TrustedSec, *Sysmon Community Guide — Clipboard Capture* https://github.com/trustedsec/SysmonCommunityGuide/blob/master/chapters/clipboard-capture.md
- Microsoft Learn, Clipboard 함수 (GetClipboardSequenceNumber, AddClipboardFormatListener) https://learn.microsoft.com/windows/win32/dataxchg/clipboard-functions
- Microsoft Learn, SetWinEventHook https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwineventhook
