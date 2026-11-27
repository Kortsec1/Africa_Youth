"""Session-only observations on the Windows host running Streamlit."""

import csv
import ctypes
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess

import streamlit as st


def local_time(timestamp=None):
    value = datetime.now() if timestamp is None else datetime.fromtimestamp(timestamp)
    return value.strftime('%Y-%m-%d %H:%M:%S')


def process_ids(name):
    result = subprocess.run(
        ['tasklist.exe', '/FI', f'IMAGENAME eq {name}', '/FO', 'CSV', '/NH'],
        capture_output=True, check=True, timeout=4, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return {
        row[1] for row in csv.reader(result.stdout.decode('oem', errors='replace').splitlines())
        if len(row) >= 2 and row[0].casefold() == name.casefold() and row[1].isdigit()
    }


def snapshot(name, file):
    clipboard = ctypes.windll.user32.GetClipboardSequenceNumber() & 0xffffffff
    processes = process_ids(name) if name else set()
    metadata = None
    if file:
        try:
            info = file.stat()
            metadata = (info.st_size, info.st_mtime_ns)
        except FileNotFoundError:
            pass
    return clipboard, processes, metadata


def changes(before, after, name, file):
    now = local_time()
    old_clip, old_pids, old_file = before
    clip, pids, metadata = after
    rows = []
    if old_clip and clip and clip != old_clip:
        rows.append((now, 'Clipboard', '변경 감지'))
    for pid in sorted(pids - old_pids):
        rows.append((now, '프로세스', f'{name} 등장 (PID {pid})'))
    for pid in sorted(old_pids - pids):
        rows.append((now, '프로세스', f'{name} 사라짐 (PID {pid})'))
    if metadata != old_file:
        if metadata is None:
            detail = '파일 없음'
        else:
            size, mtime = metadata
            detail = f'{size:,} 바이트 · 수정 {local_time(mtime / 1_000_000_000)}'
        rows.append((now, '파일', f'{file.name} · {detail}'))
    return [{'관찰 시각': time, '종류': kind, '기록': detail} for time, kind, detail in rows]


def show_live():
    st.subheader('내 PC 실시간 기록')
    if os.name != 'nt':
        st.info('실시간 기록은 Windows에서 사용할 수 있습니다.')
        return
    if st.get_option('server.address') not in ('127.0.0.1', '::1'):
        st.info('실시간 기록을 사용하려면 Streamlit을 --server.address 127.0.0.1 옵션으로 실행하세요.')
        return

    state = st.session_state
    running = state.get('live_running', False)
    st.write('관찰을 시작한 뒤 텍스트를 복사하거나, 지정한 프로그램을 열고 닫거나, 테스트 파일을 저장해 보세요.')
    with st.expander('관찰 대상', expanded=not running):
        name = st.text_input('프로세스 이름', 'notepad.exe', disabled=running).strip()
        path = st.text_input('테스트 파일 경로 (선택)', placeholder=r'C:\Temp\test.txt', disabled=running).strip()
    st.caption('약 2초마다 변경을 확인합니다. Clipboard 내용은 읽지 않으며, 최근 100건은 현재 브라우저 세션에만 보관합니다.')

    if running:
        if st.button('관찰 중지'):
            state.live_running = False
            st.rerun()
        st.success('관찰 중')
    elif st.button('관찰 시작', type='primary'):
        file = Path(path) if path else None
        if name and not re.fullmatch(r'[a-zA-Z0-9_. -]+\.exe', name, flags=re.IGNORECASE):
            st.error('프로세스 이름은 notepad.exe처럼 입력하세요.')
        elif file and (not file.is_absolute() or str(file).startswith('\\\\') or file.is_dir()):
            st.error('테스트 파일의 로컬 절대 경로를 입력하세요.')
        else:
            try:
                state.live_previous = snapshot(name, file)
            except (OSError, subprocess.SubprocessError) as error:
                st.error(f'관찰을 시작하지 못했습니다. ({type(error).__name__})')
            else:
                state.live_target = name, file
                state.live_running = True
                state.live_rows = []
                st.rerun()

    @st.fragment(run_every=2 if running else None)
    def timeline():
        if state.get('live_running', False):
            name, file = state.live_target
            try:
                current = snapshot(name, file)
            except (OSError, subprocess.SubprocessError) as error:
                st.warning(f'이번 관찰을 완료하지 못했습니다. ({type(error).__name__})')
            else:
                new = changes(state.live_previous, current, name, file)
                state.live_previous = current
                state.live_rows = (new[::-1] + state.live_rows)[:100]
        rows = state.get('live_rows', [])
        if rows:
            st.dataframe(rows, hide_index=True, width='stretch')
        else:
            st.info('아직 관찰된 변경이 없습니다.')

    timeline()
