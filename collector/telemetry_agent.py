"""엔드포인트 텔레메트리 에이전트 (Windows, 표준 라이브러리 + ctypes).

포렌식 아티팩트만으로는 남지 않는 두 가지를 실시간으로 기록한다.
  1) 포그라운드 창 전환  : 언제 어떤 앱/창(제목·클래스)을 보고 있었는가
                           - 창 클래스 '#32770' = 표준 대화상자 → 브라우저 소유면 파일 선택(업로드) 창
  2) 클립보드 변경       : 언제 어떤 프로세스가 클립보드에 썼는가 (+ 텍스트 길이, SHA-256)

개인정보 보호 설계 (docs/research/04_endpoint-telemetry 참고)
  - 클립보드 '내용'은 저장하지 않는다. 길이와 해시만 남겨 원본 문서와의 대조만 가능하게 한다.
  - --store-preview 를 주면 앞 40자만 저장 (실험 환경 전용, 운영 금지)
  - 창 제목에는 파일명·메일 제목이 포함될 수 있으므로 수집 고지/동의가 필요하다.

실행:  python telemetry_agent.py [--out C:\\ProgramData\\ShadowAIAgent\\agent.jsonl] [--interval 0.5]
출력 형식은 src/shadow_ai_forensics/parsers/agent.py 가 읽는다.

⚠ 리눅스에서 작성되어 실제 Windows 동작은 미검증. 04 실험에서 검증 후 results.md 에 기록할 것.
   폴링 방식(GetForegroundWindow / GetClipboardSequenceNumber)이라 0.5초 미만의 짧은 전환은 놓칠 수 있다.
   이벤트 방식(SetWinEventHook, AddClipboardFormatListener)으로의 개선은 추가 연구 사항.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import socket
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone

if sys.platform != "win32":
    sys.exit("Windows 전용 에이전트입니다.")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
user32.GetClipboardOwner.restype = wintypes.HWND
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.EnumClipboardFormats.argtypes = [wintypes.UINT]
user32.EnumClipboardFormats.restype = wintypes.UINT
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
CF_UNICODETEXT = 13
CF_NAMES = {1: "CF_TEXT", 2: "CF_BITMAP", 7: "CF_OEMTEXT", 8: "CF_DIB", 13: "CF_UNICODETEXT",
            15: "CF_HDROP", 16: "CF_LOCALE", 17: "CF_DIBV5"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def window_info(hwnd) -> dict:
    if not hwnd:
        return {}
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {"title": buf.value, "class": cls.value, "pid": pid.value, "process": image_of(pid.value)}


def image_of(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


def clipboard_snapshot(store_preview: bool) -> dict:
    """클립보드 형식 목록과 텍스트 길이/해시. 다른 프로세스가 열고 있으면 몇 번 재시도."""
    for _ in range(5):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return {"error": "OpenClipboard failed"}
    try:
        formats, fmt = [], 0
        while True:
            fmt = user32.EnumClipboardFormats(fmt)
            if not fmt:
                break
            formats.append(CF_NAMES.get(fmt, str(fmt)))
        out = {"formats": formats}
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if h:
            p = kernel32.GlobalLock(h)
            if p:
                try:
                    text = ctypes.wstring_at(p)
                    out["length"] = len(text)
                    out["sha256"] = hashlib.sha256(text.encode("utf-16-le")).hexdigest()
                    if store_preview:
                        out["preview"] = text[:40]
                finally:
                    kernel32.GlobalUnlock(h)
        return out
    finally:
        user32.CloseClipboard()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.environ.get("ProgramData", "."), "ShadowAIAgent", "agent.jsonl"))
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--store-preview", action="store_true", help="실험 전용: 클립보드 앞 40자 저장")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    host, user = socket.gethostname(), os.environ.get("USERNAME", "")
    last_hwnd, last_title = None, None
    last_seq = user32.GetClipboardSequenceNumber()
    last_focus: dict = {}
    print(f"[agent] logging to {args.out} (Ctrl+C to stop)")
    with open(args.out, "a", encoding="utf-8") as f:
        def emit(rec: dict) -> None:
            rec.update({"host": host, "user": user})
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()

        try:
            while True:
                hwnd = user32.GetForegroundWindow()
                info = window_info(hwnd)
                # 같은 창이라도 제목이 바뀌면(탭 전환, 대화 제목 변경) 기록
                if hwnd != last_hwnd or info.get("title") != last_title:
                    if info:
                        emit({"ts": now(), "type": "window_focus", **info})
                        last_focus = info
                    last_hwnd, last_title = hwnd, info.get("title")
                seq = user32.GetClipboardSequenceNumber()
                if seq != last_seq:
                    last_seq = seq
                    owner = window_info(user32.GetClipboardOwner())
                    # 소유 창이 없는 앱도 많으므로 포그라운드 창을 출처로 보조 기록
                    src = owner if owner.get("process") else last_focus
                    emit({"ts": now(), "type": "clipboard_change", "seq": seq,
                          "process": src.get("process", ""), "pid": src.get("pid"),
                          "source_title": src.get("title", ""), "owner_known": bool(owner.get("process")),
                          **clipboard_snapshot(args.store_preview)})
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("[agent] stopped")


if __name__ == "__main__":
    main()
