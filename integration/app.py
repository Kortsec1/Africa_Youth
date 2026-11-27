"""실행: streamlit run integration/app.py"""
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from adapters import load_events
from analysis import ROOT, run_demo
from live import show_live

st.set_page_config(page_title='Shadow AI 연구 기록', layout='wide')
st.title('Shadow AI 연구 기록')

research = ROOT / 'docs/research'
samples = {
    '파일 메타데이터': research / '02_windows-forensics/samples/observations.json',
    'Clipboard — 복사 6회': research / '04_endpoint-telemetry/evidence/clipboard-six-copies.projected.jsonl',
    'Clipboard — 복사 1회·붙여넣기 3회': research / '04_endpoint-telemetry/evidence/copy-once-paste-three.projected.jsonl',
    '프로세스 시작·종료': research / '04_endpoint-telemetry/evidence/process-test.projected.jsonl',
    '웹 Paste — 붙여넣기': research / '04_endpoint-telemetry/evidence/web-paste-positive.projected.jsonl',
    '웹 Paste — 클릭만': research / '04_endpoint-telemetry/evidence/web-paste-negative.projected.jsonl',
}
mode = st.radio('보기', ['내 PC 실시간', '기존 연구 자료', '합성 규칙 시연'],
                horizontal=True, label_visibility='collapsed')
if mode != '내 PC 실시간' and st.session_state.get('live_running', False):
    st.session_state.live_ended = datetime.now(timezone.utc)
    st.session_state.live_running = False

if mode == '내 PC 실시간':
    show_live()
elif mode == '합성 규칙 시연':
    st.subheader('기존 상관분석 규칙')
    st.warning('합성 데이터 시연입니다. 실제 자료의 탐지율이나 업로드 성공을 뜻하지 않습니다.')
    window = st.selectbox('상관분석 시간 범위(초)', [30, 60, 300], index=1)
    result = run_demo(window)
    st.caption(f"정책: {result['policy_version']} · 결과 {len(result['alerts'])}건 (규칙 간 중복 포함)")
    st.dataframe([{'규칙': a['rule_id'], '판단': a['assessment_level'], '내용': a['description'], '근거 ID': ', '.join(a['evidence_ids'])} for a in result['alerts']], hide_index=True, width='stretch')
    by_id = {e['event_id']: e for e in result['events']}
    for index, alert in enumerate(result['alerts'], 1):
        with st.expander(f"{index}. {alert['rule_id']} — {alert['description']}"):
            st.write(alert['inference'] or '위 규칙 조건에 해당하는 기록입니다.')
            st.json([by_id[eid] for eid in alert['evidence_ids']])
    st.subheader('합성 입력 Timeline')
    st.json([by_id[eid] for eid in result['timeline']], expanded=False)
else:
    choice = st.selectbox('자료 선택', list(samples) + ['내 JSON/JSONL 불러오기'])
    origin = 'observed'
    if choice == '내 JSON/JSONL 불러오기':
        st.caption('파일은 이 로컬 앱에서 읽습니다. 원본 파일을 저장소에 복사하지 않습니다.')
        uploaded = st.file_uploader('연구 로그 1개', type=['json', 'jsonl'])
        origin = st.selectbox('자료 성격 (제공자 표기)', ['unknown', 'observed', 'synthetic'])
        if uploaded is None:
            st.info('기존 자료를 선택하거나 JSON/JSONL 파일을 불러오세요.')
            st.stop()
        raw, filename = uploaded.getvalue(), Path(uploaded.name).name
    else:
        path = samples[choice]
        raw, filename = path.read_bytes(), path.relative_to(ROOT).as_posix()
    try:
        events = load_events(raw, filename, origin)
    except (ValueError, UnicodeError) as exc:
        st.error(f'파일을 읽지 못했습니다: {exc}')
        st.stop()
    st.subheader(choice)
    st.caption('실측 자료에도 더미 파일·합성 문장을 사용했습니다. 공개 JSONL은 원시 로그의 일부 필드만 남긴 자료입니다.')
    if not events:
        st.info('입력 파일에 이벤트가 없습니다. 미수집이나 수집 실패 여부는 별도 확인이 필요합니다.')
        st.stop()
    groups = list(dict.fromkeys(e['experiment_id'] for e in events))
    group = st.selectbox('실험 / 실행', groups, format_func=lambda x: x or '실험 ID 없음 — 이 입력 파일만 표시')
    selected = [e for e in events if e['experiment_id'] == group]
    types = st.multiselect('이벤트 유형', sorted({e['event_type'] for e in selected}))
    if types:
        selected = [e for e in selected if e['event_type'] in types]
    def table(rows):
        return [{'시각 (UTC)': e['event_time'], '시간 의미': e['time_semantics'], '유형': e['event_type'], '자료 성격': e['data_origin'], '자료 형태': e['representation'], '원본 위치': e['source_ref']['locator']} for e in rows]
    timed = [e for e in selected if e['event_time']]
    untimed = [e for e in selected if not e['event_time']]
    st.write(f'선택한 기록 {len(selected)}건 · 시각 확인 {len(timed)}건 · 시각 미확정 {len(untimed)}건')
    st.caption('기록 수에는 수집 시작·종료·상태도 포함됩니다. 사용자 행동 횟수가 아닙니다.')
    if timed:
        st.dataframe(table(timed), hide_index=True, width='stretch')
    if untimed:
        st.write('시각 미확정 자료')
        st.dataframe(table(untimed), hide_index=True, width='stretch')
    if selected:
        index = st.selectbox('기록 상세', range(len(selected)), format_func=lambda i: f"{selected[i]['source_ref']['locator']} · {selected[i]['event_type']}")
        event = selected[index]
        for limitation in event['limitations']:
            st.caption(limitation)
        st.json(event, expanded=False)
    st.info('합성 데이터의 규칙 결과는 상단의 합성 규칙 시연에서 확인하세요.')
    with st.expander('현재 없는 자료와 해석 범위'):
        st.write('실제 History 방문 추출본, 활성 창 원시 로그, DNS/TCP 로그는 저장소에 없습니다. 기존 형식의 JSON/JSONL이 있으면 직접 불러올 수 있습니다. 방문·Clipboard 변경·paste·연결 기록만으로 질문 전송이나 파일 업로드를 확정하지 않습니다.')
