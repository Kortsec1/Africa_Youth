"""Best-effort live read: marker counts only, not an atomic forensic acquisition."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

MARKERS = ['AIART-20261116-UNSENT-7D3F', 'AIART-20261116-SENT-9A2C',
           'AIART-20261116-FILE-4B8E', 'AIART-20261116-CONTENT-6F1D']
FOLDERS = ['Local Storage', 'Session Storage', 'IndexedDB', 'Sessions',
           'Cache/Cache_Data', 'Service Worker']


def run(profile, start):
    result = {'collected_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'method': 'best_effort_live_read_not_atomic_snapshot',
              'profile': 'Chrome Default candidate; active profile not independently verified',
              'markers': MARKERS, 'hits': [], 'errors': [], 'files_scanned': 0,
              'history': {'status': 'not_attempted'}}
    for folder in FOLDERS:
        root = profile / folder
        if not root.exists():
            result['errors'].append({'path': folder, 'error': 'missing'})
            continue
        for path in root.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(profile).as_posix()
            try:
                if path.stat().st_size > 64 * 1024 * 1024:
                    result['errors'].append({'path': rel, 'error': 'over_64MiB_limit'})
                    continue
                data = path.read_bytes()
                result['files_scanned'] += 1
                for marker in MARKERS:
                    for encoding in ['utf-8', 'utf-16-le']:
                        needle = marker.encode(encoding)
                        pos = data.find(needle)
                        if pos != -1:
                            result['hits'].append({'path': rel, 'marker': marker,
                                'encoding': encoding, 'first_byte_offset': pos,
                                'count': data.count(needle), 'length': len(data),
                                'sha256_at_read': hashlib.sha256(data).hexdigest()})
            except OSError as exc:
                result['errors'].append({'path': rel, 'error': str(exc)})
    con = None
    try:
        con = sqlite3.connect((profile / 'History').resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
        con.execute('PRAGMA query_only=ON')
        epoch = dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)
        events = []
        for rid, stamp, url, title in con.execute(
                'SELECT v.id,v.visit_time,u.url,u.title FROM visits v JOIN urls u ON v.url=u.id WHERE v.visit_time>=? ORDER BY v.visit_time', (start,)):
            if urlsplit(url).hostname not in {'chatgpt.com', 'claude.ai', 'gemini.google.com'}:
                continue
            events.append({'record_id': rid, 'raw_time': stamp,
                           'utc': (epoch + dt.timedelta(microseconds=stamp)).isoformat(),
                           'url': url, 'title': title})
        result['history'] = {'status': 'read', 'visits': events}
    except (OSError, sqlite3.Error, ValueError) as exc:
        result['history'] = {'status': 'unavailable', 'error': str(exc)}
    finally:
        if con is not None:
            con.close()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(run(args.profile, args.start), stream, ensure_ascii=False, indent=2)
        stream.write('\n')
