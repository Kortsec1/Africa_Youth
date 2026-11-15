"""정규화 이벤트 스키마.

서로 다른 아티팩트(파일시스템, LNK, 브라우저, Sysmon, 텔레메트리 에이전트)를
하나의 타임라인에 올리기 위한 공통 모델이다.

설계 원칙
- 하나의 이벤트 = 하나의 '관찰된 사실'. 추론은 이벤트가 아니라 Finding 에 둔다.
- `time_meaning` 에 타임스탬프가 '무엇의 시각인지'를 반드시 기록한다.
  (예: LNK 의 SourceModified 는 '대상 파일을 마지막으로 연 시각'이지 수정 시각이 아님)
- `raw_ref` 로 원본 파일과 행 번호를 남겨 재현 가능성(검증 가능성)을 확보한다.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .timeutil import iso


class Category(str, Enum):
    FILE = "file"
    WEB = "web"
    PROCESS = "process"
    NETWORK = "network"
    CLIPBOARD = "clipboard"
    WINDOW = "window"


class Action(str, Enum):
    # file
    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    FILE_RENAME = "file_rename"
    FILE_OPEN = "file_open"            # 사용자가 연 흔적 (LNK / JumpList)
    FILE_ACCESS = "file_access"        # $SI 접근시간 등 약한 접근 흔적
    # web
    WEB_VISIT = "web_visit"
    DOWNLOAD = "download"
    WEB_PASTE = "web_paste"            # 웹페이지 paste 이벤트 (Chrome 관측 확장)
    # process / network
    PROCESS_START = "process_start"
    NET_CONNECT = "net_connect"
    DNS_QUERY = "dns_query"
    # endpoint telemetry
    CLIPBOARD_CHANGE = "clipboard_change"
    WINDOW_FOCUS = "window_focus"
    FILE_DIALOG = "file_dialog"        # 열기/업로드 대화상자 포커스


# 출처별 기본 신뢰도: 타임스탬프 신뢰성 + 조작 난이도 + 의미의 명확성
SOURCE_RELIABILITY = {
    "Sysmon": 0.9,
    "USN": 0.85,
    "ChromeHistory": 0.8,
    "FirefoxHistory": 0.8,
    "ChromeDownloads": 0.85,
    "MFT": 0.7,          # $SI 는 타임스톰핑으로 변조 가능
    "LNK": 0.75,
    "JumpList": 0.75,
    "DNSClient": 0.8,
    "Agent": 0.8,
    "RealtimeCollector": 0.85,   # 04 실측 수집기 (C#)
    "ChromePaste": 0.85,         # 04 Chrome 붙여넣기 관측 확장
}


@dataclass
class Event:
    ts: datetime
    source: str                     # 아티팩트 종류 (SOURCE_RELIABILITY 키)
    category: Category
    action: Action
    time_meaning: str               # 이 타임스탬프가 의미하는 바
    host: str = ""
    user: str = ""
    process: str = ""               # 이미지 경로 또는 실행파일명
    pid: int | None = None
    path: str = ""                  # 파일 경로
    url: str = ""
    domain: str = ""
    title: str = ""                 # 웹 페이지 / 창 제목
    attrs: dict[str, Any] = field(default_factory=dict)
    raw_ref: str = ""               # "파일명:행번호"
    # enrichment 단계에서 채워짐
    ai_service: str = ""
    ai_role: str = ""               # chat / api / upload / app / corporate ...
    sensitive: bool = False
    tags: list[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            key = f"{iso(self.ts)}|{self.source}|{self.action}|{self.path}|{self.url}|{self.process}|{self.raw_ref}"
            self.id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]

    @property
    def process_name(self) -> str:
        return self.process.replace("/", "\\").rsplit("\\", 1)[-1].lower()

    @property
    def file_name(self) -> str:
        return self.path.replace("/", "\\").rsplit("\\", 1)[-1]

    @property
    def reliability(self) -> float:
        return SOURCE_RELIABILITY.get(self.source, 0.5)

    def summary(self) -> str:
        target = self.path or self.url or self.domain or self.title or self.process
        who = f" [{self.process_name}]" if self.process and target != self.process else ""
        return f"{self.action.value}: {target}{who}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ts"] = iso(self.ts)
        d["category"] = self.category.value
        d["action"] = self.action.value
        return d


@dataclass
class AISession:
    """AI 서비스 사용 구간. 상관분석의 기준점(anchor)."""
    service: str
    start: datetime
    end: datetime
    channel: str                    # browser / desktop_app / local_llm / api
    events: list[Event] = field(default_factory=list)
    id: str = ""

    @property
    def sources(self) -> set[str]:
        return {e.source for e in self.events}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "service": self.service,
            "channel": self.channel,
            "start": iso(self.start),
            "end": iso(self.end),
            "sources": sorted(self.sources),
            "event_ids": [e.id for e in self.events],
        }


@dataclass
class Finding:
    """탐지 결과. '증거(facts)'와 '추론(inference)'을 분리해 기록한다."""
    rule_id: str
    title: str
    severity: str                   # info / low / medium / high / critical
    confidence: float               # 0.0 ~ 1.0
    ts: datetime
    facts: list[str]                # 아티팩트로 직접 확인되는 사실
    inference: str                  # 사실들로부터 도출한 해석
    alternatives: list[str]         # 같은 사실을 설명하는 다른 가능성(오탐 요인)
    evidence: list[Event] = field(default_factory=list)
    session_id: str = ""
    gaps: list[str] = field(default_factory=list)   # 확정하려면 추가로 필요한 증거
    mitre: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "confidence": round(self.confidence, 2),
            "ts": iso(self.ts),
            "session_id": self.session_id,
            "facts": self.facts,
            "inference": self.inference,
            "alternatives": self.alternatives,
            "gaps": self.gaps,
            "mitre": self.mitre,
            "evidence": [e.id for e in self.evidence],
        }


def dump_jsonl(events: list[Event], path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e.to_dict(), ensure_ascii=False, default=_json_default) + "\n")


def _json_default(o):
    if isinstance(o, datetime):
        return iso(o)
    return str(o)
