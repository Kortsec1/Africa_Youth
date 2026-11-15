"""파서 공통 유틸리티."""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Iterator

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

_DRIVE = re.compile(r"^[a-z]:", re.I)


def read_csv(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    """BOM 을 처리하며 (행번호, dict) 를 순회. 행번호는 헤더 다음 행이 2."""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            yield i, {(k or "").strip(): (v or "").strip() for k, v in row.items()}


def csv_header(path: Path) -> list[str]:
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            return [h.strip() for h in next(csv.reader(f), [])]
    except (OSError, StopIteration):
        return []


def first(row: dict[str, str], *names: str) -> str:
    for n in names:
        v = row.get(n)
        if v:
            return v
    return ""


def truthy(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "y")


def join_path(parent: str, name: str) -> str:
    parent = (parent or "").rstrip("\\/")
    if not parent:
        return name
    return f"{parent}\\{name}"


def norm_path(p: str) -> str:
    """서로 다른 아티팩트의 경로 표기를 비교 가능하게 정규화.

    MFTECmd: '.\\Users\\kim\\Downloads\\a.py'   LECmd: 'C:\\Users\\kim\\Downloads\\a.py'
    → '\\users\\kim\\downloads\\a.py'
    """
    s = (p or "").replace("/", "\\").strip().strip('"').lower()
    s = _DRIVE.sub("", s)
    if s.startswith(".\\"):
        s = s[1:]
    if s and not s.startswith("\\"):
        s = "\\" + s
    return s


def parse_kv_block(text: str) -> dict[str, str]:
    """Zone.Identifier 같은 INI 형식 텍스트 → dict."""
    out: dict[str, str] = {}
    for line in re.split(r"\r\n|\n|\\r\\n|\\n", text or ""):
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out
