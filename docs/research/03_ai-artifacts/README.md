# 연구 주제
Browser / AI 서비스 포렌식 — 생성형 AI 사용이 브라우저와 AI 앱에 남기는 흔적

## 1. 연구 목표
- 웹 브라우저 및 AI 데스크톱 앱·로컬 LLM 이 로컬에 남기는 아티팩트를 서비스별로 정리한다.
- 각 아티팩트가 **"사용 여부 / 사용 시점 / 사용 내용(프롬프트·첨부·결과물)"** 중 무엇을 증명할 수 있는지 구분한다.

## 2. 기술 조사

### 2.1 브라우저 공통 아티팩트 (Chromium: Chrome·Edge·Whale)
경로: `%LOCALAPPDATA%\<Vendor>\<Browser>\User Data\<Profile>\`

| 아티팩트 | 위치 | 증명 가능 | 비고 |
|---|---|---|---|
| History `urls`·`visits` | `History` (SQLite) | 접속 시각·URL·페이지 제목·체류시간(`visit_duration`) | 대화 URL(`chatgpt.com/c/<id>`)과 **대화 제목**이 페이지 title 로 남는 경우가 많음 → 대화 주제 추정 근거 |
| History `downloads` | `History` | 다운로드 파일 경로·원본 URL·`tab_url`·`referrer`·MIME | AI 생성물 다운로드(SAI-005) |
| Cookies / Login Data | `Network\Cookies`, `Login Data` | AI 서비스 로그인 여부·계정(이메일) | 값은 DPAPI/앱 바인딩 암호화 — 존재·시각 위주 활용 |
| Local Storage / IndexedDB | `Local Storage\leveldb`, `IndexedDB\https_<site>_0.indexeddb.leveldb` | 일부 서비스의 대화 캐시·설정 | LevelDB 파싱 필요, 서비스 업데이트로 구조 변동 |
| Cache | `Cache\Cache_Data` | API 응답 조각·이미지 | 대화 본문은 스트리밍이라 캐시되지 않는 경우가 많음 |
| Session/Tabs | `Sessions\` | 종료 시 열려 있던 AI 탭 | |
| Extensions | `Extensions\` | AI 확장 프로그램 설치 | 확장 자체가 Shadow AI 인 경우 |

- Firefox: `places.sqlite`(moz_places, moz_historyvisits; Unix epoch µs).
- 시크릿 모드: 히스토리 없음 → DNS(05)·텔레메트리(04)·파일시스템(02)으로 보완.

### 2.2 서비스별 특징
| 서비스 | 대화 URL 패턴 | 업로드/파일 도메인 | 브라우저 외 클라이언트 |
|---|---|---|---|
| ChatGPT | `chatgpt.com/c/<uuid>` | `files.oaiusercontent.com` (OpenAI 도움말에 업로드 실패 시 허용할 도메인으로 명시) | Windows 앱 |
| Claude | `claude.ai/chat/<uuid>` (조사 필요: 업로드 엔드포인트) | 미확인 → 03 실험 | Claude Desktop |
| Gemini | `gemini.google.com/app/<id>` | Google 공용 도메인과 섞임 | – |
| Copilot | `copilot.microsoft.com` | – | Edge 사이드바, Windows Copilot 앱 |
| 로컬 LLM | – | – | Ollama, LM Studio |

### 2.3 AI 데스크톱 앱
- **ChatGPT Windows 앱**: 2025년 연구(arXiv 2505.23938)는 ChatGPT Windows 앱의 캐시·채팅 로그·레지스트리·프리페치 등을 분석했고, 삭제 후에도 채팅 기록과 시스템 흔적을 복구할 수 있었다고 보고함.
- **Claude Desktop (Electron)**: 버전·설치 방식에 따라 경로가 다름. 문서상 `%APPDATA%\Claude\` (설정 `claude_desktop_config.json`, `logs\`), MSIX 설치본은 `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\`, 로그는 `%LOCALAPPDATA%\Claude\Logs` 로 보고됨. `claude_desktop_config.json` 의 MCP 서버 설정은 '에이전트형 Shadow AI'(로컬 파일·도구 접근) 판단 근거.
- Electron 앱은 내부에 Chromium 프로필(`Partitions`, `Local Storage`, `IndexedDB`)을 가지므로 2.1 의 기법을 그대로 적용할 수 있다.

### 2.4 로컬 LLM
| 도구 | 실행 흔적 | 모델 파일 | 사용 흔적(조사 필요) |
|---|---|---|---|
| Ollama | `ollama.exe`, 로컬 API `127.0.0.1:11434` | `%USERPROFILE%\.ollama\models\blobs\sha256-*` (확장자 없음) | CLI 대화 이력 파일 존재 여부 확인 |
| LM Studio | `LM Studio.exe`, 로컬 서버 기본 포트 1234 | `%USERPROFILE%\.lmstudio\models\**\*.gguf` | 대화 저장 폴더 확인 |
- 로컬 LLM 은 외부 트래픽이 없어 네트워크 탐지로는 보이지 않음 → 프로세스 실행·대용량 모델 파일 생성이 핵심 증거 (SAI-007).

## 3. 프로젝트 적용 가능성
- 구현 완료: Chromium History(방문·다운로드·URL 체인), Firefox places 파서 (`parsers/browser.py`). 실행 중 잠금을 피하려 `-wal` 포함 복사 후 읽기 전용으로 연다.
- 페이지 제목(대화 제목)에 민감 키워드가 있으면 `sensitive` 태그 → 대화 주제 단서로 활용 중.
- 다음 단계: IndexedDB/LevelDB 에서 대화 ID·제목 추출, Claude Desktop 로그 파서, Cookies 로 계정 식별(개인 vs 회사 계정 구분).

## 4. 참고 자료
- M. W. Kankanamge et al., *Digital Forensic Investigation of the ChatGPT Windows Application*, arXiv:2505.23938 (2025) https://arxiv.org/abs/2505.23938
- OpenAI Help Center, *Network recommendations for ChatGPT errors on web and apps* https://help.openai.com/en/articles/9247338
- Anthropic, Claude Desktop 데이터 저장 위치 문서 https://www.claude.com/docs/third-party/claude-desktop/data-storage
- Cyber Triage 문서 (Claude Desktop 설정 파일 MSIX 경로) https://docs.cybertriage.com/en/latest/chapters/integrations/claude_client.html
- A. Fortuna, *Browser AI forensics* (2026) https://andreafortuna.org/2026/07/28/browser-ai-forensics/
- Chromium 소스 `components/history/core/browser/history_database.cc` (History 스키마)
