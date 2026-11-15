"""상관분석 엔진: 파싱 → enrichment → 세션 구성 → 규칙 실행."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..catalog import Catalog, enrich, load_catalog
from ..parsers import load_dir
from ..schema import AISession, Event, Finding
from .rules import RULES, Config, Context
from .sessions import annotate_focus, build_sessions

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


@dataclass
class Result:
    events: list[Event]
    sessions: list[AISession]
    findings: list[Finding]
    inventory: dict[str, str] = field(default_factory=dict)
    host: str = ""


def analyze_events(events: list[Event], cat: Catalog | None = None, cfg: Config | None = None,
                   since: datetime | None = None, until: datetime | None = None) -> Result:
    cat = cat or load_catalog()
    if since:
        events = [e for e in events if e.ts >= since]
    if until:
        events = [e for e in events if e.ts <= until]
    # 브라우저 DB·LNK 등 호스트명을 담지 않는 아티팩트는 같은 수집본의 대표 호스트로 채운다
    hosts = Counter(e.host.upper() for e in events if e.host)
    main_host = hosts.most_common(1)[0][0] if hosts else ""
    for e in events:
        e.host = e.host.upper() if e.host else main_host
    events = sorted(enrich(events, cat), key=lambda e: e.ts)
    annotate_focus(events)
    sessions = build_sessions(events, cat)
    ctx = Context(events=events, sessions=sessions, cat=cat, cfg=cfg or Config())
    for _rid, _name, fn in RULES:
        fn(ctx)
    ctx.findings.sort(key=lambda f: f.ts)
    return Result(events=events, sessions=sessions, findings=ctx.findings)


def analyze_path(path: Path, host: str = "", catalog: str | None = None, **kw) -> Result:
    events, inventory = load_dir(Path(path), host=host)
    res = analyze_events(events, load_catalog(catalog), **kw)
    res.inventory = inventory
    res.host = host or next((e.host for e in res.events if e.host), "")
    return res
