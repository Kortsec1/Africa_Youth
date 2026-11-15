"""04_endpoint-telemetry 실측 도구 출력 파서.

1) RealtimeCollector (docs/research/04_endpoint-telemetry/poc/windows-collector, C#)
   schema_version 2 JSONL: {schema_version, run_id, event_id, observed_at_utc, monotonic_ms, type, data}
   - foreground_change / foreground_title_change / foreground_snapshot → window_focus
   - clipboard_update  → clipboard_change   (원문 미수집, 형식 ID 만)
   - process_start / process_snapshot → process_start (+ PID→프로세스명 매핑에 사용)
   창 이벤트·클립보드 이벤트에는 프로세스명이 없고 PID 만 있으므로, 같은 로그의
   process_snapshot / process_start 로 PID→이름을 복원한다. (PID 재사용 가능성은 attrs 에 표시)

2) Chrome 붙여넣기 관측 확장 (docs/research/04_endpoint-telemetry/tools/chrome-paste-observer)
   schema_version 1 JSONL: {type: page_ready|paste_event|experiment_start|stop, observed_at_utc, origin, trusted, ...}
   - paste_event → web_paste  : AI 입력창 붙여넣기의 '직접' 관측 (전송 성공은 아님)

3) evidence/*.projected.jsonl (저장소 공개용 선택 필드 사본)도 같은 의미로 읽는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from ..schema import Action, Category, Event
from ..timeutil import parse_ts

COLLECTOR_TYPES = {"collector_start", "foreground_change", "foreground_title_change", "foreground_snapshot",
                   "clipboard_update", "process_start", "process_stop", "process_snapshot", "source_status",
                   "heartbeat", "collector_stop"}
PASTE_TYPES = {"experiment_start", "page_ready", "paste_event", "experiment_stop"}


def sniff_collector(obj: dict) -> bool:
    return obj.get("type") in COLLECTOR_TYPES and "observed_at_utc" in obj and (
        "monotonic_ms" in obj or obj.get("projection"))


def sniff_paste(obj: dict) -> bool:
    return obj.get("type") in PASTE_TYPES and "observed_at_utc" in obj and "monotonic_ms" not in obj


def _exe(name: str) -> str:
    n = (name or "").strip()
    return n if not n or n.lower().endswith(".exe") else n + ".exe"


def _rows(path: Path):
    with open(path, encoding="utf-8-sig") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                yield i, json.loads(line)


def parse_collector(path: Path, host: str = "") -> list[Event]:
    rows = list(_rows(path))
    pid_name: dict[int, str] = {}
    for _, o in rows:
        d = o.get("data") or {}
        if o.get("type") in ("process_snapshot", "process_start") and d.get("pid") is not None:
            pid_name[int(d["pid"])] = _exe(d.get("process_name", ""))

    events: list[Event] = []
    for i, o in rows:
        t, d = o.get("type"), o.get("data") or {}
        ts = parse_ts(o.get("observed_at_utc"))
        if not ts:
            continue
        ref = f"{path.name}:{i}"
        run = {"run_id": o.get("run_id", ""), "event_id": o.get("event_id"), "experiment": o.get("experiment", "")}
        if t in ("foreground_change", "foreground_title_change", "foreground_snapshot"):
            w = d.get("window") or {}
            pid = w.get("pid")
            events.append(Event(
                ts=ts, source="RealtimeCollector", category=Category.WINDOW, action=Action.WINDOW_FOCUS,
                time_meaning="WinEvent 전면 창 변경 관측 시각 (수집기 기록 시각)", host=host,
                process=pid_name.get(pid, ""), pid=pid, title=w.get("title") or "", raw_ref=ref,
                attrs={**run, "kind": t, "pid_name_from_log": pid in pid_name},
            ))
        elif t == "clipboard_update":
            owner = d.get("owner_at_observation") or {}
            fg = d.get("foreground_at_observation") or {}
            src = owner if owner.get("pid") else fg
            pid = src.get("pid")
            events.append(Event(
                ts=ts, source="RealtimeCollector", category=Category.CLIPBOARD, action=Action.CLIPBOARD_CHANGE,
                time_meaning="WM_CLIPBOARDUPDATE 수신 후 상태 관측 시각 (붙여넣기 아님)", host=host,
                process=pid_name.get(pid, "") if pid else "", pid=pid, title=src.get("title") or "", raw_ref=ref,
                attrs={**run, "format_status": d.get("format_query_status"), "has_text": d.get("has_unicode_text"),
                       "has_file_drop": d.get("has_file_drop"), "open_attempts": d.get("open_attempts"),
                       "source_is_owner": bool(owner.get("pid")), "source_title": src.get("title") or ""},
            ))
        elif t == "process_start":
            src_ts = parse_ts(d.get("source_time_utc")) or ts
            events.append(Event(
                ts=src_ts, source="RealtimeCollector", category=Category.PROCESS, action=Action.PROCESS_START,
                time_meaning="WMI ProcessStartTrace 생성 시각", host=host, process=_exe(d.get("process_name", "")),
                pid=d.get("pid"), raw_ref=ref,
                attrs={**run, "parent_pid": d.get("parent_pid"), "identity_verified": d.get("instance_identity_verified")},
            ))
    return events


def parse_paste(path: Path, host: str = "") -> list[Event]:
    events: list[Event] = []
    for i, o in _rows(path):
        t = o.get("type")
        ts = parse_ts(o.get("observed_at_utc"))
        origin = o.get("origin") or ""
        if not ts or t not in ("page_ready", "paste_event") or not origin:
            continue
        common = dict(ts=ts, source="ChromePaste", category=Category.WEB, host=host, process="chrome.exe",
                      url=origin, domain=urlsplit(origin).hostname or "", raw_ref=f"{path.name}:{i}")
        if t == "paste_event":
            events.append(Event(
                action=Action.WEB_PASTE, time_meaning="웹페이지 paste 이벤트 관측 시각 (전송 성공은 아님)",
                attrs={"trusted": o.get("trusted"), "target_editable": o.get("target_editable"),
                       "target_tag": o.get("target_tag"), "run_id": o.get("run_id", ""),
                       "experiment": o.get("experiment", "")}, **common))
        else:
            events.append(Event(action=Action.WEB_VISIT, time_meaning="확장 content script 로드(페이지 준비) 시각",
                                attrs={"run_id": o.get("run_id", "")}, **common))
    return events
