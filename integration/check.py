"""마지막 기능 확인: python integration/check.py"""
from collections import Counter
from pathlib import Path
import json
from streamlit.testing.v1 import AppTest
from adapters import load_events
from analysis import ROOT, run_demo

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
expected = json.loads((research / '01_detection/poc/output.json').read_text())
assert result == expected

app = AppTest.from_file(str(Path(__file__).with_name('app.py')), default_timeout=30).run()
assert not app.exception
for label in app.sidebar.selectbox[0].options[:-1]:
    app.sidebar.selectbox[0].select(label).run()
    assert not app.exception, label
    assert len(app.dataframe) >= 1, label
app.sidebar.selectbox[0].select('내 JSON/JSONL 불러오기').run()
assert not app.exception
app.sidebar.radio[0].set_value('합성 규칙 시연').run()
assert not app.exception
for seconds in (30, 60, 300):
    app.selectbox[0].set_value(seconds).run()
    assert not app.exception
    assert len(app.dataframe) == 1
print('PASS: 기존 자료 6종, UTC 변환, 누락값, 출처, 오류/빈 입력, 규칙 결과, 화면 메뉴·시간 범위')
print('공유 로그 행 수:', counts)
