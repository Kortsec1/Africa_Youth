"""Synthetic fixtures ONLY: validate host matching, visit times and WAL reads."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from analyze_history import extract


def run():
    checks = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'History'
        con = sqlite3.connect(path)
        con.executescript('CREATE TABLE urls(id INTEGER PRIMARY KEY,url TEXT,title TEXT);'
                          'CREATE TABLE visits(id INTEGER PRIMARY KEY,url INTEGER,visit_time INTEGER);')
        epoch = dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)
        moment = dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.timezone.utc)
        delta = moment - epoch
        stamp = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        hosts = ['https://chatgpt.com/c/synthetic', 'https://claude.ai/new',
                 'https://gemini.google.com/app', 'https://chat.openai.com/',
                 'https://chatgpt.com.attacker.invalid/',
                 'https://attacker.invalid/?q=chatgpt.com', 'https://chatgpt.com@attacker.invalid/',
                 'https://CHATGPT.COM/', 'file://chatgpt.com/test']
        for i, url in enumerate(hosts, 1):
            con.execute('INSERT INTO urls VALUES(?,?,?)', (i, url, 'SYNTHETIC'))
            con.execute('INSERT INTO visits VALUES(?,?,?)', (i, i, stamp))
        # Same URL visited twice: visits must not be collapsed to last_visit_time.
        con.execute('INSERT INTO visits VALUES(?,?,?)', (10, 1, stamp + 1000000))
        con.commit()
        con.close()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = extract(path)
        assert len(result['events']) == 6
        checks.append('exact_host_and_scheme_filter_6_visits')
        assert result['events'][0]['event_time_utc'] == '2026-11-16T00:00:00+00:00'
        assert result['events'][-1]['event_time_utc'] == '2026-11-16T00:00:01+00:00'
        checks.append('chromium_microseconds_1601_to_utc_and_repeated_visits')
        assert all(x['action_claim'] == 'service_visit_record' for x in result['events'])
        checks.append('no_prompt_or_upload_inference')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        checks.append('main_database_unchanged')
        con = sqlite3.connect(path)
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute('INSERT INTO visits VALUES(?,?,?)', (11, 1, stamp + 2000000))
        con.commit()
        assert Path(str(path) + '-wal').exists()
        assert len(extract(path)['events']) == 7
        checks.append('committed_wal_visit_visible')
        con.close()
        bad = Path(folder) / 'bad'
        bad.write_text('not sqlite', encoding='utf-8')
        try:
            extract(bad)
        except sqlite3.DatabaseError:
            checks.append('corrupt_database_rejected')
        else:
            raise AssertionError('corrupt database accepted')
    return {'dataset_type': 'synthetic_only_not_browser_experiment',
            'executed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'sqlite_version': sqlite3.sqlite_version, 'checks': checks,
            'passed': len(checks), 'status': 'pass'}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
