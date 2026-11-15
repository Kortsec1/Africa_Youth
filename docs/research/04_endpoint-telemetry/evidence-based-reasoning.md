# 자료 기반 판정과 한계 (실행 없이 정리)

담당: 동훈 / 정리 기준일: 2026-11-15

## 0. 이 문서의 범위

- 새 실험을 하지 않고, **이미 있는 자료**(Microsoft 공식 문서, MDN, 학술 논문, 04의 기존 실험 결과)와 **수집기 소스 코드**만으로 판정할 수 있는 항목을 정리했다.
- 각 항목은 **주장 → 근거 → 논리 → 한계** 순서로 쓴다. 근거가 없는 연결 고리는 "미검증"으로 표시하고 결론에 쓰지 않는다.
- 뒷받침할 자료가 없는 항목은 논리를 구성하지 않고 9장에 따로 적었다.
- 코드 근거는 `poc/windows-collector/Program.cs`, 실험 근거는 [results.md](results.md)와 [evidence/README.md](evidence/README.md)를 가리킨다.

## 1. 클립보드 변경 횟수는 붙여넣기 횟수가 아니다 (C3 보강)

**주장:** 수집기가 받는 클립보드 알림은 붙여넣기 때 생기지 않는다.

**근거**
- Microsoft는 WM_CLIPBOARDUPDATE를 "클립보드 내용이 바뀌었을 때" 보내는 메시지로 정의한다. AddClipboardFormatListener로 등록한 창은 내용이 바뀔 때마다 이 메시지를 받는다. [MS-1]
- Microsoft의 클립보드 명령 설명에서 Paste는 "선택 영역을 클립보드 내용으로 바꾸며, 클립보드 내용은 바뀌지 않는다"고 되어 있다. [MS-2]
- 수집기는 WM_CLIPBOARDUPDATE(0x031D)를 받을 때만 `clipboard_update`를 기록한다 (`WndProc`).
- 04 실험 2: 복사 1회 후 붙여넣기 3회에서 알림은 1건이었다.

**논리:** 붙여넣기는 클립보드 내용을 바꾸지 않는다 → 내용 변경 알림이 생기지 않는다 → 수집기 기록에 붙여넣기가 나타나지 않는다. 실험 2의 결과(알림 1건)는 이 설계상 동작과 일치한다.

**한계**
- 이 설명은 표준 클립보드 동작 기준이다. 클립보드 관리자나 지연 렌더링을 쓰는 앱이 붙여넣기 도중 클립보드를 다시 쓰는 경우는 확인하지 않았다.
- 실험 2는 1회 수행이고 조작별 독립 시각 기록이 없다 (results.md 3.4절).

## 2. 복사한 앱(출처)은 "후보"로만 기록된다

**주장:** `owner_at_observation`이 비어 있거나 실제 복사 앱과 다를 수 있으므로 복사 출처는 확정할 수 없다.

**근거**
- GetClipboardOwner는 클립보드 소유자가 없으면 NULL을 반환한다. Microsoft는 "소유자가 없어도 클립보드에 데이터가 있을 수 있다"고 하고, 소유자를 "일반적으로" 마지막으로 데이터를 넣은 창으로 설명한다. [MS-3]
- 수집기는 소유 창과 함께 당시 전면 창(`foreground_at_observation`)도 기록하고, 결과에 "not ... guaranteed copy source"를 명시한다.

**논리:** API 자체가 "일반적으로"라는 조건을 달고 NULL을 허용한다 → 소유 창은 복사 앱의 강한 후보일 뿐 확정 근거가 아니다 → 전면 창 정보와 함께 보조적으로 판단해야 한다.

**한계:** 소유 창이 NULL로 나오는 앱의 비율은 측정하지 않았다.

## 3. 붙여넣기·전송을 함께 비교하는 통합 실험(X1/X2)은 현재 구성으로 완료할 수 없다

**주장:** X1/X2를 원래 기준(붙여넣고 전송 vs 이동만)으로 완료하려면 새 기능이 필요하며, 이는 보고서 3.3절에서 정한 범위 밖이다.

