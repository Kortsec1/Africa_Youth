# 관련 연구·자료 조사

담당: 동훈 / 조사 기준일: 2026-11-15

## 0. 문서 성격과 한계

이 문서는 Endpoint Telemetry(클립보드·활성 창·프로세스 실시간 수집) 연구와 관련된 선행 연구, Windows 기본 기록, 탐지 기준, 통계, 데이터셋, 개인정보 기준을 **웹 검색으로 확인한 범위 안에서** 정리한 것이다.

- 각 자료는 검색 결과의 초록·요약 문단을 기준으로 정리했으며, **논문 원문 전체는 읽지 않았다.** 보고서에 인용하기 전에 원문을 확인해야 한다.
- 이 문서를 근거로 새로운 실험은 수행하지 않았다. 실험이 필요한 항목은 6장에 "후속 실험 후보"로만 기록한다.
- 보안 업체 보고서와 블로그는 학술 자료와 구분해 표시했다.

## 1. 조사 목적

1. 04 연구(실시간 사용자 행동 수집)와 기존 연구의 차이를 설명할 근거를 찾는다.
2. 04 실험 결과를 독립적으로 대조할 수 있는 Windows 기본 기록이 있는지 확인한다.
3. 클립보드 원문을 저장하지 않는 설계, 복사와 붙여넣기를 구분한 판단의 외부 근거를 확인한다.

## 2. 생성형 AI 포렌식 선행 연구

| 자료 | 유형 | 다루는 내용 | 04와의 관계 |
|---|---|---|---|
| Kankanamge 외, *Digital Forensic Investigation of the ChatGPT Windows Application* (arXiv 2505.23938, 2025) | 논문(프리프린트) | ChatGPT Windows 앱의 캐시·채팅 로그·레지스트리·프리페치·메타데이터 추출. 저자들은 Windows 버전을 다룬 첫 연구라고 밝힘 | 앱에 **남은 흔적** 분석. 04는 사용 **과정**의 실시간 기록 |
| 조경석·박윤지·김지윤·김병준·정두원, *Conversational AI Forensics: A Case Study on ChatGPT, Gemini, Copilot, and Claude* (SSRN, 2024, doi:10.2139/ssrn.4888688) | 논문 | 4개 대화형 AI의 포렌식 사례 연구. Windows 11에서 Copilot 흔적을 Edge 아티팩트로 찾는 내용 포함 | 국내 연구진. 비교 대상으로 원문 확인 우선순위 높음 |
| *LangurTrace: Forensic analysis of LLM applications* (Forensic Science International: Digital Investigation, 2025) | 학술지 | LLM 애플리케이션 아티팩트를 체계적으로 분석하는 프레임워크 제안 | 아티팩트 분류 체계 참고용 |
| Scanlon 외, *ChatGPT for Digital Forensic Investigation: The Good, The Bad, and The Unknown* (arXiv 2307.10195, 2023) | 논문 | ChatGPT(GPT-4)를 포렌식 **도구**로 쓸 때의 활용성과 한계 | 관점이 다름(AI를 조사 도구로 사용). 배경 설명용 |
| A. Fortuna, *Browser AI forensics* (2026) | 블로그 | Edge Copilot·Chrome Gemini가 대화 상태를 IndexedDB, Service Worker 캐시, 브라우저 DB에 저장 | 브라우저 쪽 보조 증거. 03 분야와 겹침 |

**정리:** 확인한 선행 연구는 모두 앱·브라우저·디스크에 **남은 흔적**을 다룬다. 이번 검색에서는 복사 → 창 전환 → 붙여넣기 흐름을 실시간으로 수집해 AI 사용 행위를 설명하는 학술 연구를 찾지 못했다. 이것이 04의 차별점이 될 수 있다. 다만 검색 범위가 제한적이므로 "선행 연구 없음"으로 단정하지 않는다.

## 3. 활성 창 관련 Windows 기본 기록

04 수집기와 별개로 Windows가 스스로 남기는 기록이다. 수집기 결과를 대조할 독립 기준 후보다.

