"""기존 연구 자료를 표시용 이벤트로 변환한다. 원본은 변경하지 않는다."""
import hashlib
import json
import re
from datetime import datetime, timezone


def load_events(raw, filename, origin='unknown'):
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode('utf-8-sig')
    if filename.lower().endswith('.jsonl'):
        rows = []
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    rows.append((f'line:{number}', json.loads(line)))
                except ValueError as exc:
                    raise ValueError(f'{number}행 JSON 오류: {exc}') from exc
        root = {}
    else:
        root = json.loads(text)
        if isinstance(root, list):
            rows = [(f'/{i}', row) for i, row in enumerate(root)]
            root = {}
        elif isinstance(root, dict) and isinstance(root.get('events'), list):
            rows = [(f'/events/{i}', row) for i, row in enumerate(root['events'])]
        else:
            raise ValueError('events 배열을 가진 JSON 또는 JSON/JSONL 이벤트 목록이 필요합니다.')
    events = []
    network_label = None
    for locator, row in rows:
        if not isinstance(row, dict):
            raise ValueError(f'{locator}: 이벤트는 JSON 객체여야 합니다.')
        source, kind, stamp, semantics = None, None, None, 'unknown'
        limits = []
        data_origin = origin
        if 'phase' in row and 'creationUtc' in row:
            source, kind = 'file_metadata', 'file_metadata_snapshot'
            limits.append('메타데이터 스냅샷입니다. 관측 시각과 파일 읽기·전송 여부는 알 수 없습니다.')
        elif 'action_claim' in row and 'record_id' in row:
            source, kind = 'browser_history', 'browser_visit'
            stamp, semantics = row.get('event_time_utc'), 'browser_visit_time'
            limits.append('방문 기록만으로 질문 전송·파일 업로드를 확인할 수 없습니다.')
        elif 'synthetic' in row and 'event_type' in row:
            source, kind = row.get('source'), row['event_type']
            stamp, semantics = row.get('occurred_at'), 'fixture_event_time'
            data_origin = 'synthetic' if row['synthetic'] is True else 'unknown'
            limits.append('입력의 synthetic 표기를 보존합니다. 실제 수집 여부를 인증하지 않습니다.')
        elif row.get('source') in ('dns_cache', 'tcp_conn', 'collector'):
            source = row['source']
            if source == 'collector' and row.get('event') == 'start':
                network_label = row.get('label')
            kind = {'dns_cache': 'dns_cache_observation', 'tcp_conn': 'tcp_connection_observation', 'collector': 'collector_status'}[source]
            if 'error' in row:
                kind = 'collector_error'
            stamp, semantics = row.get('observed_at'), 'poll_observation_time'
            limits.append('폴링 관측 시각이며 질의·연결 생성 시각이나 전송 증거가 아닙니다.')
        elif 'type' in row and 'observed_at_utc' in row:
            kind = row['type']
            source = 'chrome_paste_observer' if ('origin' in row or 'document_id' in row or kind in ('experiment_start', 'experiment_stop')) else 'windows_collector'
            stamp, semantics = row['observed_at_utc'], 'collector_observation_time'
            data = row.get('data') or {}
            if not isinstance(data, dict):
                raise ValueError(f'{locator}: data는 객체여야 합니다.')
            if kind in ('process_start', 'process_stop') and data.get('source_time_utc'):
                stamp, semantics = data['source_time_utc'], 'wmi_event_generation_time'
            limits.append('관측 기록입니다. Clipboard 변경·활성 창·paste는 전송 성공을 의미하지 않습니다.')
        else:
            raise ValueError(f'{locator}: 지원하지 않는 이벤트 형식입니다.')
        normalized_time = None
        if stamp is not None:
            try:
                # Python 3.10은 소수 초 3/6자리만 허용한다.
                # 원문은 attributes에 남기고 파싱할 값만 6자리로 맞춘다.
                parse_stamp = re.sub(
                    r'(\d{2}:\d{2}:\d{2})\.(\d+)',
                    lambda m: m[1] + '.' + m[2][:6].ljust(6, '0'),
                    stamp.replace('Z', '+00:00'),
                )
                value = datetime.fromisoformat(parse_stamp)
                if value.utcoffset() is None:
                    raise ValueError('시간대 없음')
                normalized_time = value.astimezone(timezone.utc).isoformat(timespec='microseconds')
                if re.search(r'\.\d{7,}', stamp):
                    limits.append('표시용 정렬 시각은 마이크로초까지 사용합니다. 원문 시각은 보존합니다.')
            except (ValueError, TypeError, AttributeError):
                limits.append('시각 또는 시간대를 해석할 수 없어 시각 미확정으로 표시합니다.')
        if row.get('projection') is True:
            limits.append('일부 필드가 제거된 공유용 파생본입니다. 누락된 사용자·장치는 복원하지 않습니다.')
        events.append(dict(
            event_id=f'{digest}:{locator}', event_time=normalized_time,
            time_semantics=semantics, source=source, event_type=kind,
            attributes=row, device_id=row.get('device_id'), user_id=row.get('user_id'),
            source_ref=dict(file=filename, sha256=digest, locator=locator),
            experiment_id=row.get('experiment') or row.get('run_id') or row.get('label') or (network_label if source in ('dns_cache', 'tcp_conn', 'collector') else None),
            data_origin=data_origin, representation='projection' if row.get('projection') is True else 'source_record',
            limitations=limits,
        ))
    return sorted(events, key=lambda e: (e['event_time'] is None, e['event_time'] or '', e['event_id']))
