"""Evidence review for one operator-confirmed, observed experiment."""

from bisect import bisect_left
from datetime import datetime, timedelta

import streamlit as st

from adapters import load_events


HOSTS = {
    'chatgpt.com': 'ChatGPT',
    'chat.openai.com': 'ChatGPT',
    'claude.ai': 'Claude',
    'gemini.google.com': 'Gemini',
}


def event_signal(event):
    row = event['attributes']
    kind = event['event_type']
    source = event['source']
    if (
        source == 'chrome_paste_observer' and kind == 'paste_event'
        and row.get('origin') == 'https://chatgpt.com'
        and row.get('trusted') is True and row.get('target_editable') is True
        and row.get('payload_collected') is False
    ):
        return 'ChatGPT', '편집 가능한 요소에 붙여넣기'
    if (source == 'browser_history' and kind == 'browser_visit'
            and row.get('action_claim') == 'service_visit_record'):
        host = row.get('host')
        return HOSTS.get(host) if isinstance(host, str) else None, '브라우저 방문'
    if kind == 'dns_cache_observation':
        return None, 'DNS 캐시 관측'
    if kind == 'tcp_connection_observation':
        return None, 'TCP 연결 관측'
    return None, kind


def review(events, unapproved, seconds):
    observed = {e['event_id']: e for e in events if e['data_origin'] == 'observed'}
    ordered = sorted(observed.values(), key=lambda e: e['event_time'] or '', reverse=True)
    clipboard = sorted(
        (datetime.fromisoformat(e['event_time']), e['event_id'])
        for e in ordered
        if e['source'] == 'windows_collector' and e['event_type'] == 'clipboard_update' and e['event_time']
    )
    clipboard_times = [time for time, _ in clipboard]
    findings = []
    for event in ordered:
        service, signal = event_signal(event)
        if service not in unapproved or not event['event_time']:
            continue
        evidence = [event]
        label = '미승인 AI 방문 정황'
        if event['event_type'] == 'paste_event':
            label = '미승인 AI 붙여넣기 관측'
            when = datetime.fromisoformat(event['event_time'])
            previous = bisect_left(clipboard_times, when) - 1
            if previous >= 0 and when - clipboard_times[previous] <= timedelta(seconds=seconds):
                evidence.append(observed[clipboard[previous][1]])
                label = 'Clipboard 변경 후 미승인 AI 붙여넣기 정황'
        findings.append((service, label, signal, evidence))
    return ordered, findings


def evidence_row(event):
    service, signal = event_signal(event)
    signal = {
        'clipboard_update': 'Clipboard 변경',
        'process_observation': '프로세스 상태 변경',
        'process_start': '프로세스 시작',
        'process_stop': '프로세스 종료',
        'file_metadata_snapshot': '파일 메타데이터 스냅샷',
        'file_metadata_observation': '파일 메타데이터 변경',
    }.get(signal, signal)
    ref = event['source_ref']
    return {
        '시각 (UTC)': event['event_time'] or '시각 미확정',
        '기록': signal,
        'AI 서비스': service or '—',
        '자료 형태': '공유용 파생본' if event['representation'] == 'projection' else '관측 기록',
        '출처': f"{ref['file']} · {ref['locator']}",
    }


def show_detection():
    st.subheader('Shadow AI 의심 동작 탐지')
    st.write('같은 테스트에서 수집한 로그를 모아 미승인 AI 방문과 붙여넣기 정황을 확인합니다.')
    uploads = st.file_uploader('관측 로그 추가', type=['json', 'jsonl'], accept_multiple_files=True,
                               help='같은 실험의 Windows·Chrome·History·DNS/TCP JSON 또는 JSONL을 선택하세요.')
    unapproved = st.multiselect('이 테스트의 미승인 AI 서비스', sorted(set(HOSTS.values())))
    seconds = st.selectbox('Clipboard 변경과 붙여넣기 사이의 최대 시간 (초)', [30, 60, 300], index=1)
    confirmed = st.checkbox('이 파일들은 같은 PC·사용자·실험에서 수집했습니다.')
    if not uploads or not confirmed:
        st.info('같은 실험의 로그를 추가하고 수집 범위를 확인하세요.')
        return

    events = []
    for uploaded in uploads:
        try:
            batch = load_events(uploaded.getvalue(), uploaded.name, 'observed')
            run_ids = {e['experiment_id'] for e in batch if isinstance(e['experiment_id'], str)}
            if len(run_ids) > 1:
                raise ValueError('한 파일에는 같은 실행의 로그만 넣어 주세요.')
            if any(e['data_origin'] != 'observed' for e in batch):
                raise ValueError('실측 분석에는 관측 로그만 사용할 수 있습니다.')
        except (ValueError, TypeError) as error:
            st.error(f'{uploaded.name} · {error}')
            return
        events.extend(batch)

    ordered, findings = review(events, set(unapproved), seconds)
    st.subheader('탐지 결과')
    if not unapproved:
        st.info('미승인 AI 서비스를 지정하면 정책 기준으로 정황을 표시합니다.')
    elif not findings:
        st.info('입력한 자료에서 정책에 해당하는 방문·붙여넣기 근거를 찾지 못했습니다.')
    for service, label, signal, evidence in findings:
        with st.expander(f"{label} · {service} · {evidence[0]['event_time']}"):
            st.write(signal)
            st.table([evidence_row(event) for event in evidence])
    st.caption('Clipboard 연결은 시각상 인접한 기록입니다. 내용 일치, 전송·업로드 성공은 이 자료로 판정할 수 없습니다.')
    st.subheader('전체 증거')
    if ordered:
        st.dataframe([evidence_row(event) for event in ordered], hide_index=True, width='stretch')
        st.caption('파일 메타데이터·프로세스·DNS/TCP는 조사 맥락으로 표시합니다. DNS 캐시와 TCP만으로 AI 서비스 방문을 판정하지 않습니다.')
    else:
        st.info('표시할 관측 기록이 없습니다.')
