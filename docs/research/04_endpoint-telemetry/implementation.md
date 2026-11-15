# PoC 구현 구조와 변경사항

## 구성과 흐름

Windows 알림 → Collector → EventLogWriter → JSONL.

| 구성 | 역할 |
|---|---|
| Program | 실행 옵션·시간제한·종료 |
| Collector | Clipboard/WinEvent/WMI 등록과 처리 |
| EventLogWriter | 4096개 대기열과 별도 파일쓰기, 내부손실/종료통계 |
| Native | Windows API 선언 |

[실제 소스](poc/windows-collector/Program.cs)를 기준으로 한다. 초기 목록은 process_snapshot, 새 실행은 process_start로 구분한다. 데이터 원문은 읽지 않으며 제목 수집은 선택사항이다.

## 변경 이유

1. Clipboard 알림은 받았지만 OpenClipboard 실패 후 형식을 조회하지 못한 사례를 확인했다. 최대5회/25ms 재시도, sequence 전후확인, 오류목록/시도횟수/조회상태 기록을 추가했다. 실패 시 null로 표시한다.
2. 테스트 세션1의 WMI StopTrace가 SessionID0으로 전달돼 기존 필터에서 빠졌다. stop은 무필터 수신 후 현재세션에서 확보한 PID/이름과 연결한다. 원천값을 보존하고 캐시연결은 후보로 표시한다. PID재사용은 미해결이다.
3. schema_version2로 기록한다. 관측시각·원천시각은 구분한다.

## 검증 범위

수정후 Clipboard6건 형식조회성공, WMI/ETW 동일 테스트 PID 시작/종료 확인. 고빈도·부하·장시간·강제종료경로 전체는 미검증. ETW는 별도 실험이며 Security/파일I/O/전송수집은 본체에 통합하지 않았다.

[요구사항 대조](requirements.md)와 [실험 결과](results.md)를 함께 읽는다.
