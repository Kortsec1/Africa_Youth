# 사용 시나리오 및 기록 기준

## 실험 매트릭스

각 행을 ChatGPT/Claude/Gemini × Chrome/Edge × 3회로 반복한다. 미지원 기능은 N/A와 이유를 기록한다. 일반/시크릿은 별도 프로필 조건과 수집 시점으로 구분한다. 계정 한도·서비스 오류는 음성 결과가 아니라 실행 실패다.

| ID | 행위 | 대조/검증 질문 | 주요 분석 후보 |
|---|---|---|---|
| S00 | 브라우저만 실행, AI 미접속 | 기준 오탐 존재 여부 | History, 캐시, 프로세스 |
| S01 | 서비스 첫 화면 방문, 질문 없음 | 접속과 질문 구분 | History/세션 |
| S02 | 마커 질문 입력 후 전송 안 함 | 입력 흔적을 전송으로 오인하는가 | origin 저장소/캐시 |
| S03 | 고유 마커 질문 전송·응답 수신 | 마커 복구 여부와 위치 | History, 저장소/응답 후보 |
| S04 | 합성 파일 선택 후 전송 전에 취소 | 파일 선택을 업로드로 오인하는가 | 파일 대화상자, 저장소 |
| S05 | 합성 파일 업로드 성공 후 내용 질문 | 완료 응답과 파일 내용 마커 연결 | 로컬 경로/파일 해시, UI, origin 저장소 |
| S06 | 업로드 실패/서비스 거절 | 실패를 성공으로 오인하는가 | 오류 화면·통신 메타데이터 |
| S07 | 시크릿에서 S03/S05, 모든 시크릿 창 종료 | 일반 모드 대비 잔존 차이 | 종료 전/후 수집 분리 |
| S08 | 전용 실험 프로필의 방문기록 삭제 후 재수집 | 삭제 항목별 잔존·미검출 | History/저장소/파일 |
| S09 | AI와 무관한 페이지에서 동일 파일 선택 | 시간 근접 기반 오연결 여부 | 파일 대화상자, 방문 기록 |
| S10 | AI 출력 파일 다운로드 | 다운로드와 업로드 분리 | downloads/파일/ADS |

S06은 실험 VM의 제한된 테스트 조건에서만 재현한다. 네트워크 보안 설정을 끄는 작업은 포함하지 않는다. S08은 사용자가 명시적으로 실험용으로 지정한 프로필에서만 수행하고 삭제 옵션/기간을 기록한다.

## 실행별 필수 기록

```text
case_id / scenario_id / run_id:
operator / tool_version / collection_method:
Windows build / browser version / profile path / login / service model:
timezone / clock synchronization / UTC offset:
prompt_marker / filename_marker / content_marker:
upload_file_sha256:
action_started_utc / action_finished_utc:
UI outcome (unsent / canceled / success / failure / unsupported):
T0 / T1 / T2 / T3 collection ids and hashes:
artifact path / parser version / record id or offset:
observed data (redacted) / timestamp semantics:
claim supported / alternative explanation / limitation:
status (executed / failed / not-run / N/A):
```

`not-run`은 `not-found`와 다르다. 미검출은 도구가 정상 동작했고 대상/기간/프로필을 확인했을 때만 기록한다. 동기화가 켜진 프로필은 다른 기기 방문 유입 가능성을 별도 기록한다. 종료 후 수집만으로 실행 중 메모리 잔존을 판단하지 않는다.

## 측정 및 완료 조건

- 마커 복구: 성공/시도 횟수와 원본 레코드 위치. 질문 내용/파일명/파일 본문을 나눠 집계한다.
- 접근 탐지: S01/S03의 방문 식별과 S00의 오탐을 구분한다.
- 전송·업로드 구분: S02/S04/S06/S09를 양성으로 잘못 판단한 건수를 집계한다.
- 조건별 잔존: T1/T2/T3와 일반/시크릿의 결과를 별도 표로 기록한다. 결측을 0으로 치환하지 않는다.
- 로그: 원본 해시·작업본·분석 명령·도구 버전·오류·마스킹 내역을 남긴다. 민감한 원본은 공개하지 않는다.
- 이슈 완료: 실제 서비스 실험, 증거 위치와 해시, 대조군 결과, 비교표와 한계, 원격 등록까지 확인해야 한다. 문서 파일 존재만으로 완료 처리하지 않는다.
