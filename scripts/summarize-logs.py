#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean
from typing import Any


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def count_by(events: list[dict[str, Any]], key: str) -> Counter[str]:
    return Counter(str(event.get(key) if event.get(key) is not None else "not_recorded") for event in events)


def field_value(event: dict[str, Any], key: str) -> str:
    value = event.get(key)
    return str(value if value is not None else "not_recorded")


def table(title: str, rows: list[tuple[str, int]]) -> str:
    lines = [f"## {title}", "", "| 항목 | 건수 |", "| --- | ---: |"]
    lines.extend(f"| `{name}` | {count} |" for name, count in rows)
    return "\n".join(lines)


def summarize(events: list[dict[str, Any]]) -> str:
    elapsed_values = [event["elapsed_ms"] for event in events if isinstance(event.get("elapsed_ms"), int | float)]
    bytes_c2u = sum(int(event.get("bytes_client_to_upstream") or 0) for event in events)
    bytes_u2c = sum(int(event.get("bytes_upstream_to_client") or 0) for event in events)

    lines = [
        "# 프록시 로그 요약",
        "",
        "## 전체 요약",
        "",
        "| 지표 | 값 |",
        "| --- | ---: |",
        f"| 총 연결 수 | {len(events)} |",
        f"| 평균 처리 시간(ms) | {round(mean(elapsed_values), 2) if elapsed_values else 0} |",
        f"| 클라이언트→업스트림 바이트 | {bytes_c2u} |",
        f"| 업스트림→클라이언트 바이트 | {bytes_u2c} |",
        "",
        table("정책 결정별 건수", count_by(events, "decision").most_common()),
        "",
        table("연결 결과별 건수", count_by(events, "connection_outcome").most_common()),
        "",
        table("SNI별 건수", count_by(events, "extracted_sni").most_common()),
        "",
        table("파싱 오류별 건수", count_by(events, "parse_error_type").most_common()),
        "",
        "## SNI와 정책 결정 교차표",
        "",
        "| SNI | allow | block | error |",
        "| --- | ---: | ---: | ---: |",
    ]

    cross: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        cross[field_value(event, "extracted_sni")][field_value(event, "decision")] += 1
    for sni in sorted(cross):
        counts = cross[sni]
        lines.append(f"| `{sni}` | {counts['allow']} | {counts['block']} | {counts['error']} |")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize proxy JSONL logs as Markdown")
    parser.add_argument("log_file", type=Path, help="Path to proxy JSONL log file")
    parser.add_argument("-o", "--output", type=Path, help="Optional Markdown output file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = summarize(load_events(args.log_file))
    if args.output:
        args.output.write_text(summary + "\n", encoding="utf-8")
    else:
        print(summary)


if __name__ == "__main__":
    main()
