# Windows 생성형 AI 서비스 사용 아티팩트 조사

관련 이슈: [#5](https://github.com/Kortsec1/Africa_Youth/issues/5). 조사일: 2026-11-16.

**상태: 실제 ChatGPT의 접속·미전송 입력·질문 전송을 단일 실행하고 IndexedDB의 마커 잔존을 확인했다.** [실측 결과와 DB 캡처](evidence/live-20261116/README.md)에 원본 해시·압축 블록 위치·복구 바이트를 기록했다. 전체 서비스/브라우저 반복 비교와 업로드·종료 후 실험은 미완료다. 합성 데이터 검증은 별도로 구분한다. 사용자가 제공한 전체 프로젝트에서 기존 README/results가 목차 상태임을 확인하고 이 작업본에 반영했다. 원본 위치는 `C:\Users\PC\Downloads\Africa_Youth-main\Africa_Youth-main`이다. 커밋·push·PR은 사용자 지시에 따라 수행하지 않는다.

## 1. 연구 목표와 범위

Windows에서 ChatGPT·Claude·Gemini 웹 사용 후 남는 흔적을 통해 (1) 서비스 접근, (2) 질문 입력/전송, (3) 파일 선택/업로드를 어디까지 입증할 수 있는지 검증한다. 프로젝트의 최종 목표인 사용자 행위 Timeline에 증거와 한계를 함께 전달한다.

우선 Chrome/Edge 일반 모드, 이후 시크릿/InPrivate, 종료·재시작, 기록 삭제를 비교한다. 데스크톱 앱은 별도 패키지/저장 경로 조사 대상으로 남긴다. API 사용·모바일·다른 PC 활동은 이번 범위 밖이다. 이 문서의 저장소 후보는 조사 가설이며 특정 서비스가 질문 전문을 반드시 저장한다는 뜻이 아니다.

## 2. 기술 조사

### 2.1 수집 위치와 증거 해석

`<profile>`은 실행 중 브라우저의 버전 페이지에서 확인한다. Chrome 기본 사용자 데이터 루트는 `%LOCALAPPDATA%\Google\Chrome\User Data`, 프로필은 `Default`, `Profile 1` 등이다 [S1]. Edge는 `%LOCALAPPDATA%\Microsoft\Edge\User Data`를 후보로 두되 실제 경로를 확인한다. 경로만으로 프로필 사용자를 확정하지 않는다.

| 아티팩트 후보 | 확인할 데이터 | 입증 가능한 범위 | 입증하지 못하는 내용/주의 |
|---|---|---|---|
| `<profile>\History` SQLite | `urls`와 `visits`의 개별 방문, URL·제목·방문시각 | 해당 프로필에 서비스 방문 기록 존재 | 질문 전송·사용자 신원·업로드 성공. 동기화/리다이렉트도 고려 |
| `History-wal`, `History-shm` | 미체크포인트 변경 및 공유 상태 | 본 DB에 없는 최신 기록 보완 가능 [S2] | DB만 복사하면 누락 가능. 실행 중 순차 복사는 일관성 보장 불가 |
| `Cache\Cache_Data`, `Code Cache`, Service Worker | 응답/리소스/스크립트 후보 | 서비스 리소스 이용 정황, 마커 잔존 가능성 | 정적 JS는 대화 증거가 아님. 압축·eviction·No-store 등으로 본문 없을 수 있음 |
| `Local Storage\leveldb`, `Session Storage` | origin, 키/값, 로그/SST 후보 | 사이트 상태 또는 입력 마커 후보 | 토큰·설정일 수 있음. 문자열 hit만으로 전송 판단 불가 |
| `IndexedDB`, `Service Worker\Database` | 서비스 origin 저장소 후보 | 객체·파일 메타데이터 잔존 가능성 | 서비스/버전에 따라 구조가 다름. 존재·내용 모두 실험 필요 |
| `Sessions` | 탭 URL·세션 복원 후보 | 열린 페이지 정황 | 대화 내용/행위시각의 완전한 기록 아님 |
| `Network\Cookies` | origin, 생성/접근시각 후보 | 사이트 상태와 세션 존재 보조 | 쿠키만으로 로그인 완료·질문·실사용 판단 불가. 값은 수집/공유에서 제외 |
| `History` 다운로드 테이블, 다운로드 파일, Zone.Identifier | 파일 경로·시각·출처 후보 | 다운로드 정황 | 다운로드는 업로드 증거가 아님. ADS 생성은 환경에 따라 다름 |
| `NTUSER.DAT` 내 ComDlg32/OpenSavePidlMRU 후보 | 파일 대화상자 경로 | 파일 선택 정황 | 웹 전송 성공 아님. 취소·실패와 대조 필요 |
| Recent LNK, JumpList | 파일/앱 접근 후보 | 로컬 파일 취급 정황 | AI 서비스로 이동했는지 단독 판단 불가 |
| `$MFT`, `$UsnJrnl` | 생성/수정·파일 식별자 | 파일 시스템 변화 | 파일 읽기는 USN 변경을 반드시 발생시키지 않음. 업로드 단정 금지 |
| Clipboard/Foreground/Process 수집 [04 연구 연계] | 실행 중 관찰한 복사·포커스·프로세스 | 해당 시점의 행위 정황 | Windows 기본 사후 로그처럼 취급하지 않음. 복사 ≠ 붙여넣기 ≠ 전송 |
| DNS/TLS 메타데이터 [05 연구 연계] | 도메인·연결시각 | 네트워크 접속 보조 | 암호화된 질문/파일 본문·업로드 완료 입증 불가 |

### 2.2 서비스별 조사 가설

| 서비스 | 시작 도메인 후보 | 우선 확인 | 현재 검증 상태 |
|---|---|---|---|
| ChatGPT | `chatgpt.com`, 과거 `chat.openai.com` | 방문 URL, 대화 경로, 질문/파일 마커의 origin 저장소 잔존 | 실험 미실행 |
| Claude | `claude.ai` | 동일 행위와 저장소를 같은 조건으로 비교 | 실험 미실행 |
| Gemini | `gemini.google.com` | Google 인증·정적 리소스와 실제 대화 행위 구분 | 실험 미실행 |

위 도메인 목록은 완전한 통신 allowlist가 아니다. 로그인·CDN 도메인만으로 서비스 사용을 판정하지 않는다. 질문을 POST/스트리밍으로 전송하는 경우 URL History만으로 본문이 복구된다고 가정할 수 없다. 실제 전송 방식·origin·응답 구조는 매 실행에서 관찰한다.

### 2.3 입증 단계

| 단계 | 최소 근거 | 허용 결론 |
|---|---|---|
| A 접근 | 서비스 host에 대한 방문 레코드/네트워크 증거 | 서비스 접근 기록 존재 |
| B 내용 잔존 | 독립 마커가 있는 원본 레코드, 출처·offset/키·해시 | 특정 문자열이 해당 저장소에 잔존 |
| C 전송 정황 | 시간·서비스·프로필이 연결된 UI/통신 기록, 응답 | 입력/전송 행위 정황. 화면 관찰과 디스크 증거는 구분 |
| D 업로드 확인 | 통제 실험에서 파일 식별자/내용 마커, 완료 응답/서비스 확인, 연결된 로컬 증거 | 해당 실행의 업로드 성공. 파일 선택 흔적만으로 승격하지 않음 |

파일명은 재사용할 수 있으므로 파일명 일치보다 파일 SHA-256·내용 마커·서비스 응답을 함께 확인한다. 근접 시각만으로 자동 결합하지 않는다. 취소/실패/다른 사이트 업로드 대조군을 반드시 포함한다.

## 3. 재현 절차

1. 폐기 가능한 Windows VM/전용 브라우저 프로필을 준비한다. 개인 실사용 프로필과 분리한다. OS 빌드, 브라우저 버전, 프로필 경로, 서비스/모델 표기, 로그인 여부, 시계/시간대, 수집 도구 버전을 기록한다.
2. 각 시나리오마다 같은 깨끗한 기준 스냅샷에서 시작한다. 원격 계정의 기존 대화가 자동으로 로드될 수 있으므로 실행별 고유 마커를 사용한다. 반복 3회, 실행별 별도 폴더를 만든다.
3. `AIART-<service>-<scenario>-<run>-<random>` 마커를 질문에 사용한다. 파일은 동일 ID의 합성 TXT만 생성하고 파일명·본문에 서로 다른 마커를 넣는다. 전송 전 파일 SHA-256을 기록한다. 개인정보/실제 업무 문서는 사용하지 않는다.
4. T0(행위 전), T1(직후 실행 중), T2(정상 종료 후), T3(재시작 후)를 구분한다. 시각은 ISO 8601 UTC로 기록하고 로컬 UTC offset도 남긴다. 동작·응답·취소/오류 화면은 원본 시각과 함께 보존한다.
5. T1은 VM/볼륨의 일관된 스냅샷 등 적절한 수집 절차를 별도로 적용한다. 실행 중 파일을 단순 순차 복사한 결과는 일관된 이미지로 표시하지 않는다. 정상 종료는 메모리/세션 상태를 바꾸므로 T1 대체가 아니다.
6. 제공 `collect.ps1`은 브라우저가 닫힌 **전용 실험 프로필**의 선정 아티팩트를 복사하는 T0/T2/T3 보조 도구다. 실행 중 사용하면 실패하도록 한다. 원본과 복사본 SHA-256, 누락·오류를 manifest에 남긴다. 완전한 포렌식 이미징 도구가 아니다.
7. 보존본을 별도 보관하고 분석용 복사본의 History를 `analyze_history.py`로 읽는다. 도구는 방문만 출력하고 질문/업로드를 자동 추론하지 않는다. LevelDB/캐시/레지스트리는 별도 검증 가능한 파서로 분석하고 도구 버전, 레코드 위치, 마커 유무를 기록한다.
8. 단순 미검출은 미사용이 아니다. 수집 실패, 삭제, 저장 안 됨, 파서 미지원, 조사 범위 밖을 구별한다. 디스크 원본·HAR·쿠키·토큰은 공개 저장소에 올리지 않고 마스킹된 결과/합성 검증 자료만 등록한다.

```powershell
# 저장소 루트에서, 실험용 Chrome/Edge를 모두 정상 종료한 뒤 실행
.\docs\research\03_ai-artifacts\scripts\collect.ps1 -ProfilePath C:\AIArtLab\Chrome\Default -OutputPath C:\AIArtLab\evidence\S01-R1-T2
# 보존본과 분리한 작업 복사본의 History 지정. 출력 경로는 새 파일이어야 한다.
python .\docs\research\03_ai-artifacts\scripts\analyze_history.py --history C:\AIArtLab\working\History --output C:\AIArtLab\visits.json
```

## 4. 프로젝트 적용 가능성

현재 프로젝트의 [상관분석 PoC](../01_detection/poc/README.md)는 `event_id, occurred_at, device_id, user_id, process_entity_id, event_type, source, source_ref, synthetic, attributes`를 사용한다. 방문은 `event_type=ai_service_access`, `attributes.observation_kind=browser_visit`에 대응할 수 있다. 다만 `analyze.py`는 `synthetic is True`인 입력만 허용한다. 실제 추출 기록을 합성으로 바꾸어 억지로 넣지 않는다. 제공 History 분석기 출력은 독립 연구 형식으로 유지하며, 실데이터 수용과 정책 매핑은 별도 구현 과제다.

후속 연계 시 추가로 `case_id, run_id, time_semantics, record_id, profile_id, action_claim, evidence_level, evidence_hash, limitations`를 보존한다. 브라우저 방문시각과 파일 수정시각·수집시각을 다른 의미로 유지한다. SID/프로필/PID는 확보한 경우에만 연결한다. 프로필 경로만으로 user_id를 만들어내지 않는다. 04 endpoint 연구의 foreground·clipboard와 05 network 연구의 연결 정보를 독립 근거로 붙인다. 조직 승인 여부는 서비스 이름만으로 결정하지 않고 별도 정책으로 확인한다.

최우선 구현은 방문 Timeline과 증거 출처 표시다. 질문 복구·업로드 확정은 실제 실험 증거가 축적된 뒤 지원 여부를 결정한다. 신뢰도 수치나 탐지율은 측정 없이 부여하지 않는다.

## 5. 산출물

- [results.md](results.md): 수행 상태, 시나리오별 비교, 합성 검증 결과와 남은 작업
- [experiment-plan.md](experiment-plan.md): 대조군·측정 기준·실험 기록 양식
- [logs/analysis-log.md](logs/analysis-log.md): 실제 확인/실패 기록
- `scripts/`: 오프라인 수집·History 분석·합성 검증 도구
- `samples/`: 합성 검증 출력만. 실제 서비스 실험 자료와 혼동 금지

## 6. 참고 자료와 근거 범위

공식 문서를 2026-11-16 브라우저로 열어 확인했다. HEAD 문서는 변할 수 있으므로 재현 실험에서는 당시 버전/커밋도 고정해야 한다.

- [S1 Chromium User Data Directory](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md): Windows Chrome 기본 경로, 프로필 확인, 사용자 데이터 경로 재정의. 이 자료는 ChatGPT 질문 잔존을 입증하지 않는다.
- [S2 SQLite Write-Ahead Logging](https://sqlite.org/wal.html): 커밋 데이터가 WAL에 존재할 수 있으며 DB와 WAL을 함께 보존해야 하는 이유. 실제 브라우저 DB의 WAL 사용 여부는 수집본에서 확인한다.
- [S3 Chrome Incognito](https://support.google.com/chrome/answer/95464?hl=en): 시크릿 세션 종료 후 사이트 데이터/방문 기록 보존 제한과 다운로드 파일 잔존. 이를 Windows 전체 무흔적으로 확대 해석하지 않는다.

그 외 서비스별 저장 키, 레지스트리·캐시 경로와 잔존 내용은 이번 작업에서 공식 명세로 확정하지 못한 **실험 후보**다.
