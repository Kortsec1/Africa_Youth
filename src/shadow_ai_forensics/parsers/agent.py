"""엔드포인트 텔레메트리 에이전트(collector/telemetry_agent.py) JSONL 파서.

레코드 예
  {"ts":"2026-11-10T05:01:12.311Z","type":"window_focus","process":"C:\\...\\chrome.exe",
   "pid":4120,"title":"ChatGPT - Chrome","class":"Chrome_WidgetWin_1","host":"FIN-PC-07","user":"kim"}
  {"ts":"...","type":"clipboard_change","process":"EXCEL.EXE","pid":7712,"formats":["CF_UNICODETEXT"],
   "length":5832,"sha256":"...","source_title":"2026_Q3_재무제표.xlsx - Excel"}
"""
from __future__ import annotations

import json
from pathlib import Path

from ..schema import Action, Category, Event
from ..timeutil import parse_ts

TYPE_MAP = {
    "window_focus": (Category.WINDOW, Action.WINDOW_FOCUS, "포그라운드 창 전환 시각"),
    "file_dialog": (Category.WINDOW, Action.FILE_DIALOG, "파일 열기/저장 대화상자 포커스 시각"),
    "clipboard_change": (Category.CLIPBOARD, Action.CLIPBOARD_CHANGE, "클립보드 시퀀스 번호 변경 감지 시각"),
}


def sniff_agent(first_obj: dict) -> bool:
    return "ts" in first_obj and first_obj.get("type") in TYPE_MAP


def parse_agent(path: Path, host: str = "") -> list[Event]:
    events = []
    with open(path, encoding="utf-8-sig") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            m = TYPE_MAP.get(o.get("type"))
            ts = parse_ts(o.get("ts"))
            if not m or not ts:
                continue
            cat, act, meaning = m
            # 창 클래스 #32770 은 표준 대화상자 → 브라우저 소유면 파일 선택(업로드) 창일 가능성
            if act == Action.WINDOW_FOCUS and o.get("class") == "#32770":
                act, meaning = Action.FILE_DIALOG, TYPE_MAP["file_dialog"][2]
            title = o.get("title", "") or o.get("source_title", "")
            attrs = {k: v for k, v in o.items()
                     if k not in ("ts", "type", "process", "pid", "title", "host", "user")}
            events.append(Event(
                ts=ts, source="Agent", category=cat, action=act, time_meaning=meaning,
                host=host or o.get("host", ""), user=o.get("user", ""), process=o.get("process", ""),
                pid=o.get("pid"), title=title, attrs=attrs, raw_ref=f"{path.name}:{i}",
            ))
    return events
