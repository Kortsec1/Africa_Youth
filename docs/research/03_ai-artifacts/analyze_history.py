"""Extract visits from a working copy of Chromium History; no action inference."""
import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

HOSTS = {"chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT",
         "claude.ai": "Claude", "gemini.google.com": "Gemini"}


def extract(path):
    path = Path(path).resolve(strict=True)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    # mode=ro respects WAL; never immutable=1 (which can ignore WAL).
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as con:
        con.execute("PRAGMA query_only=ON")
        integrity = con.execute("PRAGMA quick_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("SQLite quick_check failed: " + integrity)
        rows = con.execute("SELECT v.id, v.visit_time, u.url, u.title "
                           "FROM visits v JOIN urls u ON v.url=u.id "
                           "ORDER BY v.visit_time, v.id")
        events = []
        for record_id, raw_time, url, title in rows:
            try:
                parsed = urlsplit(url)
                host = (parsed.hostname or "").lower()
            except ValueError:
                continue
            if parsed.scheme not in {"http", "https"} or host not in HOSTS:
                continue
            event_time = None
            if isinstance(raw_time, int) and raw_time > 0:
                try:
                    event_time = (dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)
                                  + dt.timedelta(microseconds=raw_time)).isoformat()
                except OverflowError:
                    pass
            events.append({"record_id": record_id, "raw_chromium_time": raw_time,
                           "event_time_utc": event_time, "host": host,
                           "service": HOSTS[host], "url": url, "title": title,
                           "time_semantics": "browser_visit_time",
                           "action_claim": "service_visit_record",
                           "evidence_level": "A",
                           "limitations": "Does not prove prompt submission or upload."})
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError("History changed during analysis; obtain a stable working copy")
    return {"dataset_type": "provided_history_not_independently_authenticated",
            "history_sha256": before, "sqlite_version": sqlite3.sqlite_version,
            "events": events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.history)
    # Exclusive creation avoids overwriting evidence or previous results.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