| 기록 | 위치·형태 | 담긴 정보 | 한계 |
|---|---|---|---|
| UserAssist | 사용자별 NTUSER.DAT 레지스트리 | 실행 횟수, focus count(전면 창이 된 횟수), focus time(전면 창이었던 누적 시간, ms) | 빠른 전환 시 정확성·일관성에 논쟁이 있음. 누적값이라 개별 전환 시각은 없음 |
| EventTranscript.db (Win32kTraceLogging.AppInteractivity 계열) | Windows 진단 데이터 DB | 앱이 최상위 창이었던 시간 InFocusDurationMS | 사용자 귀속 정보가 없어 다른 기록과 연결해야 함. 진단 데이터 수준 설정에 영향받을 가능성(확인 필요) |
| CIT(Customer Interaction Tracker) | 레지스트리 | 프로그램별 전면 활동 비트맵 | 확인된 내용은 Windows 7까지. 최신 Windows 적용 여부 불명 |

**정리:** 세 기록 모두 **누적·집계값**이라 04가 기록하는 "몇 시 몇 분에 어느 창으로 바뀌었는가"를 대체하지 못한다. 대신 W1(창 전환 횟수) 같은 실험에서 수집기 기록과 대조하는 보조 기준으로 쓸 수 있다.

## 4. 클립보드 탐지 기준

| 자료 | 내용 | 04와의 관계 |
|---|---|---|
| MITRE ATT&CK T1115 Clipboard Data / DET0341 *Clipboard Data Access with Anomalous Context* | 클립보드 접근 자체가 아니라 비정상 맥락(낯선 프로세스, 예상 밖 부모-자식 관계, 스크립트 접근)에 탐지를 집중하라고 정리. 엔드포인트 도구가 클립보드 접근을 보지 못하면 경보가 없어도 활동이 없었다는 증거가 아님 | 04 결론("클립보드 변경 ≠ 붙여넣기·전송")과 같은 방향 |
| Sysmon Event ID 24 ClipboardChange | Sysmon 12.0(스키마 4.40)부터 지원. `<CaptureClipboard/>` 설정 필요. 복사한 프로세스와 내용 해시를 기록하고 원문은 보관 폴더에 따로 저장 | 04 수집기와 다른 독립 수집 수단. 원문 보관 기능은 04의 원문 미저장 원칙과 충돌하므로 사용 시 범위 제한 필요 |

## 5. 실태 통계 (연구 동기용)

모두 **보안 업체 보고서**다. 수치는 업체의 브라우저 확장 등 자사 텔레메트리에서 나온 것이므로 일반화에 주의한다.

| 출처 | 주요 수치 |
|---|---|
| LayerX, *Enterprise AI and SaaS Data Security Report 2025* | 기업 직원 약 18%가 생성형 AI에 데이터를 붙여넣음. 그중 50% 이상이 회사 정보 포함. 붙여넣는 사용자 1인당 하루 평균 6.8회, 그중 3.8회가 민감 데이터. 생성형 AI 접근의 71.6%가 비업무 계정 |
| Harmonic Security, 2025년 2분기 분석 | 생성형 AI에 올린 파일의 22%(4,400건 중), 프롬프트의 4.37%(43,700건 중)에 민감 정보 |

**정리:** 붙여넣기가 주요 유출 경로라는 점은 04가 클립보드·붙여넣기를 다루는 이유를 설명하는 데 쓸 수 있다.

## 6. 내부자 위협 공개 데이터셋

| 자료 | 구성 | 04와의 관계 |
|---|---|---|
| CMU SEI CERT Insider Threat Test Dataset (r4.2 등, doi:10.1184/R1/12841247.v1) | 합성 데이터. logon, device(USB), http, email, file(이동식 매체 복사), psychometric, ldap | **클립보드·활성 창 기록이 없다.** 실제 내부자 위협 데이터셋이 공개되지 않아 대부분의 연구가 이 합성 데이터를 사용 |

**정리:** 04가 수집하는 행위 데이터(클립보드 변경, 창 전환, 붙여넣기 이벤트)는 대표적인 공개 데이터셋에 없는 영역이다.

## 7. 국내 논문

| 자료 | 내용 | 04와의 관계 |
|---|---|---|
| 최정완, 「기업 내 생성형 AI 시스템의 보안 위협과 대응 방안」, 융합보안논문지 24(2), 2024 | 내부자 위협 감지를 위해 AI 질의응답 과정의 이상 징후 탐지 체계를 제안 | 탐지 관점의 국내 근거 |
| 류정화·전유란·김수경·이일구, 한국산업보안연구 14(3), 2024 | 생성형 AI를 이용한 산업기술 유출에 대한 법적 대응 부재를 지적하고 차등 접근 통제, CISO 중심 대응 제안 | 정책·법제 배경 |
| 이혜성·한유나, 「업무용 생성형 AI 모델의 안전한 활용을 위한 중요 기술정보 개체명 인식 및 비식별화 기법 개발 연구」, 한국산업보안연구 16(특별호), 2026 | 입력 데이터의 비식별화 | 예방 관점. 04(사후 설명)와 대비 |