**근거**
- 1장: 붙여넣기는 클립보드 알림을 만들지 않는다. 수집기 본체에는 클립보드·창·프로세스 외의 센서가 없다.
- Chrome 확장은 `https://chatgpt.com/*` 페이지에서만 동작한다(`manifest.json`). 웹 paste 이벤트는 MDN이 정의한 브라우저 이벤트이며 [MDN-1], 확장 README는 이 이벤트가 삽입·전송 성공을 증명하지 않는다고 명시한다.
- 04 실험 3: 설치형 ChatGPT 앱에서 "붙여넣지 않음"과 "붙여넣고 미전송"이 수집기 기록상 구분되지 않았다.
- 전송 사례는 별도 수동 화면뿐이며 원시 HAR이나 같은 요청 ID 자료가 없다 (evidence/README.md 3절).

**논리:** 붙여넣기는 웹에서만, 전송은 어디에서도 자동 기록되지 않는다 → "붙여넣고 전송"과 "이동만"을 같은 실행에서 자동 대조할 수단이 없다 → 실행을 반복해도 원래 기준을 충족할 수 없다. 따라서 X1/X2는 "미수행"보다 **"현 구성으로는 수행 불가(범위 외)"**가 정확한 판정이다.

**한계**
- 설치형 앱, 다른 브라우저, 다른 AI 서비스의 붙여넣기는 관측 범위 밖이다.
- paste 이벤트는 페이지가 기본 동작을 취소할 수 있어 실제 삽입을 보장하지 않는다.

## 4. 창 전환 기록의 의미 (W1)

**주장:** `foreground_change` 1건은 "앱 전환 1회"가 아니라 "전면 창 변경 1회"다. 기록 순서는 신뢰할 수 있지만, 기록 시각(`observed_at_utc`)은 실제 발생보다 늦을 수 있다.

**근거**
- EVENT_SYSTEM_FOREGROUND는 "전면 창이 바뀌었을 때" 발생하며, 같은 스레드의 다른 창으로 바뀌어도 발생한다. [MS-4]
- WINEVENT_OUTOFCONTEXT 방식은 시스템이 이벤트를 큐에 넣어 비동기로 전달하지만 순서는 보장된다. 이 방식은 호출 스레드에 메시지 루프가 있어야 하며, 이벤트는 SetWinEventHook을 호출한 스레드로 전달된다. [MS-5]
- 콜백의 `dwmsEventTime`은 이벤트가 생성된 시각(ms)이다. [MS-6] 수집기는 이를 `source_event_tick_ms`로 기록한다.
- 수집기는 클립보드 조회 재시도를 같은 GUI 스레드에서 최대 100ms(25ms × 4회 대기) 수행한다 (`ClipboardEvent`).

**논리**
- 같은 앱 안에서 창이 바뀌어도 이벤트가 생기므로, 기록 건수와 사용자가 의도한 앱 전환 횟수는 같다고 가정할 수 없다.
- 이벤트는 큐에 쌓였다가 메시지 루프에서 처리된다. 같은 스레드가 클립보드 재시도로 멈춘 동안 들어온 창 이벤트는 늦게 처리되어, `observed_at_utc`가 실제보다 늦게 찍힐 수 있다.
- 순서는 보장되고 생성 시각(`source_event_tick_ms`)이 함께 남으므로, 정밀 분석에서는 생성 시각을 기준으로 삼아야 한다.

**한계**
- Alt+Tab 전환 화면처럼 중간 창이 전면에 오는지, 그래서 1회 전환이 여러 건으로 기록되는지는 **미검증**이다. 5왕복 정량 대조(W1)가 여전히 필요하다.
- 수집기 자신의 프로세스에서 생긴 이벤트는 SKIPOWNPROCESS로 제외된다.

## 5. 탭 전환 기록의 의미 (W2)

**주장:** 수집기는 탭 전환을 직접 기록하지 않는다. 창 제목 변경을 기록하므로 "탭 전환 횟수"를 정확히 셀 수 없다.

**근거**
- EVENT_OBJECT_NAMECHANGE는 객체의 Name 속성이 바뀌었을 때 발생하며, 시스템은 window 객체에 대해 이 이벤트를 보낸다. [MS-4]
- 수집기는 `--window-titles`를 켰을 때만 이 이벤트를 구독하고, 전면 창 자체(`idObject=0`, `idChild=0`, `hwnd`가 전면 창)의 변경만 기록한다 (`OnWinEvent`).

