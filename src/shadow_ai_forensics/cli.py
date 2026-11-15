"""명령행 인터페이스.

  python -m shadow_ai_forensics analyze <수집폴더> -o <출력폴더> [--host PC명] [--since ISO] [--until ISO]
  python -m shadow_ai_forensics detect  <수집폴더>          # 형식 자동판별 결과만 출력
  python -m shadow_ai_forensics rules                         # 규칙 목록
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .correlate import SEVERITY_ORDER, analyze_path
from .correlate.rules import RULES
from .parsers import detect
from .report import write_all
from .timeutil import fmt_kst, parse_ts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="saf", description="Shadow AI Forensics - 아티팩트 상관분석")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="수집 폴더 분석 후 리포트 생성")
    a.add_argument("input", type=Path)
    a.add_argument("-o", "--out", type=Path, default=Path("out"))
    a.add_argument("--host", default="")
    a.add_argument("--catalog", help="AI 서비스 카탈로그 TOML 경로 (기본: 내장)")
    a.add_argument("--since", help="분석 시작 시각 (ISO8601, 시간대 없으면 UTC)")
    a.add_argument("--until", help="분석 종료 시각")
    d = sub.add_parser("detect", help="입력 파일 형식 판별")
    d.add_argument("input", type=Path)
    sub.add_parser("rules", help="탐지 규칙 목록")
    args = ap.parse_args(argv)

    if args.cmd == "rules":
        for rid, name, fn in RULES:
            print(f"{rid:<12} {name}  — {(fn.__doc__ or '').strip().splitlines()[0] if fn.__doc__ else ''}")
        return 0
    if args.cmd == "detect":
        files = [args.input] if args.input.is_file() else sorted(p for p in args.input.rglob("*") if p.is_file())
        for p in files:
            print(f"{detect(p) or '-':<10} {p}")
        return 0

    if not args.input.exists():
        print(f"입력 경로가 없습니다: {args.input}", file=sys.stderr)
        return 2
    res = analyze_path(args.input, host=args.host, catalog=args.catalog,
                       since=parse_ts(args.since), until=parse_ts(args.until))
    paths = write_all(res, args.out)
    print(f"[+] 입력 {len(res.inventory)}개 파일 → 이벤트 {len(res.events)}건, AI 세션 {len(res.sessions)}개, "
          f"탐지 {len(res.findings)}건")
    for s in res.sessions:
        print(f"    {s.id} {s.service:<10} {s.channel:<12} {fmt_kst(s.start)} ~ {fmt_kst(s.end)}")
    for f in sorted(res.findings, key=lambda f: (-SEVERITY_ORDER[f.severity], f.ts)):
        if f.severity != "info":
            print(f"    [{f.severity:<6}] {f.rule_id} {fmt_kst(f.ts)} conf={f.confidence:.2f} {f.title}")
    print(f"[+] 리포트: {paths['report']}")
    return 0
