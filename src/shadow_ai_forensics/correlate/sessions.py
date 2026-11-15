"""AI 사용 세션 구성.

AI 서비스와 직접 관련된 이벤트(방문·DNS·연결·창 포커스·앱 실행)를 서비스/채널별로 모아
일정 간격(gap) 이내면 하나의 세션으로 묶는다. 세션은 이후 모든 상관분석의 기준점이 된다.
corporate/static 역할(회사 홈페이지, CDN)은 '사용'의 근거가 아니므로 세션 구성에서 제외한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..catalog import Catalog
from ..schema import Action, AISession, Event

USAGE_ROLES = {"chat", "upload", "api", "app", "local_app"}
ANCHOR_ACTIONS = {Action.WEB_VISIT, Action.DNS_QUERY, Action.NET_CONNECT, Action.WINDOW_FOCUS,
                  Action.PROCESS_START}


def annotate_focus(events: list[Event]) -> None:
    """에이전트 포커스 이벤트에 포커스 종료 시각(다음 포커스 전환 시각)을 기록."""
    focus = [e for e in events if e.action in (Action.WINDOW_FOCUS, Action.FILE_DIALOG)]
    by_host: dict[str, list[Event]] = {}
    for e in focus:
        by_host.setdefault(e.host, []).append(e)
    for evs in by_host.values():
        evs.sort(key=lambda e: e.ts)
        for cur, nxt in zip(evs, evs[1:]):
            cur.attrs["focus_end"] = nxt.ts
            cur.attrs["next_focus_id"] = nxt.id
        if evs:
            evs[-1].attrs.setdefault("focus_end", evs[-1].ts)


def channel_of(e: Event, cat: Catalog) -> str:
    if e.ai_role == "local_app":
        return "local_llm"
    if e.ai_role == "app":
        return "desktop_app"
    if e.source in ("ChromeHistory", "FirefoxHistory") or cat.is_browser(e.process):
        return "browser"
    if e.ai_role == "api":
        return "api"
    if e.process and not cat.is_browser(e.process):
        # 데스크톱 앱(Electron)도 chat 도메인에 붙는다. 프로세스가 브라우저가 아니면 앱/스크립트로 본다.
        return "desktop_app" if cat.match_process(e.process) else "api"
    return "browser"     # 프로세스 정보 없는 DNS(DNS-Client 로그)는 브라우저로 가정 → 신뢰도에서 감점


def _end_of(e: Event) -> datetime:
    fe = e.attrs.get("focus_end")
    return fe if isinstance(fe, datetime) and fe > e.ts else e.ts


def build_sessions(events: list[Event], cat: Catalog, gap: timedelta = timedelta(minutes=10)) -> list[AISession]:
    anchors = [e for e in events
               if e.ai_service and e.ai_role in USAGE_ROLES and e.action in ANCHOR_ACTIONS]
    groups: dict[tuple[str, str, str], list[Event]] = {}
    for e in sorted(anchors, key=lambda e: e.ts):
        groups.setdefault((e.host, e.ai_service, channel_of(e, cat)), []).append(e)

    sessions: list[AISession] = []
    for (_host, svc, ch), evs in groups.items():
        cur: AISession | None = None
        for e in evs:
            if cur and e.ts - cur.end <= gap:
                cur.events.append(e)
                cur.end = max(cur.end, _end_of(e))
            else:
                cur = AISession(service=svc, start=e.ts, end=_end_of(e), channel=ch, events=[e])
                sessions.append(cur)
    sessions.sort(key=lambda s: s.start)
    for i, s in enumerate(sessions, start=1):
        s.id = f"S{i:03d}"
        for e in s.events:
            e.tags.append(f"session:{s.id}")
    return sessions