## 8. 개인정보와 수집 범위

- 직원 모니터링 관련 자료들은 데이터 최소화, 목적 제한, 사전 고지를 공통 원칙으로 든다.
- EU 기준을 설명한 업체 자료는 키 입력 기록을 GDPR 데이터 최소화 원칙 위반으로 보고, 내용 없이 키보드·마우스 활동만 추적하는 것도 문제가 될 수 있다고 정리한다.
- 04는 클립보드 원문을 저장하지 않고 형식 정보만 기록하며, 창 제목은 선택 옵션이다. 이 설계는 위 원칙과 방향이 맞다.
- **국내 개인정보보호법 기준은 이번 조사에서 확인하지 않았다.** 보고서에 쓰려면 별도 확인이 필요하다.

## 9. 04 연구에 주는 시사점

1. **연구 위치:** 기존 연구는 "남은 흔적" 분석, 04는 "실시간 행위 흐름" 수집으로 구분해 설명할 수 있다.
2. **판단 기준의 근거:** "복사 ≠ 붙여넣기 ≠ 전송"으로 구분한 04의 판단은 MITRE의 맥락 중심 탐지 원칙과 일치한다.
3. **설계 근거:** 원문 미저장 설계는 데이터 최소화 원칙으로 설명할 수 있다.
4. **후속 실험 후보 (이번에는 수행하지 않음):** W1 재실험 시 UserAssist focus count와 EventTranscript를 독립 기준으로 함께 수집하는 방안. 실행 환경 문제(3.2절)가 해결된 뒤에 검토한다.

## 10. 참고 자료

선행 연구
- arXiv 2505.23938: https://arxiv.org/abs/2505.23938
- SSRN 4888688: https://doi.org/10.2139/ssrn.4888688
- LangurTrace(FSI:DI 2025): https://dfrws.org/wp-content/uploads/2025/10/LangurTrace-Forensic-analysis-of-lo_2025_Forensic-Science-International-Di.pdf
- arXiv 2307.10195: https://arxiv.org/abs/2307.10195
- Browser AI forensics: https://andreafortuna.org/2026/07/28/browser-ai-forensics/

Windows 기록
- Securelist, UserAssist 구조 분석: https://securelist.com/userassist-artifact-forensic-value-for-incident-response/116911/
- Magnet Forensics, UserAssist: https://www.magnetforensics.com/blog/artifact-profile-userassist
- Kroll, EventTranscript.DB Win32kTraceLogging: https://kroll.com/en/insights/publications/cyber/forensically-unpacking-eventtranscript/forensic-quick-wins-with-eventtranscript
- NCC Group, CIT: https://research.nccgroup.com/2022/04/12/a-brief-look-at-windows-telemetry-cit-aka-customer-interaction-tracker/

클립보드 탐지
- MITRE ATT&CK T1115: https://attack.mitre.org/techniques/T1115/
- DET0341 해설: https://security.glexia.com/learn/attack/detections/DET0341-clipboard-data-access-with-anomalous-context
- Sysmon 12.0 EID 24: https://medium.com/falconforce/sysmon-12-0-eventid-24-31e0109c78e3

통계·데이터셋
- LayerX 보고서 보도: https://www.esecurityplanet.com/news/shadow-ai-chatgpt-dlp/
- Harmonic Security 분석 보도: https://securitybrief.co.uk/story/sensitive-data-exposure-rises-with-employee-use-of-genai-tools
- CERT 데이터셋 설명(arXiv 2005.12433): https://arxiv.org/abs/2005.12433

국내 논문
- 최정완(2024): https://www.earticle.net/Article/A452755
- 류정화 외(2024): https://www.earticle.net/Article/A460123
- 이혜성·한유나(2026): https://www.earticle.net/Article/A479147

개인정보
- Clockify, 직원 모니터링 지역별 기준: https://clockify.me/blog/workforce-management/monitor-employee-computer-activity/
