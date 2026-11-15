"""시간 변환 유틸리티.

모든 내부 타임스탬프는 timezone-aware UTC datetime 으로 통일한다.
아티팩트마다 기준 epoch 와 단위가 다르므로 변환을 한 곳에 모아 둔다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc
KST = timezone(timedelta(hours=9), "KST")

_WEBKIT_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)   # Chrome/Edge (µs), FILETIME(100ns)
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def from_webkit(us: int | str | None) -> datetime | None:
    """Chromium 계열 History DB 시간(1601-01-01 기준 마이크로초)."""
    if us in (None, "", 0, "0"):
        return None
    return _WEBKIT_EPOCH + timedelta(microseconds=int(us))


def to_webkit(dt: datetime) -> int:
    return int((dt - _WEBKIT_EPOCH) / timedelta(microseconds=1))


def from_filetime(ft: int | str | None) -> datetime | None:
    """Windows FILETIME(1601-01-01 기준 100ns 단위)."""
    if ft in (None, "", 0, "0"):
        return None
    return _WEBKIT_EPOCH + timedelta(microseconds=int(ft) // 10)


def from_unix_us(us: int | str | None) -> datetime | None:
    """Firefox places.sqlite 시간(Unix epoch 마이크로초)."""
    if us in (None, "", 0, "0"):
        return None
    return _UNIX_EPOCH + timedelta(microseconds=int(us))


_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


def parse_ts(value: str | None, assume_tz=UTC) -> datetime | None:
    """EZ Tools CSV / ISO8601 / Sysmon UtcTime 등 문자열 타임스탬프 파싱.

    EZ Tools(MFTECmd, LECmd, JLECmd, EvtxECmd)는 기본적으로 UTC 로 출력하며
    소수점 7자리(100ns)를 쓰기도 하므로 6자리로 잘라 파싱한다.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or s in ("-", "0001-01-01 00:00:00"):
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = None
        base = s
        if "." in s:
            head, frac = s.rsplit(".", 1)
            digits = "".join(ch for ch in frac if ch.isdigit())
            base = f"{head}.{digits[:6].ljust(6, '0')}"
        for fmt in _FORMATS:
            try:
                dt = datetime.strptime(base, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=assume_tz)
    return dt.astimezone(UTC)


def fmt_kst(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")


def iso(dt: datetime | None) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z") if dt else ""
