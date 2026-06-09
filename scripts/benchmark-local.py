#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import subprocess
import time


@dataclass(frozen=True)
class Result:
    host: str
    returncode: int
    elapsed_ms: float


def curl_once(host: str, port: int, timeout: float) -> Result:
    started = time.perf_counter()
    result = subprocess.run(
        [
            "curl",
            "--noproxy",
            "*",
            "-sk",
            "--resolve",
            f"{host}:{port}:127.0.0.1",
            f"https://{host}:{port}/",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return Result(host, result.returncode, elapsed_ms)


def run_benchmark(hosts: list[str], port: int, requests: int, concurrency: int, timeout: float) -> list[Result]:
    jobs = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for _ in range(requests):
            for host in hosts:
                jobs.append(pool.submit(curl_once, host, port, timeout))
        return [job.result() for job in as_completed(jobs)]


def render_markdown(results: list[Result]) -> str:
    by_host: dict[str, list[Result]] = {}
    for result in results:
        by_host.setdefault(result.host, []).append(result)

    lines = [
        "# 로컬 프록시 벤치마크 요약",
        "",
        "| Host | 요청 수 | 성공 수 | 실패 수 | 평균 시간(ms) | 최소(ms) | 최대(ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for host in sorted(by_host):
        rows = by_host[host]
        elapsed = [row.elapsed_ms for row in rows]
        success = sum(1 for row in rows if row.returncode == 0)
        fail = len(rows) - success
        avg = round(sum(elapsed) / len(elapsed), 2)
        lines.append(f"| `{host}` | {len(rows)} | {success} | {fail} | {avg} | {min(elapsed)} | {max(elapsed)} |")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run simple curl-based local proxy benchmark")
    parser.add_argument("--port", type=int, default=9443)
    parser.add_argument("--requests", type=int, default=5, help="Requests per host")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--hosts", nargs="+", default=["allowed.test", "blocked.test", "unknown.test"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_benchmark(args.hosts, args.port, args.requests, args.concurrency, args.timeout)
    print(render_markdown(results))


if __name__ == "__main__":
    main()
