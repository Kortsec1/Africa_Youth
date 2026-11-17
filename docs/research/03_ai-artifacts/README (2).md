# 실제 ChatGPT 사용 및 DB 바이트 증거

2026-11-16 Windows의 실행 중 Chrome에서 수행한 단일 실행이다. 합성 DB 테스트가 아니다. 입력 내용 자체는 개인정보 없는 실험용 마커다. 별도 초기화 VM이 아닌 기존 프로필이며 확장 프로그램이 활성화되어 있어 일반 환경 전체로 결과를 확대할 수 없다.

## 1. 수행과 관찰

| 단계 | 실제 행위/관측 | 증거 |
|---|---|---|
| S01 | ChatGPT 첫 화면 방문, 사이드바 숨김 | `screenshots/01-chatgpt-before.png` |
| S02 | `AIART-20261116-UNSENT-7D3F` 입력, 보내기 미클릭 | `screenshots/02-chatgpt-unsent.png` |
| S02 저장소 조사 | 당시 IndexedDB `000107.log`의 UTF-16LE 마커 8회 검출, 첫 파일 오프셋 3,471,428 | `02-unsent.json` |
| S03 | 다른 마커 `AIART-20261116-SENT-9A2C`로 입력을 교체하고 전송. 화면에서 마커 및 덧셈 답 42 응답 확인 | `screenshots/03-chatgpt-response.png` |
| DB 재검증 | 과거 `000107.log`는 사라져 동일 파일 재캡처 불가. 현재 `000111.ldb` 압축 블록에서 두 마커를 다시 복구 | `sst-marker-verification.json` |
| DB 증거 캡처 | 실제 `.ldb`에서 디코딩한 블록을 010 Editor로 열어 미전송 마커 52바이트 선택 후 캡처 | `screenshots/04-db-unsent-hex-crop.png` |
| History | 실행 중 DB 잠금으로 읽기 실패 | `01-before.json`, `02-unsent.json`, `03-sent.json` |
| 파일 업로드 | 파일 추가 메뉴까지 접근했으나 컴퓨터 제어 중단. 성공 여부 미검증 | 업로드 성공으로 집계하지 않음 |

첫 문구는 전송하지 않고 두 번째 문구로 교체했다. 따라서 미전송 문구도 로컬 저장소에 잔존할 수 있다는 대조 관측이다. 마커 출현 횟수는 DB 중복/과거 버전/재기록의 영향을 받을 수 있으므로 질문 횟수나 전송 횟수로 해석하지 않는다.

## 2. DB 캡처의 출처

원본 경로 후보:

```text
%LOCALAPPDATA%\Google\Chrome\User Data\Default\IndexedDB\
https_chatgpt.com_0.indexeddb.leveldb\000111.ldb
```

| 항목 | 확인 값 |
|---|---|
| SST 원본 크기 | 1,941,272 bytes |
| SST SHA-256 | `adb42d2b488e09eeb6dba2de07ece14d7def087ec2db1c02a655e65d145b0fc7` |
| 압축 블록의 SST 파일 시작 오프셋 | 19,019 decimal |
| 압축 블록 길이 | 17,355 bytes (trailer 별도) |
| 압축 | Snappy, type 1 |
| 블록 CRC32C | 검증 통과 |
| 압축 해제 블록 크기 | 37,976 bytes |
| 해제 블록 SHA-256 | `c15d764a31b4dfb435b0227d914ed6d22131012c8e0213f38c93cf222fd54f27` |
| 문구 시작 위치 | 해제 블록 내 8,902 decimal = `0x22C6` |
| 선택 길이 | 52 bytes = `0x34` |
| 해석 | UTF-16LE, `AIART-20261116-UNSENT-7D3F` |

**`0x22C6`는 압축 해제된 블록 내 위치이며 `.ldb` 원본의 직접 오프셋이 아니다.** 캡처에 열린 파일은 원본 SST에서 추출·압축 해제한 `000111-block-19019-decoded.bin`이다. 원본 `.log` 화면이나 IndexedDB 논리 레코드 뷰어 화면으로 표시하지 않는다.

![실제 DB 압축 해제 블록에서 선택한 미전송 문구 바이트](screenshots/04-db-unsent-hex-crop.png)

