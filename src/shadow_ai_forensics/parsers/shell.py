"""사용자 파일 열람 흔적: LNK(LECmd), JumpList(JLECmd) CSV 출력.

수집:
    LECmd.exe  -d "%APPDATA%\\Microsoft\\Windows\\Recent" --csv out --csvf lnk.csv
    JLECmd.exe -d "%APPDATA%\\Microsoft\\Windows\\Recent\\AutomaticDestinations" --csv out
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from ..schema import Action, Category, Event
from ..timeutil import parse_ts
from .common import first, join_path, read_csv

LNK_SIGNATURE = {"SourceFile", "SourceCreated", "SourceModified", "LocalPath"}
JUMP_SIGNATURE = {"AppId", "AppIdDescription", "LastModified"}


def sniff_lnk(header: list[str]) -> bool:
    h = set(header)
    return LNK_SIGNATURE <= h and "AppId" not in h


def sniff_jumplist(header: list[str]) -> bool:
    return JUMP_SIGNATURE <= set(header)


def _target(r: dict[str, str]) -> str:
    p = first(r, "LocalPath", "TargetIDAbsolutePath", "Path")
    if not p and r.get("NetworkPath"):
        p = join_path(r["NetworkPath"], r.get("CommonPath", ""))
    return p


def parse_lnk(path: Path, host: str = "") -> list[Event]:
    events: list[Event] = []
    for line, r in read_csv(path):
        target = _target(r)
        if not target:
            continue
        ref = f"{path.name}:{line}"
        attrs = {
            "lnk": r.get("SourceFile", ""),
            "volume_serial": r.get("VolumeSerialNumber", ""),
            "drive_type": r.get("DriveType", ""),
            "machine_id": r.get("MachineID", ""),
            "target_modified": r.get("TargetModified", ""),
            "size": r.get("FileSize", ""),
        }
        created = parse_ts(r.get("SourceCreated"))
        modified = parse_ts(r.get("SourceModified"))
        if created:
            events.append(Event(
                ts=created, source="LNK", category=Category.FILE, action=Action.FILE_OPEN,
                time_meaning="LNK 생성시각 ≈ 대상 파일 최초 열람",
                host=host, path=target, attrs=dict(attrs), raw_ref=ref,
            ))
        if modified and (not created or modified - created > timedelta(seconds=2)):
            events.append(Event(
                ts=modified, source="LNK", category=Category.FILE, action=Action.FILE_OPEN,
                time_meaning="LNK 수정시각 ≈ 대상 파일 마지막 열람",
                host=host, path=target, attrs=dict(attrs), raw_ref=ref + "#m",
            ))
    return events


def parse_jumplist(path: Path, host: str = "") -> list[Event]:
    events: list[Event] = []
    for line, r in read_csv(path):
        target = _target(r)
        ts = parse_ts(r.get("LastModified"))
        if not target or not ts:
            continue
        app = r.get("AppIdDescription", "") or r.get("AppId", "")
        events.append(Event(
            ts=ts, source="JumpList", category=Category.FILE, action=Action.FILE_OPEN,
            time_meaning="DestList 항목 마지막 사용시각 (해당 앱으로 열람)",
            host=host or r.get("Hostname", ""), path=target, raw_ref=f"{path.name}:{line}",
            attrs={
                "app": app,
                "app_id": r.get("AppId", ""),
                "interaction_count": r.get("InteractionCount", ""),
                "first_seen": r.get("CreationTime", ""),
            },
        ))
    return events