**논리**
- 탭을 바꾸면 브라우저 창 제목이 바뀔 수 있고, 그 변경이 기록된다. 하지만 같은 이벤트는 페이지 스스로 제목을 바꿀 때도 생긴다 → 두 경우를 구분할 정보가 기록에 없다.
- 제목이 같은 탭끼리 전환하면 Name이 바뀌지 않으므로 이벤트가 생기지 않는다.
- 따라서 W2의 결론은 실행 없이도 "제목 이벤트로는 탭 전환 횟수를 정확히 셀 수 없다"로 정리할 수 있다.

**한계**
- Chrome·Edge가 탭 전환 때 최상위 창에 이 이벤트를 실제로 보내는지는 **미검증**이다. "제목 변경이 기록된다"는 부분은 실행으로 확인해야 한다.
- 제목은 URL이 아니며, 창 제목 수집은 개인정보 노출 위험이 있어 선택 옵션이다.

## 6. 수집 전에 실행된 프로세스의 구분 (P3)

**주장:** 수집 시작 전 프로세스(`process_snapshot`)와 이후 시작된 프로세스(`process_start`)는 기록 타입으로 구분된다. 다만 경계 구간에서 중복이 생길 수 있다.

**근거**
- Microsoft의 커널 ETW 프로세스 이벤트도 "세션 시작 시점에 실행 중인 프로세스 목록"(이벤트 타입 3)과 "새로 시작된 프로세스"(타입 1)를 별도 이벤트로 구분한다. [MS-7] 수집기의 스냅샷/시작 구분은 이와 같은 방식이다.
- `Process.StartTime`은 Windows 함수 호출 오류 시 Win32Exception, 프로세스 핸들이 없으면 InvalidOperationException을 던질 수 있다. [MS-8] 수집기는 이 경우 `snapshot_unavailable`로 남긴다.
- 수집기는 WMI 시작 감시(`StartWatcher`)를 **먼저** 켜고 그 다음에 스냅샷을 찍는다 (`Start`).
- 기존 10회 실행에서 수집 전 생성된 브라우저 147건이 같은 PID의 새 시작 이벤트와 구분되었다 (evidence/README.md 3절, 후향 관측).

**논리:** 구분 방식은 Microsoft 커널 추적과 같은 원리이고, 기존 기록에서도 구분이 확인됐다. 다만 감시를 먼저 켜므로 그 짧은 사이에 시작된 프로세스는 `process_start`와 `process_snapshot`에 모두 나올 수 있다. 분석 시 같은 PID·이름·시작 시각의 중복을 하나로 묶어야 한다.

**한계**
- 147건은 반복 관측이며 독립 실험이 아니다. 통제된 P3 실험은 여전히 미수행이다.
- 중복 구간이 실제로 발생하는 빈도는 측정하지 않았다. PID 재사용 문제도 미해결이다.

## 7. 파일 작업 기록(F1)은 수집기의 대상이 아니다

**주장:** 수집기로 파일 생성·이름변경·삭제를 검증하는 것은 구조상 불가능하다. F1은 "수집기 검증 대상 아님"으로 정리할 수 있다.

**근거**
- 수집기 본체에는 파일 센서가 없다 (클립보드·WinEvent·WMI 프로세스만 등록).
- Windows 기본 파일 감사 이벤트 4663은 SACL이 설정된 객체에서, 그 SACL과 맞는 접근이 있을 때만 생성된다. File System 감사 정책만으로는 이벤트가 생기지 않는다. [MS-9]
- 04 추가 검증에서 당시 PC는 파일시스템 감사가 꺼져 있었다 (evidence/README.md 3절).

**논리:** 수집기에는 파일 센서가 없고, OS 감사 로그는 정책과 SACL을 별도로 설정해야 생긴다 → 현재 구성에서는 어떤 경로로도 파일 이벤트가 수집되지 않는다 → F1의 수집 검증은 범위 밖이다. 메모장 열기·편집·저장 확인은 "사용자 조작 확인"이지 "수집 확인"이 아니다.

**한계:** Sysmon이나 ETW 파일 이벤트 같은 대안 수단은 이번 범위에서 검증하지 않았다. 파일 활동 재구성은 02(Windows 포렌식) 분야와 연계해야 한다.

## 8. 연구 위치 (선행 연구와의 관계)

**주장:** 04는 선행 연구가 다루지 않은 "실시간 행위 흐름"을 수집한다는 점에서 차별점이 있다.