캡처는 010 Editor의 실제 화면을 크롭만 했다. 보이는 값이나 강조 영역을 이미지에 새로 그리지 않았다. 전체 원본 화면에는 인접 프로필 식별자가 있으므로 공개용은 해당 문구와 근처 저장 구조 부분만 남겼다. 크롭 영역·스크린샷 해시는 `db-screenshot-provenance.json`에 기록했다. 공유 가능한 바이너리는 정확한 테스트 마커 52바이트를 추출한 `000111-block-19019-marker-excerpt.bin`이다. 원본 SST와 전체 디코딩 블록은 프로젝트 외부의 로컬 비공개 작업 경로에 보존했다.

## 3. 재검증과 한계

`scripts/inspect_sst_marker.py`는 SST footer/index의 블록 핸들을 읽고, 블록 trailer의 masked CRC32C를 검증한 뒤 Snappy를 해제해 마커를 찾는다. 원본 파일 해시가 같은 사본에서 반복 실행하면 같은 해제 블록 위치를 얻는다. Literal 및 overlapping copy의 최소 Snappy 검사도 실행했다. 완전한 IndexedDB 파서 검증을 의미하지 않는다.

이 도구는 IndexedDB 키/값 의미, LevelDB 시퀀스와 삭제 상태, 최종 유효 레코드를 판정하지 않는다. 주변 바이트에 draft 관련 문자열이 보이더라도 그것만으로 정확한 객체/필드 의미를 확정하지 않는다. 이번 캡처는 저장소 바이트 잔존 증거이며 서버 전송 증거는 아니다.

`live_probe.py`는 실행 중 파일을 순차 읽은 결과다. 원자적 스냅샷이 아니고 일부 파일은 잠금/크기 제한으로 읽지 못했다. 실험 전 검사에서는 마커가 0건, 미전송 검사에서는 1개 파일에서 검출되었지만 전체 디스크의 부재/존재 판정을 의미하지 않는다. 당시 History 조회 시작시각 인자도 잘못 지정되어 있었다. History 조회는 모두 잠금 단계에서 실패했으며 방문 결과를 산출하지 않았다. 해당 인자는 수정해 재실험해야 한다.

새 DB 증거 확보 과정에서 기존 로그를 사전에 원본 보존하지 않은 한계가 확인됐다. 따라서 새 `.ldb` 취득 결과를 과거 `.log`의 동일 해시 증거로 대체하지 않고 별도 취득으로 구분했다. 별도 VM·브라우저 버전 고정·확장 비활성 조건과 3회 반복, 종료 후 잔존 비교는 남아 있다.

## 4. 전송 후 응답 수신 시나리오 DB 캡처 추가

전송한 질문의 식별 문구 `AIART-20261116-SENT-9A2C`도 보존한 원본 SST 사본에서 재검증하고 010 Editor 화면으로 캡처했다.

| 항목 | 값 |
|---|---|
| 원본 | 앞 절과 동일 해시의 `000111.ldb` |
| SST 압축 블록 위치 | 1,212 decimal |
| 압축 길이 | 17,802 bytes, Snappy type 1 |
| 블록 무결성 | masked CRC32C 통과 |
| 해제 블록의 문구 위치 | 10,234 = `0x27FA` |
| 선택 범위 | `0x27FA`~`0x2829`, 48 bytes |
| 인코딩 | UTF-16LE |

![전송한 질문 문구의 DB 잔존 바이트](screenshots/05-db-sent-hex-crop.png)

![질문 전송 후 응답 수신 화면](screenshots/03-chatgpt-response.png)

첫 그림은 질문에 사용한 마커의 DB 잔존을 보여주고, 두 번째 그림은 해당 질문 전송 후 응답 수신을 보여준다. DB 바이트만으로 전송 여부를 판정하지 않는다. 특히 캡처 근처에 draft 관련 문자열이 존재하므로 이 바이트를 서버 전송 완료 레코드나 AI 응답 본문으로 부르지 않는다. AI 응답 본문의 디스크 잔존 여부는 이번 캡처로 검증하지 않았다. 원본 해시·해제 블록 해시·캡처 크롭 범위는 `db-sent-screenshot-provenance.json`에 기록했다.
