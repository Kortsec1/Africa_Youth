# Shadow AI Forensics 연구 결과 통합 — STEP 1

작성일: 2026-11-27. 대상: `Kortsec1/Africa_Youth`의 로컬 체크아웃, 기준 커밋 `cb48814b248b0dd836da6b48dc778d0186b56944`. 작업 브랜치: `docs/integration-step1`.

이 문서는 기존 5개 연구를 연결하는 연구 보고서이자 다음 단계의 최소 구현 명세다. 새 보안 솔루션, 전송 탐지기 또는 중앙 관제를 개발하는 계획이 아니다. STEP 1에서는 연구 파일과 입출력·실행 경로를 확인하고 이 문서만 작성했다. 기존 `docs/research`는 수정하지 않았으며 통합 프로그램 구현, 새 Windows 수집 실험, commit/push/PR은 수행하지 않았다. 원격 최신 상태와의 동기화는 하지 않았다.

## 1. 확인 범위와 증거 구분

각 디렉터리의 파일 목록, README·결과 문서, 통합에 필요한 코드와 JSON/JSONL을 확인했다. 전체 코드를 보안 감사하거나 연구 실험을 반복한 것은 아니다. 아래에서 ‘보고됨’은 기존 연구 보고서의 실행 결과, ‘자료 확인’은 현재 저장소에서 해당 산출물을 읽을 수 있다는 뜻이다. 비공개 원본과 스크린샷의 모든 주장을 이번에 독립 재검증한 것은 아니다.

- **실측 자료:** 실제 환경에서 기록된 관측. 실험에 더미 파일·합성 문장을 사용했어도 로그 자체가 인위적으로 생성된 것은 아니다.
- **공유용 파생 자료:** 실측 로그에서 일부 필드를 제거한 게시본. 원시 로그와 같은 스키마·증거 범위를 갖지 않는다.
- **합성 자료:** 코드나 사람이 만든 이벤트·DB. 실제 수집 성공이나 탐지 성능의 근거로 사용하지 않는다.
- **문헌·계획:** 실행 코드나 실측 증거가 확인되지 않은 설명. 검증 완료로 표시하지 않는다.

## 2. 5개 연구의 핵심 결과와 산출물

