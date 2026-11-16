# 분석 수행 로그

일자: 2026-11-16. 아래 항목은 실제 작업 기록이며 AI 서비스 실험 로그가 아니다.

| 순서 | 작업 | 관찰 결과 | 영향 |
|---|---|---|---|
| 1 | HTTPS git clone | `getaddrinfo() thread failed to start`, 종료 코드 1 | 전체 소스/기존 git 메타데이터 확보 실패 |
| 2 | GitHub REST API 읽기 | 호스트 이름 해석 실패 | API를 통한 issue/파일 읽기 불가 |
| 3 | 연결된 Chrome에서 이슈 #5 열기 | 연구 목표, 작업 경로, 완료 기준 확인. 모든 체크 항목 미완료 | 사용자 제공 요구와 일치 |
| 4 | 원격 main 루트와 연구 폴더 열기 | Shadow AI Forensics, 5개 연구 분야와 endpoint PoC 연계 확인 | Timeline/증거 기반 연구 방향 반영 |
| 5 | main 상태 확인 | 루트 최신 표시 `da48b5912d0011567ec2b7ed024b63885025bfe5`; 연구 03 문서 변경 이력에 revert `56450ed...` 표시 | 과거 구현이 현재 존재한다고 가정하지 않음 |
| 6 | GitHub Code → Download ZIP | codeload 도메인 `ERR_BLOCKED_BY_CLIENT` | 브라우저 다운로드도 실패, 차단 우회하지 않음 |
| 7 | 03 README/results 확인 | README: 연구 주제/목표/기술 조사/적용/참고자료 목차. results: 실험 환경/목적/과정/결과/한계/추가 연구 목차, 153 bytes 표시 | 기존 실험 데이터는 확인되지 않음. samples 내용은 열람하지 않음 |
| 8 | 공식 문서 확인 | Chromium 프로필 경로, SQLite WAL, Chrome 시크릿 문서 열람 | 문헌 근거와 서비스별 가설 분리 |
| 9 | 실제 AI 전송/업로드 | 실행하지 않음 | 서비스 잔존 결과/복구율 미산출 |

로컬 검증의 실제 출력은 `samples/selftest.json`에 기록한다. 합성 DB를 사용하는 분석기 검증으로, 브라우저 또는 AI 서비스가 생성한 데이터가 아니다. 원격 push/PR/이슈 체크 변경은 수행하지 않았다.

최초 합성 검증은 SQLite 연결 미종료로 임시 파일 정리에서 WinError 32가 발생했다. 명시적으로 연결을 닫도록 수정한 뒤 UTC 2026-11-16T10:59:40에 재실행하여 6개 검사를 통과했다. PowerShell AST 구문 검사도 오류 0건으로 통과했다. 수집기의 실제 프로필 실행은 수행하지 않았다.

## 사용자 제공 프로젝트 확인

- 사용자가 `C:\Users\PC\Downloads\Africa_Youth-main`을 제공했다. 실제 프로젝트 루트는 하위 `Africa_Youth-main`이었다.
- 전체 파일을 열거했으며 AGENTS.md는 없었다. 03 README/results는 목차, samples는 .gitkeep만 있는 상태였다.
- 원본을 `Africa_Youth_project` 작업 폴더로 복사한 뒤 03 연구 작업본을 적용했다. Downloads 원본은 변경하지 않았다.
- 루트 README, 01 PoC README/analyze.py/sample_events.json, 04 요구사항을 읽었다. 01 상관분석기가 합성 데이터만 허용함을 확인하고 문서에 직접 실데이터 연계 불가를 명시했다.
- 사용자가 커밋/PR 금지를 명시했으므로 commit/push/PR은 수행하지 않는다.
