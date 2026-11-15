"""분석 결과 출력: JSON, 타임라인 CSV, Markdown 요약, HTML 리포트."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from ..correlate import SEVERITY_ORDER, Result
from ..schema import dump_jsonl
from ..timeutil import fmt_kst, iso
from .html import render_html


def write_all(res: Result, out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "events": out / "events.jsonl",
        "timeline": out / "timeline.csv",
        "findings": out / "findings.json",
        "summary": out / "summary.md",
        "report": out / "report.html",
    }
    dump_jsonl(res.events, paths["events"])
    with open(paths["timeline"], "w", newline="", encoding="utf-8-sig") as f:   # Excel 한글 호환
        w = csv.writer(f)
        w.writerow(["time_kst", "time_utc", "source", "action", "ai_service", "process", "target",
                    "time_meaning", "tags", "raw_ref", "event_id"])
        for e in res.events:
            w.writerow([fmt_kst(e.ts), iso(e.ts), e.source, e.action.value, e.ai_service, e.process,
                        e.path or e.url or e.domain or e.title, e.time_meaning, ";".join(e.tags), e.raw_ref, e.id])
    paths["findings"].write_text(json.dumps({
        "host": res.host,
        "sessions": [s.to_dict() for s in res.sessions],
        "findings": [f.to_dict() for f in res.findings],
        "inventory": res.inventory,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["summary"].write_text(render_markdown(res), encoding="utf-8")
    paths["report"].write_text(render_html(res), encoding="utf-8")
    return paths


def render_markdown(res: Result) -> str:
    lines = [f"# Shadow AI 분석 요약 — {res.host or '(host 미상)'}", ""]
    if res.events:
        lines.append(f"- 분석 구간: {fmt_kst(res.events[0].ts)} ~ {fmt_kst(res.events[-1].ts)} (KST)")
    lines += [f"- 정규화 이벤트: {len(res.events)}건 / AI 세션: {len(res.sessions)}개 / 탐지: {len(res.findings)}건", ""]
    lines += ["## AI 사용 세션", "", "| ID | 서비스 | 채널 | 시작(KST) | 종료(KST) | 출처 |", "|---|---|---|---|---|---|"]
    for s in res.sessions:
        lines.append(f"| {s.id} | {s.service} | {s.channel} | {fmt_kst(s.start)} | {fmt_kst(s.end)} | "
                     f"{', '.join(sorted(s.sources))} |")
    lines += ["", "## 탐지 결과 (심각도순)", ""]
    for f in sorted(res.findings, key=lambda f: (-SEVERITY_ORDER[f.severity], f.ts)):
        lines += [f"### [{f.severity.upper()}] {f.rule_id} {f.title}",
                  f"- 시각: {fmt_kst(f.ts)} / 신뢰도: {f.confidence:.2f} / 세션: {f.session_id or '-'}",
                  "- **확인된 사실 (증거)**"]
        lines += [f"  - {x}" for x in f.facts]
        lines += [f"- **추론**: {f.inference}", "- **다른 가능성 (오탐 요인)**"]
        lines += [f"  - {x}" for x in f.alternatives]
        if f.gaps:
            lines += ["- **확정에 필요한 추가 증거**"] + [f"  - {x}" for x in f.gaps]
        lines.append("")
    lines += ["## 입력 아티팩트", ""] + [f"- `{k}` → {v}" for k, v in res.inventory.items()]
    return "\n".join(lines) + "\n"
