# 연구 자료 조회 프로그램

Windows에서 직접 만든 변경을 관찰하고, 기존 연구 자료와 합성 탐지 규칙도 살펴볼 수 있는 Streamlit 프로그램이다.

## 실행

저장소 루트에서 실행한다. Python 3.10 이상이 필요하다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r integration/requirements.txt
python -m streamlit run integration/app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Windows에서는 활성화 명령을 `.venv\Scripts\Activate.ps1`로 바꾼다.

## 사용

- **내 PC 실시간:** 앱을 `--server.address 127.0.0.1`로 실행한다. 관찰 대상을 지정하고 **관찰 시작**을 누른 뒤, 더미 텍스트를 복사하거나 메모장을 열고 닫거나 지정한 테스트 파일을 저장한다. 약 2초마다 Clipboard 변경, 지정한 프로세스 PID의 등장·사라짐, 파일 크기·수정 시각 변화를 확인한다. 표의 시각은 PC의 관찰 시각이다. 두 확인 사이에 나타났다 사라진 변경은 놓칠 수 있다. Clipboard 내용은 읽지 않고, 기록은 세션 메모리에만 보관한다. 다른 메뉴로 이동하면 관찰이 중지된다.
- **기존 연구 자료:** 자료 선택 → 표 확인 → 기록 상세에서 원본 필드·출처·한계 확인.
- **내 JSON/JSONL 불러오기:** 기존 수집기 출력 또는 History 분석 JSON을 한 파일씩 읽는다. 자료 성격은 제공자 표기이며 앱이 인증하지 않는다. 지원하지 않는 형식은 오류로 표시한다.
- **합성 규칙 시연:** 30/60/300초를 선택하고 R01~R05 결과와 근거 이벤트를 확인한다. 사용자가 올린 파일은 이 분석기로 전달하지 않는다.

파일 메타데이터는 관측 시각이 없어 별도 표에 표시한다. 생성·수정·접근 시각은 상세 원본에 있다. 서로 다른 실험을 합치지 않으며 실험 ID가 없는 자료는 해당 파일 단위로 본다. 실제 History·활성 창·DNS/TCP 입력의 연동은 원시 자료가 없어 실측 검증하지 않았다.

`app.py`는 화면, `adapters.py`는 형식 변환, `analysis.py`는 기존 규칙 호출을 맡는다. 새 DB나 API 서버 없이 메모리에서 처리한다. 원본 파일은 수정하거나 자동 저장하지 않는다. 민감한 로그를 저장소에 넣지 않는다.

## 확인 결과

2026-11-27, Python 3.14.6 / Streamlit 1.67.0에서 `python integration/check.py` 실행 통과.

기존 자료 6종, UTC 변환, 누락값·출처 보존, 잘못된 JSON·빈 입력 처리를 확인했다. Streamlit AppTest로 자료 메뉴와 합성 시연의 30/60/300초 선택을 확인했다. 기본 60초 결과는 기존 `output.json`과 일치했다(R01 3건, R02 1건, R05 1건).

이는 프로그램 기능 확인이며 브라우저 화면의 수동 육안 검사나 Windows 수집 실험을 다시 한 것은 아니다.

## Windows 설치·시간 변환 수정

Windows 사용자 환경에서 Streamlit 1.67.0 설치에 실패하고 1.65.0 설치에 성공한 기록에 따라 설치 버전을 1.65.0으로 맞췄다. 위의 1.67.0 검증 기록은 이전 실행 결과다.

Python 3.10의 시간 파싱 제한을 고려해 소수 초를 파싱할 때만 6자리로 맞춘다. 원본 시각은 그대로 보존한다. 소수 초 1~7자리의 UTC 변환과 원문 보존 검사를 추가했다. Windows에서 수정본의 검사 통과 여부는 별도로 확인해야 한다.

수정 후 macOS / Python 3.14.6 / Streamlit 1.65.0에서 `python integration/check.py`가 통과했다. Windows/Python 3.10 실행 결과와는 구분한다.
