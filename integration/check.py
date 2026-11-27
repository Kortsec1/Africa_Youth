"""마지막 기능 확인: python integration/check.py"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
from streamlit.testing.v1 import AppTest
from adapters import load_events
from analysis import ROOT, run_demo
from detection import review
from live import browser_rows

research = ROOT / 'docs/research'
metadata = research / '02_windows-forensics/samples/observations.json'
events = load_events(metadata.read_bytes(), metadata.name, 'observed')
assert len(events) == 4 and all(e['event_time'] is None for e in events)
assert all(e['event_type'] == 'file_metadata_snapshot' for e in events)
counts = {}
for path in (research / '04_endpoint-telemetry/evidence').glob('*.projected.jsonl'):
    rows = load_events(path.read_bytes(), path.name, 'observed')
    counts[path.name] = len(rows)
    assert all(e['representation'] == 'projection' and e['device_id'] is None for e in rows)
    assert all(e['source_ref']['locator'].startswith('line:') for e in rows)
assert sorted(counts.values()) == [2, 2, 3, 4, 7]
process = research / '04_endpoint-telemetry/evidence/process-test.projected.jsonl'
rows = load_events(process.read_bytes(), process.name, 'observed')
assert rows[0]['event_time'] == '2026-10-26T15:53:10.567614+00:00'
assert rows[0]['data_origin'] == 'observed'
assert rows[0]['attributes']['data']['instance_identity_verified'] is False
try:
    load_events(b'{invalid}', 'bad.json')
except ValueError:
    pass
else:
    raise AssertionError('잘못된 JSON을 거부하지 않음')
assert load_events(b'', 'empty.jsonl') == []
fixture = [{'type': 'paste_event', 'observed_at_utc': '2026-11-27T12:00:00', 'origin': 'https://chatgpt.com'}]
assert load_events(json.dumps(fixture).encode(), 'test.json')[0]['event_time'] is None
for fraction in ('4', '40', '400', '4000', '40000', '400000', '4000000'):
    fixture[0]['observed_at_utc'] = '2026-10-26T23:42:02.' + fraction + '+09:00'
    converted = load_events(json.dumps(fixture).encode(), 'test.json')[0]
    assert converted['event_time'] == '2026-10-26T14:42:02.400000+00:00'
    assert converted['attributes']['observed_at_utc'] == fixture[0]['observed_at_utc']
result = run_demo()
assert Counter(a['rule_id'] for a in result['alerts']) == {'R01': 3, 'R02': 1, 'R05': 1}
expected = json.loads((research / '01_detection/poc/output.json').read_text(encoding='utf-8'))
assert result == expected

started = datetime(2026, 10, 26, 14, 42, tzinfo=timezone.utc)
ended = started.replace(minute=43)
paste = {
    'type': 'paste_event', 'run_id': 'check-run', 'origin': 'https://chatgpt.com',
    'observed_at_utc': '2026-10-26T14:42:50.823Z', 'trusted': True,
    'target_editable': True, 'payload_collected': False,
}
variants = [paste, {**paste, 'trusted': False}, {**paste, 'target_editable': False},
            {**paste, 'observed_at_utc': '2026-10-26T14:41:50Z'}]
paste_log = '\n'.join(map(json.dumps, variants)).encode('utf-8')
assert len(browser_rows(paste_log, 'chrome.jsonl', started, ended)) == 1

clipboard = {'type': 'clipboard_update', 'observed_at_utc': '2026-10-26T14:42:15Z'}
dns = {'source': 'dns_cache', 'observed_at': paste['observed_at_utc'],
       'domain': 'chatgpt.com', 'matched_ai': True}
review_log = '\n'.join(map(json.dumps, [clipboard, paste, dns])).encode('utf-8')
observed = load_events(review_log, 'observed.jsonl', 'observed')
assert review(observed, set(), 60)[1] == []
assert review([e for e in observed if e['source'] == 'dns_cache'], {'ChatGPT'}, 60)[1] == []
assert len(review(observed, {'ChatGPT'}, 30)[1][0][3]) == 1
assert [e['event_type'] for e in review(observed, {'ChatGPT'}, 60)[1][0][3]] == [
    'paste_event', 'clipboard_update',
]
assert review(load_events(review_log, 'synthetic.jsonl', 'synthetic'), {'ChatGPT'}, 60)[1] == []
visit = {'action_claim': 'service_visit_record', 'record_id': 1,
         'event_time_utc': paste['observed_at_utc'], 'host': 'claude.ai'}
history = load_events(json.dumps([visit]).encode(), 'history.json', 'observed')
assert review(history, {'ChatGPT'}, 60)[1] == []
assert review(history, {'Claude'}, 60)[1][0][1] == '미승인 AI 방문 정황'

tcp = {'source': 'tcp_conn', 'observed_at': paste['observed_at_utc'],
       'domain_from_dns_cache': 'chatgpt.com', 'matched_ai': True}
network = load_events(json.dumps([dns, tcp]).encode(), 'network.json', 'observed')
assert review(network, {'ChatGPT'}, 60)[1] == []
for timestamp, expected_count in (
    ('2026-10-26T23:41:50.823+09:00', 2),
    ('2026-10-26T14:41:50.822Z', 1),
    (paste['observed_at_utc'], 1),
    ('2026-10-26T14:43:00Z', 1),
):
    records = [{**clipboard, 'observed_at_utc': timestamp}, paste]
    timed = load_events(json.dumps(records).encode(), 'timed.json', 'observed')
    assert len(review(timed, {'ChatGPT'}, 60)[1][0][3]) == expected_count

evidence_dir = research / '04_endpoint-telemetry/evidence'
for variant, expected_count in [('positive', 1), ('negative', 0)]:
    file = evidence_dir / f'web-paste-{variant}.projected.jsonl'
    projected = load_events(file.read_bytes(), file.name, 'observed')
    assert len(review(projected, {'ChatGPT'}, 60)[1]) == expected_count

app = AppTest.from_file(str(Path(__file__).with_name('app.py')), default_timeout=30).run()
assert not app.exception
app.file_uploader[0].upload('windows.jsonl', json.dumps(clipboard).encode()).upload(
    'chrome.jsonl', json.dumps(paste).encode()).run()
app.multiselect[0].select('ChatGPT').run()
assert not app.dataframe
app.checkbox[0].check().run()
assert not app.exception and not app.error
assert len(app.dataframe[0].value) == 2
assert any('Clipboard 변경 후 미승인 AI 붙여넣기 정황' in x.label for x in app.expander)
app.file_uploader[0].upload('fixture.json', json.dumps([
    {'event_type': 'paste_event', 'synthetic': True},
]).encode()).run()
assert app.error and not app.dataframe
app.radio[0].set_value('기존 연구 자료').run()
assert not app.exception
for label in app.selectbox[0].options[:-1]:
    app.selectbox[0].select(label).run()
    assert not app.exception, label
    assert len(app.dataframe) >= 1, label
app.selectbox[0].select('내 JSON/JSONL 불러오기').run()
assert not app.exception
app.radio[0].set_value('합성 규칙 시연').run()
assert not app.exception
for seconds in (30, 60, 300):
    app.selectbox[0].set_value(seconds).run()
    assert not app.exception
    assert len(app.dataframe) == 1
print('PASS: 기존 자료 6종, UTC 변환, 누락값, 출처, 오류/빈 입력, Chrome 로그 연결, 실측 의심 동작, 합성 규칙, 화면 메뉴·시간 범위')
print('공유 로그 행 수:', counts)