| 연구 | 확인한 산출물·재사용 코드 | 검증 범위와 통합상 의미 |
|---|---|---|
| 01 탐지·상관분석 | [결과](research/01_detection/results.md), [규칙](research/01_detection/poc/rules.md), [analyze.py](research/01_detection/poc/analyze.py), `compare.py`, `test_analyze.py`, `sample_events.json`, 기본·확장 비교 입력/출력 | R01~R05, 시간순 정렬, ID 충돌·시간대 검사 구현. 합성 사례 검증이며 실제 로그·유출 탐지는 미검증. 확장 비교에서 60→300초로 늘리면 TP 1→2, FP 1→3: 시간 인접성은 인과관계가 아니다. |
| 02 Windows 포렌식 | [결과](research/02_windows-forensics/results.md), [관측 JSON](research/02_windows-forensics/samples/observations.json), 더미 텍스트, [조사 문서](research/02_windows-forensics/README.md) | 단일 Windows/NTFS 호스트에서 생성·열람·수정·복사·삭제 각 1회 보고. 메타데이터 4개 스냅샷, 복사본 ID 차이·해시 일치·삭제 후 부재 자료 확인. 별도 실행 가능한 수집 스크립트는 없다. MFT/USN 본격 파싱·LNK·JumpList는 조사 단계. |
| 03 AI 아티팩트 | [결과](research/03_ai-artifacts/results.md), [실측 보고](research/03_ai-artifacts/README%20%282%29.md), [History 분석기](research/03_ai-artifacts/analyze_history.py), `selftest.py`, `collect.ps1`, `live_probe.py`, `inspect_sst_marker.py`, before/unsent/sent JSON, 검증·출처 JSON, PNG·마커 발췌 바이너리 | History 분석기는 합성 DB 6개 검사. 실제 ChatGPT에서는 미전송·전송 마커의 저장소 잔존과 전송 후 응답 화면을 보고했지만 History는 잠금으로 실패. 저장소 문구 존재만으로 전송 판정 불가. 업로드 성공 미검증. |
| 04 엔드포인트 | [결과](research/04_endpoint-telemetry/results.md), [C# 수집기](research/04_endpoint-telemetry/poc/windows-collector/Program.cs), [실행 안내](research/04_endpoint-telemetry/poc/windows-collector/README.md), 검증 PowerShell 2개, [Chrome 확장](research/04_endpoint-telemetry/tools/chrome-paste-observer/README.md), [공유 증거](research/04_endpoint-telemetry/evidence/README.md) | Clipboard 6회 관측, 복사 1회/붙여넣기 3회에서 변경 알림 1건, 프로세스 시작·종료, 창 이벤트 수신이 보고됨. 확장 paste 양성 1건/음성 0건 각 1회. 공개 자료는 5개 projected JSONL과 요약·manifest. 활성 창 원시 행과 ETL은 공개 파일에 없음. |
| 05 네트워크 | [결과](research/05_network-detection/results.md), [절차](research/05_network-detection/protocol.md), [collect_network.ps1](research/05_network-detection/poc/collect_network.ps1), [export_dns_log.ps1](research/05_network-detection/poc/export_dns_log.ps1) | DNS 캐시/TCP 폴링 실험 보고. 최초 DNS 관측 후 8회에서는 chatgpt.com 캐시 누락, 후보 IP 연결은 관측됨. 접속만/입력·전송 각 1회의 IP·횟수는 같음. 원시 JSONL은 저장소에 없고 결과표만 확인 가능. DNS-Client 내보내기는 미사용. |

### 현재 파일 배치의 주의점

03 문서에 나오는 `scripts/`, `samples/`, `evidence/live-20261116/`, `screenshots/` 경로와 달리 현재 관련 파일은 `research/03_ai-artifacts/` 바로 아래에 있다. 이 문서의 링크와 명령은 실제 배치를 따른다. `results.md`의 초기 합성 실험 표 및 미실행 매트릭스와 후속 실측 설명이 함께 있으므로 후속 [실측 보고](research/03_ai-artifacts/README%20%282%29.md)를 함께 읽어야 한다. `download`는 빈 파일, `download (1)`은 Python 캐시 제외 패턴 텍스트이며 분석 데이터로 사용하지 않는다. 기존 문서·경로는 이번에 수정하지 않는다.

### 연구 간 상호 보완

02는 파일 상태, 03은 브라우저 방문과 저장소 잔존, 04는 사용자 행동 주변의 관측, 05는 프로세스의 네트워크 접근 정황을 제공한다. 01은 조건이 갖춰진 이벤트의 시간·장치·사용자·순서를 연결하고 판단 근거를 설명한다. 브라우저 방문은 DNS 누락 시 도메인 근거를 보완할 수 있고, paste 계측은 Clipboard 변경만으로 알 수 없는 웹 붙여넣기를 보완한다.

현재 자료는 서로 다른 날짜·호스트·실행에서 얻었다. 이들을 한 화면에 나열할 수는 있어도 ‘파일 읽기 → 복사 → AI 붙여넣기 → 전송’이라는 하나의 실제 사건으로 연결할 수 없다. 같은 실험이라는 근거와 식별자 매핑이 없으면 실험별로 분리한다.

## 3. 연동 대상 결정

| 기능 | 결정 | 현재 사용할 수 있는 자료·조건 |
|---|---|---|
| 기존 R01~R05 | 즉시 재사용: 합성 규칙 시연 | 01 원본 샘플을 변경 없이 기존 `analyze()`에 입력. 결과의 근거 ID·관찰·추론·한계를 표시. |
| 파일 메타데이터 | 즉시 표시 | 02 `observations.json`. 행위 로그로 승격하지 않고 메타데이터 스냅샷으로 사용. |
| Clipboard 변경 | 즉시 표시 | 04의 복사 관련 projected JSONL 2개. 조회 실패/누락을 false로 바꾸지 않음. |
| 프로세스 활동 | 즉시 표시 | `process-test.projected.jsonl` 2행. PID·이름 연결은 후보, `instance_identity_verified=false` 유지. |
| Chrome paste | 즉시 표시 | 양성 4행(그중 paste 1행), 음성 3행(그중 paste 0행). 준비·시작·종료 행은 행동과 구분. |
| 브라우저 방문 | 조건부 연동 | 기존 분석기가 만든 JSON을 입력받는 구조. 저장소에는 성공한 실제 History 방문 추출본이 없으므로 기본 실측 데모에 방문을 만들어 넣지 않음. |
| 활성 창 | 조건부 연동 | C# 출력 스키마는 확인. 검토된 기존 로그가 제공되면 처리하고, 현재 공개 자료만으로는 ‘자료 없음’ 표시. |
| DNS/TCP | 조건부 연동 | PowerShell 출력 스키마는 확인. 검토된 기존 JSONL 확보 시 처리. 결과표를 원시 이벤트로 재구성하지 않음. |

**문서로 남길 기능:** MFT/USN 원본 파싱, LNK/JumpList/휴지통 연계, Security 4663·4688·4689, ETW 파일 I/O, DNS-Client/Sysmon/네트워크 ETW, 패킷 분석, 전송 요청 자동 수집, 업로드 성공 판정. IndexedDB/SST 마커 분석은 의미 구분을 보여주는 연구 결과로 참조하되 통합 파서를 새로 만들지 않는다. 별도 수동 요청 화면도 자동 탐지 결과로 만들지 않는다.

## 4. 수집원별 실제 입출력과 시간의 의미

아래는 실제 파일 또는 코드에서 확인한 필드다. 출력 코드가 있다는 것과 사용 가능한 실측 출력 파일이 있다는 것은 구분한다.

| 수집원 | 입력·출력 형태와 주요 필드 | 시간·식별·해석 |
|---|---|---|
| 01 규칙 | 입력 JSON 배열: `event_id, occurred_at, device_id, user_id, process_entity_id, event_type, source, source_ref, synthetic, attributes`. 출력 JSON 객체: `timeline, events, alerts, policy_version, parameters, limitation, synthetic` | 시간대 있는 `occurred_at` 필수. `synthetic is True`, 장치 ID 필수. 사용자 null 허용. `file_access/read_data`, `ai_service_access/browser_visit`가 규칙 핵심 입력. |
| 02 메타데이터 | JSON 객체의 `events[]`: `phase, file, creationUtc, writeUtc, accessUtc, bytes`. 루트: `os, format, powerShell, hashMatch, originalFileId, copyFileId, usnProbe, copyExistsAfterRemoval` | 4개 스냅샷. 별도 관측 시각·사용자·장치 ID 없음. `phase=read`는 실험 단계 표기이며 접근 감사 이벤트가 아님. 삭제 시각 없음. `hashMatch`는 비교 결과이지 원본 SHA-256 값이 아님. |
| 03 History 분석 | 기존 Chromium History 작업 사본의 `visits JOIN urls` → JSON 객체의 `events[]`: `record_id, raw_chromium_time, event_time_utc, host, service, url, title, time_semantics, action_claim, evidence_level, limitations`; 루트 `dataset_type, history_sha256, sqlite_version` | 1601 epoch 마이크로초 → UTC, 잘못된 값은 시각 null. `time_semantics=browser_visit_time`, `action_claim=service_visit_record`. 사용자/장치 없음. 출력의 `provided_history_not_independently_authenticated`는 실제 데이터 인증 표시가 아님. |
| 03 live probe | JSON: `collected_utc, method, profile, markers, hits[], errors[], files_scanned, history`. hit에 `path, marker, encoding, first_byte_offset, count, length, sha256_at_read` | `collected_utc`는 수집 시각이며 입력·전송 시각 아님. 현재 세 파일의 History는 unavailable. 저장소 출현 횟수는 질문 횟수 아님. 자동 Timeline의 사용자 행동으로 사용하지 않음. |
| 04 C# 원래 출력 | JSONL schema 2: `run_id, event_id, observed_at_utc, monotonic_ms, type, data`. `clipboard_update`, `foreground_change/title_change/snapshot`, `process_start/stop/snapshot`, 상태·오류·종료 행 | `observed_at_utc`는 행 생성 관측 시각. WMI `data.source_time_utc/source_time_filetime`은 이벤트 생성 시각. 창의 `source_event_tick_ms`는 uptime으로 UTC 아님. 초기 snapshot은 과거 start 이벤트가 아님. 시작 메타데이터의 장치/사용자는 확보된 실행 범위에서만 연결. |
| 04 공개 Clipboard·프로세스 | JSONL: `projection, experiment, type, observed_at_utc, event_id, data`. Clipboard의 sequence/조회 상태/형식/재시도, 프로세스의 PID·부모 PID·이름·세션·연결 상태 등을 남김 | 원본 `run_id`, 장치/SID, 창 정보·일부 원천 시각 등이 제거됨. run은 [manifest](research/04_endpoint-telemetry/evidence/projection-manifest.json)로 출처 확인 가능. 관측 시각만으로 원천 시각 복원 금지. |
| 04 확장 원래 출력 | JSONL schema 1 관측 행: `document_id, type, observed_at_utc, document_monotonic_ms, origin, run_id, tab_id, event_id`; paste에는 `trusted, target_tag, target_editable, payload_collected, semantics` | DOM paste 콜백 관측 시각. 시작·종료 행은 일부 필드 없음. Windows 수집기와 run_id 독립. `target_editable`이 ChatGPT 입력창 자체를 증명하지 않음. |
| 04 공개 웹 paste | JSONL: `projection, experiment, type, observed_at_utc, origin, trusted, target_editable, target_tag, payload_collected` | `event_id/run_id/tab_id/document_id`가 없음. 원본 문장 없음. paste 양성/음성은 다른 실험. |
| 05 DNS | 코드 출력 JSONL schema 1, `source=dns_cache`, `observed_at, domain, record_type, data, ttl_remaining, matched_ai, evidence_level` | 캐시에서 처음 본 항목의 폴링 시각. 실제 질의 시각 아님. 캐시가 수집 전부터 존재했을 수도 있음. 사용자·장치·이벤트 ID 없음. |
| 05 TCP | 코드 출력 JSONL schema 1, `source=tcp_conn`, `observed_at, pid, process_name, remote_ip, remote_port, domain_from_dns_cache, matched_ai, evidence_level` | Established 상태에서 처음 관측한 연결. 새 연결 생성 시각을 보장하지 않음. 내부 중복 키는 PID/IP/원격포트/로컬포트지만 출력에는 로컬포트 없음. PID 캐시와 IP→도메인 연결은 재사용·공유 IP 한계가 있음. |
| 05 상태 행 | `source=collector`, `event=start/end`, `observed_at`; 시작 `label, interval_sec, duration_sec`, 종료 카운터. 소스별 오류 행에는 `error` | label은 시작 행에서 같은 파일에만 전파. 오류/종료 통계를 접속 이벤트로 세지 않음. `matched_ai`는 도메인 패턴 매칭이며 결과 문서의 사후 IP 5개 매칭과 다름. |

04 게시본에는 이름이 `observed_at_utc`여도 `+09:00` 값이 있다. 필드명 대신 문자열의 실제 offset으로 UTC 변환하고 원문을 보존한다. 05 문서의 ‘최대 1초 오차’는 하드 보장으로 채택하지 않는다. 코드가 조회 작업 후 1초 쉬므로 주기가 더 길 수 있고, 기존 캐시/연결은 발생 시각과의 차이를 상한으로 정할 수 없다.

### 기존 실행 경로

아래는 실행 방법 확인용이다. STEP 1에서 수집기를 새로 실행한 것은 아니다. 모든 새 출력은 연구 원본 디렉터리 밖의 비공개 작업 경로에 둔다.

- 01: 저장소 루트에서 `python3 docs/research/01_detection/poc/analyze.py docs/research/01_detection/poc/sample_events.json`. 비교 실행은 [RUN.md](research/01_detection/poc/RUN.md) 참조. 외부 패키지 없음.
- 02: 독립 실행 스크립트 없음. [결과의 실험 절차](research/02_windows-forensics/results.md)를 참조하고 기존 JSON을 사용한다.
- 03: `python3 docs/research/03_ai-artifacts/analyze_history.py --history <작업사본/History> --output <새출력.json>`. `collect.ps1 -ProfilePath <실험프로필> -OutputPath <새폴더>`는 종료된 브라우저의 선택 파일 복사 도구이며 실프로필 수집 실행 검증은 별도다. 기본 통합 화면은 이미 추출된 JSON만 받는다.
- 04: Windows/.NET 8에서 수집기 폴더 기준 `dotnet build -c Release`, 실행 파일에 `--seconds 60 --out <비공개폴더>`. 과거 성공과 현재 Smart App Control 차단을 구분한다. 확장은 [안내](research/04_endpoint-telemetry/tools/chrome-paste-observer/README.md)의 수동 로드·시작·중지·JSONL 내보내기 사용.
- 05: Windows PowerShell에서 `collect_network.ps1 -Label S1_run1 -DurationSec 180 -OutDir <비공개폴더>`. 선택적 DNS-Client 내보내기는 구현만 확인했으며 기본 연동에서 제외한다.

## 5. 최소 공통 데이터 구조 제안

JSON/JSONL을 읽어 메모리의 이벤트 목록으로 통일한다. 영구 DB는 필요 없다. 기존 01과 비슷한 이름을 유지하되 모호한 시각을 발생 시각으로 가장하지 않도록 `event_time`과 `time_semantics`를 함께 둔다.

| 필드 | 형식·규칙 |
|---|---|
| `event_id` | 문자열. 원본 식별자는 `attributes.original_event_id`에 보존. 통합용 ID는 입력 파일 SHA-256 + 행/JSON 경로 + 세부 항목으로 결정적으로 부여한다. 관측 사실을 생성하는 것이 아닌 내부 추적키임을 명시한다. |
| `event_time` | UTC ISO 8601 또는 null. 의미가 확인된 원천 시각이나 관측 시각만 사용. 타임존 미상은 추정하지 않는다. |
| `time_semantics` | `browser_visit_time`, `collector_observation_time`, `wmi_event_generation_time`, `filesystem_creation_time`, `filesystem_last_write_time`, `filesystem_last_access_time`, `poll_observation_time`, `unknown` 등. |
| `source` | `file_metadata`, `browser_history`, `windows_collector`, `chrome_paste_observer`, `dns_cache`, `tcp_conn`, `synthetic_rule_fixture` 등 어댑터 식별자. 원본 source/type도 보존. |
| `event_type` | 메타데이터·방문·변경·paste·네트워크·수집 상태를 구분. 예: `file_metadata_snapshot`, `browser_visit`, `clipboard_update`, `foreground_change`, `process_start`, `paste_event`, `dns_cache_observation`, `tcp_connection_observation`, `collector_status`. |
| `attributes` | 객체. 원본 시각 문자열, 관측 시각, PID·파일 필드·서비스·조회 결과 등 필요한 내용. 원문이 없으면 새로 만들지 않는다. |
| `device_id`, `user_id` | 확인된 값 또는 null. 익명화 자료의 누락값을 파일명·PID·동일 날짜로 추정하지 않는다. 서로 다른 사용자 ID 체계는 확인된 매핑 없이 합치지 않는다. |
| `source_ref` | `{file, sha256, locator}`. locator는 JSON Pointer 또는 JSONL 1-based 행 번호. 게시본 해시와 비공개 원본 해시는 구분하고, 원본 해시는 manifest에 있는 경우에만 별도 보존한다. |
| `experiment_id` | 원본 experiment/label 또는 근거 있는 실험 메타데이터의 ID, 미확인은 null. run_id도 원문 보존. 입력 파일 그룹용 내부 ID를 실제 실험 ID라고 표시하지 않는다. |
| `data_origin` | `observed`, `synthetic`, `unknown`. 실제 수집에서 합성 문장을 사용한 경우 observed이며 내용이 실험용이었다는 사실을 별도 보존. |
| `representation` | `source_record`, `projection`, `summary`. 공개 파생본은 projection. 문서 요약은 자동 사건 입력에서 제외. |
| `limitations` | 문자열 배열. 원본 한계와 변환 시 발생한 누락·시각·식별자 제약을 보존. |

### 변환 및 Timeline 규칙

1. 원본 행은 추적 가능하게 유지하고 파싱 실패 파일·행, 시간대 누락, 누락 필드를 명시한다. 빈 입력·미수집·수집 실패·탐지 0건은 서로 다른 상태다. UTF-8 BOM이 있을 수 있는 PowerShell 출력도 고려한다.
2. 02는 한 스냅샷을 한 행으로 유지하고 세 시각을 모두 attributes에 둔다. 관측 시각이 없으므로 기본 `event_time=null`, `time_semantics=unknown`으로 ‘시각 미확정’ 표에 둔다. 사용자가 특정 메타데이터 시각 기준으로 볼 경우 별도 보조 보기에서 해당 의미를 명시한다. `phase=read`나 `accessUtc`를 `file_access/read_data`로 변환하지 않는다.
3. 03 방문은 `event_time_utc`를 사용한다. 04 원본 WMI는 원천 시각이 유효하면 그것을 사용하고 관측 시각도 보존한다. 원천 시각이 제거된 projected 자료는 관측 시각만 사용한다. 창 uptime·단조 시계 값을 임의로 UTC로 변환하지 않는다.
4. 타임라인은 UTC 값으로 정렬하고 동일 시각은 통합 ID로 안정 정렬한다. 이는 표시 순서이며 같은 시각의 인과 순서가 아니다. 원문 정밀도를 보존하고 Python의 마이크로초 정밀도보다 세밀한 값은 정밀도 손실을 표시한다. 시각 null은 날짜를 채우지 않고 별도 표에 둔다.
5. 기본 보기는 실험/입력 묶음별로 분리한다. 시간대 변환은 장치 시계 오차 보정이 아니다. 실험·장치·사용자 관계가 미확인인 자료를 상관분석에 자동 투입하지 않는다.
6. 동일 파일·행의 재입력은 중복 처리하되 서로 다른 출처의 같은 시각·PID 기록을 하나로 합치지 않는다. 프로세스 snapshot과 start, source_status와 행동 이벤트를 구분한다.

### 반드시 구분할 주장

| 관측 | 허용되는 설명 | 확정할 수 없는 설명 |
|---|---|---|
| 파일 메타데이터 | 해당 스냅샷의 생성·수정·접근 시각 값 | 특정 사용자가 내용을 읽음, 업로드함 |
| History 방문 | AI 도메인 방문 기록 | 질문 전송·파일 업로드·업무상 사용 |
| Clipboard 변경 | 상태 변경 및 조회된 형식 | 원문 출처·붙여넣기 횟수·전송 |
| DOM paste | 해당 origin에서 paste 이벤트 발생 | 입력 성공·특정 입력창·질문 전송 |
| 저장소 마커 | 해당 취득 자료에 문구 바이트 잔존 | 서버 전송 완료·최종 유효 대화 레코드 |
| 질문 전송 수동 사례 | 기존 화면 관측과 그 증거 범위 | 현재 자동 프로그램이 전송을 탐지했다는 주장 |
| 파일 선택/추정 접근 | 선택 또는 주변 정황 | 업로드 성공. 현재 성공 검증 자료 없음 |
| DNS/TCP | 캐시 또는 연결 관측·접근 후보 | 실제 방문 탭·요청 본문·전송 성공 |

## 6. 통합 프로그램의 최소 구조

Python + Streamlit 단일 로컬 실행으로 충분하다. 목록·표·필터를 중심으로 구성하고 별도 그래프 엔진은 필요 없다. SQLite 저장소, FastAPI, React, 별도 API 서버, 실시간 중앙 관제는 도입하지 않는다. Streamlit 자체의 로컬 실행만 사용한다.

```text
기존 JSON / JSONL
  → 출처별 형식 확인·정규화
  → 실험별 Timeline + 시각 미확정 자료 + 수집 상태
  → [합성 규칙 시연 선택 시] 기존 01 analyze()
  → 규칙 결과 + 근거 이벤트 + 판단 한계
```

다음 단계의 파일 구성은 `integration/app.py`(화면), `integration/adapters.py`(입력·정규화), `integration/analysis.py`(기존 규칙 호출 경계) 정도면 충분하다. 공통 스키마는 dict로 시작하고 불필요한 프레임워크나 데이터 계층은 만들지 않는다. 기존 연구 코드는 그대로 참조한다. 이는 제안이며 이번 단계에 해당 파일을 만들지 않았다.

화면은 입력/출처·실험 선택, 시간순 표, 선택 이벤트의 원본 위치·내용·한계, 규칙 결과와 근거 표로 한정한다. 실측·합성·파생본 표기를 항상 보인다. ‘자료 없음’과 ‘규칙 적용 불가’를 정상 결과와 구분한다. 원본 로그를 자동 저장하거나 외부로 보내지 않는다.

### 기존 규칙을 재사용하는 경계

[analyze.py](research/01_detection/poc/analyze.py)는 실측 입력을 명시적으로 거부하며 결과에도 `synthetic=true`를 고정한다. 연구용 정책은 `AI-DEMO=unapproved`, `AI-OK=approved`, 그 외 unknown이고 적용 시작은 2026-11-01 UTC다. 실제 ChatGPT를 AI-DEMO로 바꾸거나 실제 로그에 synthetic=true를 붙여 우회해서는 안 된다.

최소 구현에서는 **실측/파생본 Timeline 보기와 합성 규칙 시연을 분리**한다. 01 샘플을 그대로 기존 분석기에 전달하고 R01(미승인 방문), R02(읽기 후 방문 정황), R03(반복 방문), R04(정책 미확인), R05(사용자 누락) 결과를 보여준다. 판단 수준은 확률이 아니다. 같은 근거가 여러 규칙에 포함되므로 alert 수를 독립 행위 수로 세지 않는다.

실측 규칙 적용은 STEP 2의 기본 완료 조건이 아니다. 추후 필요할 때만 기존 연구 폴더 밖에서 실측용 입력 경계·정책 설정·출력 표기를 별도로 조정해야 한다. 특히 실제 파일 읽기 근거, 식별자, 같은 실험의 방문이 없으면 R02를 적용하지 않는다. 메타데이터·paste·TCP를 기존 규칙에 맞추기 위해 다른 사건 유형으로 치환하지 않는다.

브라우저 History는 원래 SQLite 형식이지만 새 통합 저장소로 SQLite를 도입하는 것과 다르다. 이번 최소 프로그램은 기존 `analyze_history.py`로 미리 추출한 JSON만 불러오므로 직접 DB 열기조차 필요 없다.

## 7. 기술적 한계와 공개 증거의 범위

- 공통 실험 ID·시계 동기화·사용자/장치 매핑이 없는 독립 연구 자료다. 전체 흐름의 종단 간 검증이나 실제 탐지율·오탐률은 제시할 수 없다.
- 02 접근 시각은 설정·접근 방식의 영향을 받으며 `usnProbe`의 Reason은 0이다. 삭제 후 부재와 USN FileDelete 또는 MFT 삭제 레코드 확인은 다르다.
- 03 History 분석기의 합성 검증 성공과 실프로필 수집 성공은 다르다. live read는 비원자적이며 일부 잠금·크기 제한이 있다. 저장소 마커는 미전송 상태에서도 남았고 업로드는 미완료다.
- 04 공개 자료는 장치/SID·창·일부 시간 정보가 제거되어 원본 수준의 연결이 불가능하다. 창/탭 정량 대조와 장시간 부하·무손실은 미검증이다. 원문 미수집으로 파일 내용→Clipboard→paste의 동일성도 확인할 수 없다.
- 05는 캐시 및 Established TCP 스냅샷의 최초 관측이다. 짧은 연결·UDP/QUIC 등은 이 TCP 수집 범위에 없다. 공용 CDN IP, DNS 누락, PID 재사용, 도메인 캐시 갱신은 오연결·누락 원인이 될 수 있다. IP 5개 목록은 사후 분석이고 세 IP는 도메인 근거 없이 추정했다. 고정 목록을 자동 탐지 규칙으로 추가하지 않는다.
- 해시 일치는 파일 식별·변경 검사 근거이며 사건의 진실성이나 완전성을 인증하지 않는다. 원본이 없는 경우 manifest의 원본 해시를 독립 검증했다고 표시하지 않는다.
- 기존 03 probe JSON에는 로컬 프로필 경로·다른 사이트 경로가 포함되어 있다. 이번 문서에 재전재하지 않는다. 기존 파일의 존재를 공개 적합성 보증으로 간주하지 않는다. 새 실측 로그·History·ETL·HAR·전체 화면은 저장소에 추가하지 않고, 필요한 공유본만 별도 검토한다.

## 8. STEP 1 확인 결과와 STEP 2 계획

### 이번 단계의 확인

2026-11-27 로컬 Python 3.14.6에서 기존 `test_analyze.py` 7개 테스트와 `selftest.py` 6개 검사를 재실행해 통과했다. 후자는 SQLite 3.53.4의 임시 합성 DB 검사다. `PYTHONDONTWRITEBYTECODE=1`로 실행했고 연구 파일에 결과를 덮어쓰지 않았다. Windows/.NET·PowerShell·Chrome 확장·실제 AI 서비스 실험은 재실행하지 않았다. 기존 결과 보고와 이번 재실행 범위는 구분한다.

### STEP 2의 짧은 구현 순서

1. **입력과 정규화:** 현재 있는 01 샘플, 02 관측 JSON, 04 공개 JSONL을 지원한다. 원본 스키마와 projected 스키마를 구분하고 출처·데이터 성격·null 보존을 먼저 확인한다.
2. **Timeline 화면:** 실험별 정렬, 시각 미확정 표, 수집 상태/오류, 이벤트 상세와 원본 locator를 구현한다. 활성 창·History·DNS/TCP는 기존 검토 자료가 없으면 자료 없음으로 표시한다. 제공된 경우에만 위 코드 스키마에 맞는 어댑터를 연결한다.
3. **기존 규칙 시연:** 01 샘플에 기존 분석기를 호출해 R01 3건/R02 1건/R05 1건과 근거 ID를 표시한다. 실측 자료에는 적용 불가 이유를 표시하고 합성 입력과 섞지 않는다.
4. **소규모 확인:** UTC offset 변환, 시각 null 보존, 서로 다른 실험의 분리, 원본 locator, 상태 행과 행동 건수 구분, 실제 자료의 합성 규칙 입력 차단을 점검한다. 기존 테스트·기본 출력과 회귀 비교하고 실행 안내를 추가한다.

STEP 2 완료 기준은 **기존 자료를 정직하게 불러와 시간·출처·판단 한계와 함께 보여주고 기존 합성 규칙의 결과를 재현하는 것**이다. 자료 확보를 위해 새 수집기나 업로드 탐지 기능을 만드는 것은 범위에 포함하지 않는다. 최종 보고서는 이 문서에 실제 구현·확인 결과만 보충하면 된다.
