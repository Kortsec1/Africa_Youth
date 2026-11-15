"""입력 파일 형식 자동 판별 및 파싱 진입점."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..schema import Event
from . import agent, browser, eventlog, filesystem, shell
from .common import csv_header

log = logging.getLogger(__name__)


def detect(path: Path) -> str | None:
    """파일 내용(헤더/스키마)으로 형식을 판별. 파일명에 의존하지 않는다."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        h = csv_header(path)
        if filesystem.sniff_usn(h):
            return "usn"
        if filesystem.sniff_mft(h):
            return "mft"
        if shell.sniff_jumplist(h):
            return "jumplist"
        if shell.sniff_lnk(h):
            return "lnk"
        if eventlog.sniff_evtxecmd(h):
            return "evtxecmd"
        return None
    if suffix in (".jsonl", ".json", ".ndjson"):
        try:
            with open(path, encoding="utf-8-sig") as f:
                first = next((json.loads(l) for l in f if l.strip()), None)
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(first, dict):
            return None
        if agent.sniff_agent(first):
            return "agent"
        if eventlog.sniff_winevent_jsonl(first):
            return "winevent"
        return None
    # 확장자 없는 SQLite (History, places.sqlite)
    try:
        if browser.sniff_firefox(path):
            return "firefox"
        if browser.sniff_chromium(path):
            return "chromium"
    except Exception:  # noqa: BLE001 - 손상 DB 등은 건너뜀
        log.debug("sqlite sniff failed: %s", path, exc_info=True)
    return None


PARSERS = {
    "mft": filesystem.parse_mft,
    "usn": filesystem.parse_usn,
    "lnk": shell.parse_lnk,
    "jumplist": shell.parse_jumplist,
    "evtxecmd": eventlog.parse_evtxecmd,
    "winevent": eventlog.parse_winevent_jsonl,
    "agent": agent.parse_agent,
    "chromium": browser.parse_chromium,
    "firefox": browser.parse_firefox,
}


def load_dir(root: Path, host: str = "") -> tuple[list[Event], dict[str, str]]:
    """디렉터리 아래 모든 파일을 판별·파싱. (이벤트, {파일: 형식}) 반환."""
    events: list[Event] = []
    inventory: dict[str, str] = {}
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    for p in files:
        if p.name.endswith(("-wal", "-journal", "-shm")):
            continue
        kind = detect(p)
        if not kind:
            continue
        parsed = PARSERS[kind](p, host=host)
        inventory[str(p.relative_to(root) if root.is_dir() else p.name)] = f"{kind} ({len(parsed)} events)"
        events.extend(parsed)
    events.sort(key=lambda e: e.ts)
    return events, inventory
