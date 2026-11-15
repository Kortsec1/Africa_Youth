"""AI 서비스 카탈로그 로딩 및 이벤트 enrichment."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from urllib.parse import urlsplit

from .schema import Action, Event

ROLE_ORDER = ("upload", "chat", "api", "static", "corporate")


@dataclass
class Service:
    name: str
    vendor: str
    local: bool
    domains: dict[str, list[str]]
    processes: list[str]
    window_titles: list[str]


@dataclass
class Catalog:
    services: list[Service]
    browsers: set[str]
    sensitive_keywords: list[str]
    document_exts: set[str]
    archive_exts: set[str]
    model_exts: set[str]
    _domain_index: list[tuple[str, str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 긴 도메인부터 매칭해야 chat.openai.com 이 openai.com(corporate) 보다 먼저 잡힌다.
        idx = []
        for s in self.services:
            for role in ROLE_ORDER:
                for d in s.domains.get(role, []):
                    idx.append((d.lower().lstrip("*."), s.name, role))
        self._domain_index = sorted(idx, key=lambda t: -len(t[0]))

    # ---- lookups ----
    def match_domain(self, domain: str) -> tuple[str, str] | None:
        d = (domain or "").lower().strip(".")
        if not d:
            return None
        for suffix, svc, role in self._domain_index:
            if d == suffix or d.endswith("." + suffix):
                return svc, role
        return None

    def match_url(self, url: str) -> tuple[str, str] | None:
        host = urlsplit(url).hostname if url else None
        return self.match_domain(host or "")

    def match_process(self, process: str) -> tuple[str, str] | None:
        name = process.replace("/", "\\").rsplit("\\", 1)[-1].lower()
        for s in self.services:
            if name in s.processes:
                return s.name, ("local_app" if s.local else "app")
        return None

    def match_title(self, title: str, process_name: str = "") -> tuple[str, str] | None:
        t = (title or "").lower()
        if not t:
            return None
        for s in self.services:
            for w in s.window_titles:
                if w in t:
                    if process_name in self.browsers:
                        return s.name, "chat"
                    if s.processes and process_name in s.processes:
                        return s.name, ("local_app" if s.local else "app")
        return None

    def service(self, name: str) -> Service | None:
        return next((s for s in self.services if s.name == name), None)

    def is_browser(self, process: str) -> bool:
        return process.replace("/", "\\").rsplit("\\", 1)[-1].lower() in self.browsers

    def is_sensitive(self, path_or_title: str) -> bool:
        p = (path_or_title or "").lower()
        return any(k.lower() in p for k in self.sensitive_keywords)

    def ext(self, path: str) -> str:
        name = path.replace("/", "\\").rsplit("\\", 1)[-1].lower()
        return "." + name.rsplit(".", 1)[-1] if "." in name else ""


def load_catalog(path: str | Path | None = None) -> Catalog:
    if path:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    else:
        data = tomllib.loads(
            resources.files("shadow_ai_forensics").joinpath("data/ai_services.toml").read_text(encoding="utf-8")
        )
    services = []
    for s in data.get("service", []):
        services.append(
            Service(
                name=s["name"],
                vendor=s.get("vendor", ""),
                local=bool(s.get("local", False)),
                domains={r: [d.lower() for d in s.get(r, [])] for r in ROLE_ORDER},
                processes=[p.lower() for p in s.get("processes", [])],
                window_titles=[w.lower() for w in s.get("window_titles", [])],
            )
        )
    return Catalog(
        services=services,
        browsers={p.lower() for p in data.get("browser", {}).get("processes", [])},
        sensitive_keywords=data.get("sensitive", {}).get("keywords", []),
        document_exts=set(data.get("sensitive", {}).get("extensions", [])),
        archive_exts=set(data.get("archive", {}).get("extensions", [])),
        model_exts=set(data.get("local_model", {}).get("extensions", [])),
    )


def enrich(events: list[Event], cat: Catalog) -> list[Event]:
    """AI 서비스 매칭, 민감 자료 표시, 태그 부여."""
    for e in events:
        hit = None
        if e.url:
            hit = cat.match_url(e.url)
        if not hit and e.domain:
            hit = cat.match_domain(e.domain)
        if not hit and e.action in (Action.WINDOW_FOCUS,):
            hit = cat.match_title(e.title, e.process_name)
        if not hit and e.process and e.action in (Action.PROCESS_START, Action.NET_CONNECT, Action.WINDOW_FOCUS):
            hit = cat.match_process(e.process)
        if hit:
            e.ai_service, e.ai_role = hit
            e.tags.append(f"ai:{e.ai_service}")
        # 다운로드 출처(Zone.Identifier / referrer)가 AI 도메인이면 태그
        for key in ("referrer", "tab_url", "host_url", "zone_referrer"):
            ref = e.attrs.get(key)
            if ref:
                h = cat.match_url(ref)
                if h and h[1] in ("chat", "upload", "static"):
                    e.attrs["origin_ai_service"] = h[0]
                    if "origin:ai" not in e.tags:
                        e.tags.append("origin:ai")
        target = e.path or e.title
        if target and cat.is_sensitive(target):
            e.sensitive = True
            e.tags.append("sensitive")
        if e.path:
            ext = cat.ext(e.path)
            if ext in cat.archive_exts:
                e.tags.append("archive")
            if ext in cat.model_exts:
                e.tags.append("local_model")
            if ext in cat.document_exts:
                e.tags.append("document")
        if e.process and cat.is_browser(e.process):
            e.tags.append("browser")
    return events
