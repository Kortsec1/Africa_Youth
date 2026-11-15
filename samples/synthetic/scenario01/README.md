가상 시나리오 데이터 생성기.

실제 Windows 실험 전에 상관분석 엔진을 검증하기 위해, 실제 도구 출력과 '같은 형식'의 파일을 만든다.
  - MFTECmd  : mft.csv, usn.csv
  - LECmd    : lnk.csv
  - JLECmd   : jumplist_AutomaticDestinations.csv
  - Chrome   : Chrome/History (SQLite)
  - EvtxECmd : sysmon_evtxecmd.csv
  - 에이전트  : agent.jsonl

⚠ 이 데이터는 '가상'이다. 실험 결과(results.md)로 인용하지 말 것.
   실제 실험 데이터는 docs/research/*/samples 에 별도로 수집한다.

시나리오 (2026-11-10, FIN-PC-07, 사용자 kim.analyst)
  [정상] 09:05 네이버 방문, 09:10 회의록 열람, 09:30 메모장 복사(이후 AI 사용 없음)
  [정상] 10:20 openai.com 뉴스 페이지 방문 (회사 홈페이지 → '사용'으로 보면 안 됨)
  [경미] 11:00 Claude 짧은 사용 (다른 행위와 연결 없음)
  [사고] 13:40 고객DB 압축 → 13:52 재무제표 열람 → 14:01 엑셀에서 복사 → ChatGPT 전환
         14:04 파일 선택창 → 압축파일 업로드 → 14:09 AI 생성 스크립트 다운로드 → 14:12 실행
         14:48~14:50 스크립트·압축파일 삭제
  [정책] 16:20 Ollama 실행, 16:30 LM Studio 모델(.gguf) 저장, 16:45 스크립트의 OpenAI API 호출
