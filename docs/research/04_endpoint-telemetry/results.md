# 실험 결과

> 상태: **실험 설계 완료 / 실측 전**.

## 1. 실험 환경
- Windows 11 VM, Python 3.11+, Sysmon(collector/sysmon-shadowai.xml), `collector/telemetry_agent.py`
- Office(Excel/Word), 메모장, Chrome, ChatGPT 웹

## 2. 실험 목적
에이전트·Sysmon 이 복사와 창 전환을 **놓치지 않고, 올바른 프로세스로** 기록하는지와 성능 부담을 측정한다.

## 3. 실험 과정
| ID | 동작 | 측정 |
|---|---|---|
| T-1 | Excel 셀 복사 → Chrome(ChatGPT) 전환 → 붙여넣기 (20회) | 에이전트/EID24 탐지율, 기록된 프로세스 정확도, 복사→전환 간격 분포 |
| T-2 | 메모장·Word·브라우저 내부 복사 | 소유 창 없는 앱의 `owner_known` 비율 |
| T-3 | 빠른 창 전환(Alt+Tab 0.3초 간격) | 폴링 0.5초에서 누락률 → 간격 조정 근거 |
| T-4 | Chrome 파일 첨부 버튼 클릭 | 대화상자 클래스 `#32770`·제목·소유 프로세스 확인 |
| T-5 | 에이전트 8시간 실행 | CPU·메모리·로그 크기 |

## 4. 실험 결과
| ID | 결과 | 비고 |
|---|---|---|
| T-1 | | SAI-003 시간창(120초) 보정 |
| T-2 | | |
| T-3 | | |
| T-4 | | SAI-004 전제 |
| T-5 | | |

## 5. 확인된 한계

## 6. 추가 연구 사항
- 폴링 → 이벤트 방식(SetWinEventHook, AddClipboardFormatListener) 전환
- 서비스(백그라운드) 형태로 배포, 변조 방지
