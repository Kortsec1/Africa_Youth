"""브라우저 히스토리 파서 (Chromium 계열 History, Firefox places.sqlite).

브라우저 실행 중에는 DB 가 잠겨 있고 WAL 에 최신 기록이 남아 있을 수 있으므로
원본을 직접 열지 않고 -wal/-journal 파일과 함께 임시 디렉터리에 복사해 읽기 전용으로 연다.

  Chrome : %LOCALAPPDATA%\\Google\\Chrome\\User Data\\<Profile>\\History
  Edge   : %LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\<Profile>\\History
  Whale  : %LOCALAPPDATA%\\Naver\\Naver Whale\\User Data\\<Profile>\\History
  Firefox: %APPDATA%\\Mozilla\\Firefox\\Profiles\\<profile>\\places.sqlite
"""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from ..schema import Action, Category, Event
from ..timeutil import from_unix_us, from_webkit

# Chromium PageTransition core 값 (transition & 0xFF)
TRANSITIONS = {0: "link", 1: "typed", 2: "auto_bookmark", 3: "auto_subframe", 4: "manual_subframe",
               5: "generated", 6: "auto_toplevel", 7: "form_submit", 8: "reload", 9: "keyword",
               10: "keyword_generated"}
DOWNLOAD_STATE = {0: "in_progress", 1: "complete", 2: "cancelled", 3: "interrupted"}


def _is_sqlite(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


@contextmanager
def _open_copy(path: Path):
    tmp = Path(tempfile.mkdtemp(prefix="saf_"))
    try:
        dst = tmp / path.name
        shutil.copy2(path, dst)
        for suffix in ("-wal", "-journal", "-shm"):
            side = path.with_name(path.name + suffix)
            if side.exists():
                shutil.copy2(side, tmp / side.name)
        con = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
        try:
            yield con
        finally:
            con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tables(con) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def sniff_chromium(path: Path) -> bool:
    if not _is_sqlite(path):
        return False
    with _open_copy(path) as con:
        return {"urls", "visits"} <= _tables(con)


def sniff_firefox(path: Path) -> bool:
    if not _is_sqlite(path):
        return False
    with _open_copy(path) as con:
        return {"moz_places", "moz_historyvisits"} <= _tables(con)


def _browser_from_path(path: Path) -> str:
    p = str(path).lower()
    if "edge" in p:
        return "msedge.exe"
    if "whale" in p:
        return "whale.exe"
    if "brave" in p:
        return "brave.exe"
    return "chrome.exe"


def parse_chromium(path: Path, host: str = "", user: str = "", browser: str | None = None) -> list[Event]:
    browser = browser or _browser_from_path(path)
    events: list[Event] = []
    with _open_copy(path) as con:
        tables = _tables(con)
        q = ("SELECT v.id, v.visit_time, u.url, u.title, v.transition, v.visit_duration "
             "FROM visits v JOIN urls u ON v.url = u.id ORDER BY v.visit_time")
        for vid, vt, url, title, trans, dur in con.execute(q):
            ts = from_webkit(vt)
            if not ts:
                continue
            events.append(Event(
                ts=ts, source="ChromeHistory", category=Category.WEB, action=Action.WEB_VISIT,
                time_meaning="visits.visit_time (페이지 방문 시각)",
                host=host, user=user, process=browser, url=url, domain=urlsplit(url).hostname or "",
                title=title or "", raw_ref=f"{path.name}:visits.id={vid}",
                attrs={"transition": TRANSITIONS.get((trans or 0) & 0xFF, str(trans)),
                       "duration_s": round((dur or 0) / 1e6, 1)},
            ))
        if "downloads" in tables:
            chains: dict[int, list[str]] = {}
            if "downloads_url_chains" in tables:
                for did, idx, u in con.execute(
                        "SELECT id, chain_index, url FROM downloads_url_chains ORDER BY id, chain_index"):
                    chains.setdefault(did, []).append(u)
            cols = {r[1] for r in con.execute("PRAGMA table_info(downloads)")}
            want = [c for c in ("id", "target_path", "start_time", "end_time", "total_bytes", "state",
                                "referrer", "tab_url", "tab_referrer_url", "site_url", "mime_type",
                                "danger_type") if c in cols]
            for row in con.execute(f"SELECT {', '.join(want)} FROM downloads"):
                d = dict(zip(want, row))
                ts = from_webkit(d.get("end_time")) or from_webkit(d.get("start_time"))
                if not ts:
                    continue
                chain = chains.get(d["id"], [])
                url = chain[-1] if chain else ""
                events.append(Event(
                    ts=ts, source="ChromeDownloads", category=Category.WEB, action=Action.DOWNLOAD,
                    time_meaning="downloads.end_time (다운로드 완료 시각)",
                    host=host, user=user, process=browser, url=url,
                    domain=urlsplit(url).hostname or "", path=d.get("target_path", "") or "",
                    raw_ref=f"{path.name}:downloads.id={d['id']}",
                    attrs={
                        "referrer": d.get("referrer", ""),
                        "tab_url": d.get("tab_url", ""),
                        "site_url": d.get("site_url", ""),
                        "mime": d.get("mime_type", ""),
                        "bytes": d.get("total_bytes", 0),
                        "state": DOWNLOAD_STATE.get(d.get("state"), str(d.get("state"))),
                        "url_chain": chain,
                        "started": str(from_webkit(d.get("start_time")) or ""),
                    },
                ))
    return events


def parse_firefox(path: Path, host: str = "", user: str = "") -> list[Event]:
    events: list[Event] = []
    with _open_copy(path) as con:
        q = ("SELECT v.id, v.visit_date, p.url, p.title, v.visit_type FROM moz_historyvisits v "
             "JOIN moz_places p ON v.place_id = p.id ORDER BY v.visit_date")
        for vid, vd, url, title, vtype in con.execute(q):
            ts = from_unix_us(vd)
            if not ts:
                continue
            events.append(Event(
                ts=ts, source="FirefoxHistory", category=Category.WEB, action=Action.WEB_VISIT,
                time_meaning="moz_historyvisits.visit_date (페이지 방문 시각)",
                host=host, user=user, process="firefox.exe", url=url,
                domain=urlsplit(url).hostname or "", title=title or "",
                raw_ref=f"{path.name}:moz_historyvisits.id={vid}", attrs={"visit_type": vtype},
            ))
    return events
