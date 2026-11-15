"""Windows 이벤트 로그 파서 (Sysmon, DNS-Client).

지원 입력
1) EvtxECmd CSV : EvtxECmd.exe -f Microsoft-Windows-Sysmon%4Operational.evtx --csv out
   - Payload 컬럼에 {"EventData":{"Data":[{"@Name":..,"#text":..}]}} JSON 이 들어있다.
2) JSONL        : collector/collect_artifacts.ps1 가 Get-WinEvent 로 내보낸 형식
   - {"TimeCreated": ..., "Id": 1, "ProviderName": ..., "MachineName": ..., "EventData": {...}}
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from ..schema import Action, Category, Event
from ..timeutil import parse_ts
from .common import parse_kv_block, read_csv

EVTXECMD_SIGNATURE = {"TimeCreated", "EventId", "Provider", "Payload"}

SYSMON = "microsoft-windows-sysmon"
DNSCLIENT = "microsoft-windows-dns-client"


def sniff_evtxecmd(header: list[str]) -> bool:
    return EVTXECMD_SIGNATURE <= set(header)


def _payload_to_dict(payload: str) -> dict[str, str]:
    if not payload:
        return {}
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    data = obj.get("EventData", obj).get("Data", []) if isinstance(obj, dict) else []
    if isinstance(data, dict):
        data = [data]
    out = {}
    for d in data:
        if isinstance(d, dict) and "@Name" in d:
            out[d["@Name"]] = str(d.get("#text", ""))
    return out


def _dns_names(results: str) -> list[str]:
    # QueryResults 예: "type:  5 chatgpt.com.cdn.cloudflare.net;::ffff:104.18.32.47;"
    return [p.strip() for p in (results or "").split(";") if p.strip()]


def to_event(provider: str, eid: int, ed: dict[str, str], created: str, host: str, ref: str) -> Event | None:
    prov = provider.lower()
    ts = parse_ts(ed.get("UtcTime")) or parse_ts(created)
    if not ts:
        return None
    image = ed.get("Image", "")
    pid = int(ed["ProcessId"]) if ed.get("ProcessId", "").isdigit() else None
    common = dict(ts=ts, host=host, process=image, pid=pid, raw_ref=ref, user=ed.get("User", ""))

    if prov == SYSMON:
        if eid == 1:
            return Event(source="Sysmon", category=Category.PROCESS, action=Action.PROCESS_START,
                         time_meaning="Sysmon EID 1 프로세스 생성 시각",
                         attrs={"command_line": ed.get("CommandLine", ""), "parent": ed.get("ParentImage", ""),
                                "hashes": ed.get("Hashes", ""), "guid": ed.get("ProcessGuid", ""),
                                "original_name": ed.get("OriginalFileName", "")}, **common)
        if eid == 3:
            dst = ed.get("DestinationHostname", "") or ed.get("DestinationIp", "")
            return Event(source="Sysmon", category=Category.NETWORK, action=Action.NET_CONNECT,
                         time_meaning="Sysmon EID 3 연결 시각", domain=ed.get("DestinationHostname", ""),
                         attrs={"dst_ip": ed.get("DestinationIp", ""), "dst_port": ed.get("DestinationPort", ""),
                                "dst": dst}, **common)
        if eid == 11:
            return Event(source="Sysmon", category=Category.FILE, action=Action.FILE_CREATE,
                         time_meaning="Sysmon EID 11 파일 생성 시각", path=ed.get("TargetFilename", ""),
                         attrs={}, **common)
        if eid == 15:
            # Zone.Identifier ADS 생성 = 인터넷에서 받은 파일 (MotW). Sysmon 13+ 는 Contents 포함
            target = ed.get("TargetFilename", "")
            kv = parse_kv_block(ed.get("Contents", ""))
            attrs = {"stream": True}
            if kv.get("hosturl"):
                attrs["host_url"] = kv["hosturl"]
            if kv.get("referrerurl"):
                attrs["zone_referrer"] = kv["referrerurl"]
            return Event(source="Sysmon", category=Category.FILE, action=Action.FILE_CREATE,
                         time_meaning="Sysmon EID 15 Zone.Identifier 스트림 생성 시각",
                         path=target.split(":Zone.Identifier")[0], attrs=attrs, **common)
        if eid == 22:
            q = ed.get("QueryName", "")
            return Event(source="Sysmon", category=Category.NETWORK, action=Action.DNS_QUERY,
                         time_meaning="Sysmon EID 22 DNS 질의 시각", domain=q,
                         attrs={"results": _dns_names(ed.get("QueryResults", "")),
                                "status": ed.get("QueryStatus", "")}, **common)
        if eid in (23, 26):
            return Event(source="Sysmon", category=Category.FILE, action=Action.FILE_DELETE,
                         time_meaning=f"Sysmon EID {eid} 파일 삭제 시각", path=ed.get("TargetFilename", ""),
                         attrs={"archived": eid == 23}, **common)
        if eid == 24:
            return Event(source="Sysmon", category=Category.CLIPBOARD, action=Action.CLIPBOARD_CHANGE,
                         time_meaning="Sysmon EID 24 클립보드 변경 시각",
                         attrs={"hashes": ed.get("Hashes", ""), "archived": ed.get("Archived", ""),
                                "client": ed.get("ClientInfo", "")}, **common)
        return None
    if prov == DNSCLIENT and eid in (3006, 3008, 3020):
        q = ed.get("QueryName", "")
        return Event(source="DNSClient", category=Category.NETWORK, action=Action.DNS_QUERY,
                     time_meaning=f"DNS-Client/Operational EID {eid} 시각", domain=q,
                     attrs={"results": _dns_names(ed.get("QueryResults", ""))}, **common)
    return None


def parse_evtxecmd(path: Path, host: str = "") -> list[Event]:
    events = []
    for line, r in read_csv(path):
        try:
            eid = int(r.get("EventId", "0"))
        except ValueError:
            continue
        ev = to_event(r.get("Provider", ""), eid, _payload_to_dict(r.get("Payload", "")),
                      r.get("TimeCreated", ""), host or r.get("Computer", ""), f"{path.name}:{line}")
        if ev:
            events.append(ev)
    return events


def sniff_winevent_jsonl(first_obj: dict) -> bool:
    return {"Id", "ProviderName", "EventData"} <= set(first_obj)


def parse_winevent_jsonl(path: Path, host: str = "") -> list[Event]:
    events = []
    with open(path, encoding="utf-8-sig") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            ev = to_event(o.get("ProviderName", ""), int(o.get("Id", 0)), o.get("EventData", {}) or {},
                          str(o.get("TimeCreated", "")), host or o.get("MachineName", ""), f"{path.name}:{i}")
            if ev:
                events.append(ev)
    return events


def url_host(u: str) -> str:
    return urlsplit(u).hostname or ""
