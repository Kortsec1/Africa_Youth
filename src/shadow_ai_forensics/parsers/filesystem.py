"""NTFS 아티팩트 파서: MFTECmd 의 $MFT CSV, $J($UsnJrnl) CSV 출력.

수집: FTK Imager / KAPE 로 $MFT, $Extend\\$UsnJrnl:$J 추출 후
    MFTECmd.exe -f $MFT --csv out --csvf mft.csv
    MFTECmd.exe -f $J -m $MFT --csv out --csvf usn.csv   (-m 을 주어야 ParentPath 가 복원됨)
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from ..schema import Action, Category, Event
from ..timeutil import parse_ts
from .common import first, join_path, parse_kv_block, read_csv, truthy

MFT_SIGNATURE = {"EntryNumber", "ParentPath", "FileName", "Created0x10"}
USN_SIGNATURE = {"UpdateTimestamp", "UpdateReasons", "Name"}


def sniff_mft(header: list[str]) -> bool:
    return MFT_SIGNATURE <= set(header)


def sniff_usn(header: list[str]) -> bool:
    return USN_SIGNATURE <= set(header)


def parse_mft(path: Path, host: str = "", user_paths_only: bool = True) -> list[Event]:
    events: list[Event] = []
    for line, r in read_csv(path):
        if truthy(r.get("IsDirectory", "")):
            continue
        parent = r.get("ParentPath", "")
        if user_paths_only and "\\users\\" not in parent.lower() + "\\":
            continue
        fpath = join_path(parent, r.get("FileName", ""))
        ref = f"{path.name}:{line}"
        attrs = {
            "entry": r.get("EntryNumber", ""),
            "in_use": r.get("InUse", ""),
            "size": r.get("FileSize", ""),
            "si_lt_fn": truthy(r.get("SI<FN", "")),       # 타임스톰핑 의심 지표
            "copied": truthy(r.get("Copied", "")),        # 생성 > 수정 : 복사 흔적
            "fn_created": r.get("Created0x30", ""),
        }
        zone = r.get("ZoneIdContents", "")
        if zone:
            kv = parse_kv_block(zone)
            attrs["zone_id"] = kv.get("zoneid", "")
            if kv.get("hosturl"):
                attrs["host_url"] = kv["hosturl"]
            if kv.get("referrerurl"):
                attrs["zone_referrer"] = kv["referrerurl"]
        created = parse_ts(r.get("Created0x10"))
        modified = parse_ts(r.get("LastModified0x10"))
        if created:
            events.append(Event(
                ts=created, source="MFT", category=Category.FILE, action=Action.FILE_CREATE,
                time_meaning="$SI 생성시각 (복사 시 복사 시각, 타임스톰핑 가능)",
                host=host, path=fpath, attrs=dict(attrs), raw_ref=ref,
            ))
        if modified and (not created or abs(modified - created) > timedelta(seconds=2)):
            events.append(Event(
                ts=modified, source="MFT", category=Category.FILE, action=Action.FILE_MODIFY,
                time_meaning="$SI 내용 수정시각 (복사 시 원본 수정시각이 유지됨)",
                host=host, path=fpath, attrs=dict(attrs), raw_ref=ref + "#m",
            ))
    return events


def _usn_action(reasons: str) -> Action | None:
    r = reasons.lower()
    if "filedelete" in r:
        return Action.FILE_DELETE
    if "filecreate" in r:
        return Action.FILE_CREATE
    if "renamenewname" in r:
        return Action.FILE_RENAME
    if "dataoverwrite" in r or "dataextend" in r or "datatruncation" in r:
        return Action.FILE_MODIFY
    return None   # Close / BasicInfoChange / SecurityChange 등은 노이즈로 제외


def parse_usn(path: Path, host: str = "") -> list[Event]:
    events: list[Event] = []
    last_seen: dict[tuple[str, Action], object] = {}
    for line, r in read_csv(path):
        action = _usn_action(r.get("UpdateReasons", ""))
        if not action:
            continue
        ts = parse_ts(r.get("UpdateTimestamp"))
        if not ts:
            continue
        fpath = join_path(r.get("ParentPath", ""), r.get("Name", ""))
        key = (fpath.lower(), action)
        prev = last_seen.get(key)
        # 하나의 작업이 여러 USN 레코드(FileCreate, FileCreate|DataExtend, ...|Close)로 남으므로 2초 내 중복 제거
        if prev is not None and abs(ts - prev) <= timedelta(seconds=2):
            continue
        last_seen[key] = ts
        meaning = {
            Action.FILE_CREATE: "USN FileCreate 기록시각",
            Action.FILE_DELETE: "USN FileDelete 기록시각",
            Action.FILE_RENAME: "USN RenameNewName 기록시각",
            Action.FILE_MODIFY: "USN 데이터 변경 기록시각",
        }[action]
        events.append(Event(
            ts=ts, source="USN", category=Category.FILE, action=action, time_meaning=meaning,
            host=host, path=fpath, raw_ref=f"{path.name}:{line}",
            attrs={
                "reasons": r.get("UpdateReasons", ""),
                "usn": first(r, "UpdateSequenceNumber"),
                "entry": r.get("EntryNumber", ""),
            },
        ))
    return events
