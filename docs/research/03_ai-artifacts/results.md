# 실험 결과

> 상태: **실험 설계 완료 / 실측 전**. 결과 열은 실험 후 기입한다.

## 1. 실험 환경
- Windows 11 VM, Chrome·Edge 최신, ChatGPT/Claude/Gemini 테스트 계정(개인정보 없는 더미 계정)
- 도구: DB Browser for SQLite, Hindsight(Chromium 분석), LevelDB 파서(ccl_chromium_reader 등), 본 프로젝트 엔진

## 2. 실험 목적
서비스별로 브라우저/앱 아티팩트에 **무엇이 남는지**(사용 여부·시점·내용) 확인하고, 엔진 카탈로그(도메인·역할)를 실측으로 보정한다.

## 3. 실험 과정
| ID | 동작 | 확인 항목 |
|---|---|---|
| A-1 | 서비스별 새 대화 → 프롬프트 3개 | History URL 패턴, 페이지 title 에 대화 제목 반영 시점, visit 수 |
| A-2 | 파일 첨부 업로드 | 업로드 요청 도메인 (브라우저 DevTools/HAR 로 확인) → 카탈로그 `upload` 역할 반영 |
| A-3 | AI 생성 파일 다운로드 | `downloads` 테이블 컬럼값, Zone.Identifier |
| A-4 | 대화 삭제 후 아티팩트 잔존 | History·IndexedDB 에 대화 ID/제목 잔존 여부 |
| A-5 | 시크릿 모드 사용 | 남는 흔적(DNS, Prefetch 등) 목록 |
| A-6 | ChatGPT·Claude 데스크톱 앱 사용 | 앱 데이터 폴더 구조, 대화 캐시·로그 위치 |
| A-7 | Ollama / LM Studio 로 대화 | 모델 파일 경로, 대화 기록 파일 존재 여부 |

## 4. 실험 결과
| ID | 서비스 | 결과 | 카탈로그/파서 반영 |
|---|---|---|---|
| A-1 | | | |
| A-2 | | | |
| A-3 | | | |
| A-4 | | | |
| A-5 | | | |
| A-6 | | | |
| A-7 | | | |

## 5. 확인된 한계

## 6. 추가 연구 사항
- IndexedDB(LevelDB) 파서 추가 여부 결정
