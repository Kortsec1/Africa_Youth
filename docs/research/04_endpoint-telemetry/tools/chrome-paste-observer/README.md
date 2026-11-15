# Chrome 붙여넣기 관측 PoC

상태: 기존 Windows/Chrome 사용자 실험에서 실제 로드와 붙여넣기1건·미붙여넣기 대조0건 확인. 각1회 결과이며 버전/장기안정성 미검증. 게시 과정에서 새 브라우저 실행 검증은 하지 않음.

## 설치
1. Chrome 주소창에 chrome://extensions 입력.
2. 개발자 모드 켜기 → 압축해제된 확장 프로그램을 로드합니다.
3. 이 README가 있는 이 README가 있는 chrome-paste-observer 폴더 선택.
4. 도구 모음 퍼즐 아이콘에서 연구용 ChatGPT 붙여넣기 관측 열기.

## 실험
1. 메모장에 합성 문장 AI-CLIP-TEST-001 준비.
2. Chrome에서 https://chatgpt.com 열기.
3. 확장 팝업에서 새 실험 시작. 이전 기록을 대체하므로 기존 로그는 먼저 저장.
4. ChatGPT 탭 새로고침. 팝업에서 페이지 준비 1 이상 확인. 0이면 실험하지 말고 상태 확인.
5. 메모장 합성 문장 한 번 복사 → Chrome ChatGPT 입력창에 붙여넣기 한 번. 전송하지 않음.
6. 확장 팝업에서 붙여넣기 1건 확인 → 중지 → 로그 저장.
7. Chrome 다운로드 폴더에 chrome-paste-실행ID.jsonl 저장. 경로를 사용자에게 확인받아 분석.
8. A(이동만)와 B(붙여넣기)는 각각 새 실험으로 분리하고 각 로그를 저장.

## 수집 범위와 한계
- ChatGPT 도메인 최상위 문서에서 paste 이벤트 메타데이터를 관측. 특정 입력창 식별은 아직 미검증.
- 원문/대화/계정/전체 URL/키 입력/네트워크 요청 미수집. 데이터 외부 전송 없음.
- storage 권한과 chatgpt.com content script만 사용. clipboardRead/clipboardWrite 권한 없음.
- target_editable과 target_tag는 대상 요소 힌트. 편집 가능 요소가 반드시 GPT 입력창이라는 뜻은 아님.
- trusted는 브라우저가 생성한 이벤트의 속성. 특정 사람의 의도나 물리 조작을 보장하지 않음.
- paste 이벤트는 삽입 성공/AI 전송 성공 증거가 아님. 페이지가 기본 동작을 취소할 수도 있음.
- 기록은 원래 Windows 아티팩트가 아니라 추가 계측으로 생성한 로그.
- 최대 5000행. 초과 시 오류 표시. 무손실 보장 없음.
- Windows 수집기와 run_id가 독립적. 둘을 함께 실행할 때 파일명/UTC/실험 메모로 연결.
- 실험 종료 후 확장 프로그램 중지 또는 제거.

근거: https://developer.mozilla.org/en-US/docs/Web/API/Element/paste_event
설치: https://support.google.com/chrome/a/answer/2714278