**근거:** [관련 연구 조사](related-work.md) 1~2장. 확인한 생성형 AI 포렌식 논문 4편은 앱·브라우저·디스크에 남은 흔적을 다룬다. 내부자 위협 연구에서 널리 쓰는 CERT 데이터셋에는 클립보드·활성 창 기록이 없다.

**논리:** 기존 연구는 사후 흔적, 04는 사용 과정의 기록 → 두 접근은 보완 관계이며, 04의 기록은 공개 데이터셋에 없는 유형이다.

**한계:** 논문 원문을 읽지 않고 검색 요약만으로 정리했다. 검색 범위가 좁아 "선행 연구 없음"으로 단정하지 않는다.

## 9. 자료가 없어 논리를 구성하지 않은 항목

아래 항목은 뒷받침할 공식 문서나 논문을 확인하지 못했다. 코드에서 관찰한 사실만 적고 결론은 내리지 않는다.

| 항목 | 코드에서 확인한 사실 | 남은 확인 |
|---|---|---|
| 장시간 실행·누락률 | 대기열 4,096건, 가득 차면 버린 건수를 셈. OS·WMI 단계 손실은 측정하지 않는다고 코드에 명시 | 실행 측정 필요 |
| CPU·메모리 부담 | 측정 코드 없음 | 실행 측정 필요 |
| 감사 이벤트 실제 생성 | 7장의 조건 외 확인 없음 | 정책 설정 후 실행 필요 |
| Alt+Tab 중간 창 | 4장 한계 참조 | 실행 필요 |

## 10. 판정 요약

| 항목 | 기존 판정 (results.md 3.4) | 이 문서의 판정 | 근거 수준 |
|---|---|---|---|
| C3 | 수행, 독립 시각 없음 | 결과가 API 설계와 일치함을 확인 | 공식 문서 + 실험 1회 |
| X1/X2 | 부분 충족 | **현 구성으로 수행 불가(범위 외)** | 공식 문서 + 코드 + 실험 |
| W1 | 정량 대조 미수행 | 기록의 의미 확정, 정량 대조는 여전히 필요 | 공식 문서 + 코드 |
| W2 | 미수행 | **"탭 전환 횟수를 정확히 셀 수 없음" 확정**, 이벤트 발생 여부는 미검증 | 공식 문서 + 코드 |
| P3 | 통제 실험 미수행 | 구분 원리 확정, 중복 가능 구간 확인, 통제 실험은 필요 | 공식 문서 + 코드 + 후향 관측 |
| F1 | GUI 이름변경·삭제 미검증 | **수집기 검증 대상 아님(범위 외)** | 공식 문서 + 코드 + 감사 상태 확인 |

이 판정은 기존 실험 결과를 대체하지 않는다. "범위 외"로 바꾼 항목도 실험이 완료되었다는 뜻이 아니라, 현재 구성으로는 완료할 수 없다는 뜻이다.

## 참고 자료

- [MS-1] Microsoft, WM_CLIPBOARDUPDATE / AddClipboardFormatListener: https://learn.microsoft.com/windows/win32/dataxchg/wm-clipboardupdate , https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-addclipboardformatlistener
- [MS-2] Microsoft, About the Clipboard (Clipboard Commands): https://learn.microsoft.com/windows/win32/dataxchg/about-the-clipboard
- [MS-3] Microsoft, GetClipboardOwner: https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-getclipboardowner
- [MS-4] Microsoft, Event Constants (EVENT_SYSTEM_FOREGROUND, EVENT_OBJECT_NAMECHANGE): https://learn.microsoft.com/windows/win32/winauto/event-constants
- [MS-5] Microsoft, SetWinEventHook: https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwineventhook
- [MS-6] Microsoft, WINEVENTPROC callback: https://learn.microsoft.com/windows/win32/api/winuser/nc-winuser-wineventproc
- [MS-7] Microsoft, ETW Process class (event types): https://learn.microsoft.com/windows/win32/etw/process
- [MS-8] Microsoft, Process.StartTime: https://learn.microsoft.com/dotnet/api/system.diagnostics.process.starttime
- [MS-9] Microsoft, Advanced Audit Policy Configuration (Audit File System, 4663): https://learn.microsoft.com/windows-server/identity/ad-ds/plan/security-best-practices/advanced-audit-policy-configuration
- [MDN-1] MDN, Element: paste event: https://developer.mozilla.org/en-US/docs/Web/API/Element/paste_event
