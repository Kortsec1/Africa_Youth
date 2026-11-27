# 연구 자료 조회 프로그램

기존 파일 메타데이터와 공유용 이벤트를 표로 보고, 기존 합성 데이터로 탐지 규칙을 실행하는 작은 Streamlit 프로그램이다. 실시간 수집이나 업로드 탐지 기능은 없다.

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

- **기존 자료 Timeline:** 왼쪽에서 실험 선택 → 표 확인 → 기록 상세에서 원본 필드·출처·한계 확인.
- **내 JSON/JSONL 불러오기:** 기존 수집기 출력 또는 History 분석 JSON을 한 파일씩 읽는다. 자료 성격은 제공자 표기이며 앱이 인증하지 않는다. 지원하지 않는 형식은 오류로 표시한다.
- **합성 규칙 시연:** 30/60/300초를 선택하고 R01~R05 결과와 근거 이벤트를 확인한다. 사용자가 올린 파일은 이 분석기로 전달하지 않는다.

파일 메타데이터는 관측 시각이 없어 별도 표에 표시한다. 생성·수정·접근 시각은 상세 원본에 있다. 서로 다른 실험을 합치지 않으며 실험 ID가 없는 자료는 해당 파일 단위로 본다. 실제 History·활성 창·DNS/TCP 입력의 연동은 원시 자료가 없어 실측 검증하지 않았다.

`app.py`는 화면, `adapters.py`는 형식 변환, `analysis.py`는 기존 규칙 호출을 맡는다. 새 DB나 API 서버 없이 메모리에서 처리한다. 원본 파일은 수정하거나 자동 저장하지 않는다. 민감한 로그를 저장소에 넣지 않는다.

## 확인 결과

2026-11-27, Python 3.14.6 / Streamlit 1.67.0에서 `python integration/check.py` 실행 통과.

기존 자료 6종, UTC 변환, 누락값·출처 보존, 잘못된 JSON·빈 입력 처리를 확인했다. Streamlit AppTest로 자료 메뉴와 합성 시연의 30/60/300초 선택을 확인했다. 기본 60초 결과는 기존 `output.json`과 일치했다(R01 3건, R02 1건, R05 1건).

이는 프로그램 기능 확인이며 브라우저 화면의 수동 육안 검사나 Windows 수집 실험을 다시 한 것은 아니다.
