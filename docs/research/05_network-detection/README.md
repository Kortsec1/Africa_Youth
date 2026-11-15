# 연구 주제
Windows 포렌식 아티팩트 기반 Shadow AI 사용 행위 탐지 및 분석

## 1. 연구 목표
DNS 및 네트워크 연결 정보를 활용하여 생성형 AI 서비스 접근을 식별하고,
네트워크 증거를 통해 확인할 수 있는 AI 사용 행위의 범위를 연구한다.

## 2. 기술 조사
#### 2.1 AI 서비스 도메인 및 DNS 특성
| 서비스 | 주요 도메인(후보) | 비고 |
|---|---|---|
| ChatGPT | `chatgpt.com`, `chat.openai.com`(구), `ws.chatgpt.com`(WebSocket), `files.oaiusercontent.com`(파일 업·다운로드), `cdn.oaistatic.com`(정적), `api.openai.com`(API) | OpenAI 도움말의 허용 도메인 목록 기준. `openai.com` 자체는 회사 홈페이지 겸용 → 사용 증거로 쓰지 않음 |
| Claude | `claude.ai`(UI), `api.anthropic.com`(API) | `anthropic.com`·`claude.com` 은 회사/문서 사이트 |
| Gemini | `gemini.google.com`, `aistudio.google.com`, `generativelanguage.googleapis.com`(API) | 정적 리소스는 Google 공용 도메인(`gstatic.com` 등)과 공유 → 도메인 단독 식별 어려움 |
| Copilot | `copilot.microsoft.com`, `copilot.cloud.microsoft` | M365 내장 Copilot 은 Office 도메인과 섞여 분리 어려움 |
| 기타 | `perplexity.ai`, `chat.deepseek.com`, `grok.com`, `chat.mistral.ai`, `wrtn.ai`(뤼튼), `clova-x.naver.com`, `poe.com` | 전체 목록: `src/shadow_ai_forensics/data/ai_services.toml` |

조사 시 확인할 DNS 특성:
- **CDN 공유 IP**: 주요 서비스가 Cloudflare 등 CDN 뒤에 있어 IP 로는 서비스 구분 불가 → **도메인(QueryName/SNI) 기준**으로 판정해야 함.
- **CNAME 체인**: Sysmon EID 22 `QueryResults` 에 CNAME(`type: 5 ...`)이 남음 → 실제 CDN 확인 가능.
- **프리페치/프리커넥트**: 브라우저가 페이지 안의 링크 도메인을 미리 질의 → 질의 1건 ≠ 사용. 엔진은 DNS 만 있는 세션의 신뢰도를 낮춤.
- **DNS 캐시·짧은 TTL**: 캐시 적중 시 질의가 다시 발생하지 않아 '사용 종료 시각' 추정에는 부적합.
- **DoH (DNS over HTTPS)**: 브라우저 보안 DNS 사용 시 OS DNS-Client 로그·Sysmon EID 22 에 질의가 남지 않을 수 있음 → 실험 N-3.
- **ECH (Encrypted Client Hello)**: 적용되면 네트워크 장비에서 SNI 로도 도메인을 볼 수 없음 → 엔드포인트 증거의 가치가 커짐.

#### 2.2 Windows 네트워크 정보 수집 방법
| 방법 | 수집 정보 | 장점 | 한계 |
|---|---|---|---|
| Sysmon EID 22 (DNSQuery) | 질의 도메인, 결과, **질의 프로세스** | 프로세스 귀속 → 브라우저/앱/스크립트 구분 | Sysmon 설치 필요, DoH 우회 |
| Sysmon EID 3 (NetworkConnect) | 목적지 IP·포트·호스트명, 프로세스 | 연결 단위 기록 | 대량 이벤트 → 필터 필요, 호스트명은 역조회 의존 |
| DNS-Client/Operational (EID 3006/3008/3020) | 질의 도메인 | OS 기본 로그 | **기본 비활성화**, 프로세스명 없음(PID 만) |
| `ipconfig /displaydns` | 현재 DNS 캐시 | 즉시 확인 | 휘발성, 시각 정보 없음 |
| `Get-NetTCPConnection`/netstat | 현재 연결 | 라이브 대응 | 휘발성 |
| SRUM (`SRUDB.dat`) 네트워크 사용량 | 앱별 송수신 바이트 (1시간 단위) | 사후 아티팩트, **업로드 규모 추정** 가능 | 도메인 정보 없음, 시간 해상도 낮음 |
| Windows 방화벽 로그 (`pfirewall.log`) | IP·포트 | 기본 기능 | 기본 비활성, 도메인 없음 |
| 프록시/SWG 로그 (엔드포인트 외부) | URL·바이트·사용자 | 조직 전체 가시성 | 사내망 밖 트래픽 누락, 본 연구 범위 밖(비교 기준으로만) |

#### 2.3 접속 시 DNS·연결 이벤트 분석 (실험 설계)
1. Sysmon(EID 3·22) + DNS-Client 로그 활성화 VM 에서 서비스별 '새 대화 → 프롬프트 → 파일 업로드 → 다운로드' 수행.
2. 각 단계 직후 발생한 질의 도메인 목록을 수집해 **단계 ↔ 도메인 지문**을 만든다 (예: 업로드 시 `files.oaiusercontent.com`).
3. 브라우저 보안 DNS(DoH) on/off, QUIC on/off 로 같은 실험을 반복해 로그 누락 여부 확인.
4. SRUM 에서 실험 시간대 chrome.exe 송신 바이트를 확인해 업로드 크기와 비교.
→ 세부 절차와 기록 양식: [results.md](results.md)

## 3. 프로젝트 적용 가능성
- 엔진은 Sysmon EID 3/22, DNS-Client EID 3006/3008/3020 을 파싱해 `dns_query`/`net_connect` 이벤트로 정규화한다.
- 도메인 역할(upload 등)은 SAI-004(업로드 정황)에서 "파일 선택 ↔ 업로드 엔드포인트 통신" 시간 일치 판단에 쓰인다.
- 프로세스 귀속으로 **브라우저 사용 / 데스크톱 앱 / 스크립트 API 호출 / 로컬 LLM** 채널을 구분한다 (세션의 `channel`).
- 실험 결과로 도메인 지문이 확정되면 카탈로그 TOML 만 수정하면 된다 (코드 변경 불필요).

## 4. 참고 자료
- OpenAI Help Center, *Network recommendations for ChatGPT errors on web and apps* (허용 도메인·WebSocket·업로드 도메인) https://help.openai.com/en/articles/9247338
- Microsoft Sysinternals, Sysmon https://learn.microsoft.com/sysinternals/downloads/sysmon
- Chromium, *Secure DNS (DNS-over-HTTPS)* 정책 https://chromeenterprise.google/policies/#DnsOverHttpsMode
- Cloudflare, *Encrypted Client Hello* https://blog.cloudflare.com/encrypted-client-hello/
- SRUM 분석: SrumECmd (Eric Zimmerman) https://ericzimmerman.github.io/
