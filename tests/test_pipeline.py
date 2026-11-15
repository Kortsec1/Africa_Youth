"""가상 시나리오(tools/generate_synthetic.py) 기반 회귀 테스트.

시나리오에 심어 둔 정답(ground truth)을 엔진이 찾아내는지, 그리고 정상 행위를 오탐하지 않는지 검증한다.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from shadow_ai_forensics.catalog import load_catalog
from shadow_ai_forensics.correlate import analyze_path
from shadow_ai_forensics.parsers import detect
from shadow_ai_forensics.parsers.common import norm_path
from shadow_ai_forensics.report import write_all
from shadow_ai_forensics.timeutil import from_webkit, parse_ts, to_webkit

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def scenario(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("scn") / "scenario01"
    subprocess.run([sys.executable, str(ROOT / "tools" / "generate_synthetic.py"), "-o", str(out)], check=True)
    return out


@pytest.fixture(scope="session")
def result(scenario):
    return analyze_path(scenario)


def by_rule(res, rid):
    return [f for f in res.findings if f.rule_id == rid]


# ---------------------------------------------------------------- 단위
def test_time_conversions():
    dt = datetime(2026, 11, 10, 5, 1, 19, tzinfo=timezone.utc)
    assert from_webkit(to_webkit(dt)) == dt
    assert parse_ts("2026-11-10 05:01:19.1234567") == datetime(2026, 11, 10, 5, 1, 19, 123456, tzinfo=timezone.utc)
    assert parse_ts("2026-11-10T05:01:19Z") == dt
    assert parse_ts("") is None


def test_norm_path_across_tools():
    assert norm_path(r".\Users\kim\Downloads\a.py") == norm_path(r"C:\Users\kim\Downloads\a.py")


def test_catalog_roles():
    cat = load_catalog()
    assert cat.match_domain("ws.chatgpt.com") == ("ChatGPT", "chat")
    assert cat.match_domain("files.oaiusercontent.com") == ("ChatGPT", "upload")
    assert cat.match_domain("openai.com") == ("ChatGPT", "corporate")
    assert cat.match_domain("chat.openai.com") == ("ChatGPT", "chat")      # 긴 접미사 우선
    assert cat.match_domain("notchatgpt.com") is None                       # 접미사 경계 확인
    assert cat.match_title("ChatGPT - Chrome", "chrome.exe") == ("ChatGPT", "chat")


# ---------------------------------------------------------------- 형식 판별
def test_detect_all_formats(scenario):
    kinds = {p.name: detect(p) for p in scenario.rglob("*") if p.is_file()}
    assert kinds["mft.csv"] == "mft"
    assert kinds["usn.csv"] == "usn"
    assert kinds["lnk.csv"] == "lnk"
    assert kinds["jumplist_AutomaticDestinations.csv"] == "jumplist"
    assert kinds["sysmon_evtxecmd.csv"] == "evtxecmd"
    assert kinds["agent.jsonl"] == "agent"
    assert kinds["History"] == "chromium"
    assert kinds["README.md"] is None


# ---------------------------------------------------------------- 세션
def test_sessions(result):
    got = {(s.service, s.channel) for s in result.sessions}
    assert ("ChatGPT", "browser") in got
    assert ("Claude", "browser") in got
    assert ("ChatGPT", "api") in got
    assert ("LM Studio", "local_llm") in got
    # 여러 출처(Agent·ChromeHistory·Sysmon)가 한 세션으로 합쳐져야 함 (호스트 누락으로 분리되면 안 됨)
    chat = [s for s in result.sessions if s.service == "ChatGPT" and s.channel == "browser"]
    assert len(chat) == 1 and {"Agent", "ChromeHistory", "Sysmon"} <= chat[0].sources


def test_corporate_site_is_not_usage(result):
    """10:20 openai.com/news 방문은 '사용'이 아니므로 세션이 생기면 안 된다."""
    for s in result.sessions:
        assert not any("openai.com/news" in e.url for e in s.events)


# ---------------------------------------------------------------- 탐지 (정답)
def test_clipboard_to_ai(result):
    f = by_rule(result, "SAI-003")
    assert len(f) == 1                      # Agent + Sysmon EID24 는 하나로 병합
    assert f[0].severity == "high" and "excel" in f[0].facts[0].lower()


def test_notepad_copy_not_flagged(result):
    """09:30 메모장 복사 후 Outlook 전환 → AI 와 무관하므로 탐지되면 안 된다."""
    assert all("notepad" not in " ".join(f.facts).lower() for f in by_rule(result, "SAI-003"))


def test_upload(result):
    f = by_rule(result, "SAI-004")
    assert len(f) == 1 and "영업자료_고객DB.zip" in f[0].title
    assert f[0].confidence >= 0.8           # 대화상자 + LNK + 업로드 엔드포인트 3중 일치


def test_download_and_exec(result):
    dl = by_rule(result, "SAI-005")
    ex = by_rule(result, "SAI-006")
    assert len(dl) == 1 and "report_automation.py" in dl[0].title
    assert {"ChromeDownloads", "MFT", "Sysmon", "USN"} <= {e.source for e in dl[0].evidence}
    assert len(ex) == 1 and ex[0].severity == "high"


def test_staging_and_cleanup(result):
    st = by_rule(result, "SAI-008")
    assert len(st) == 1 and st[0].severity == "high"     # 업로드와 연결됐으므로 상향
    deleted = {f.title.split(": ")[-1] for f in by_rule(result, "SAI-009")}
    assert deleted == {"report_automation.py", "영업자료_고객DB.zip"}


def test_local_llm(result):
    names = {f.title.split(": ")[-1] for f in by_rule(result, "SAI-007")}
    assert names == {"Ollama", "LM Studio"}              # .gguf 파일은 경로로 LM Studio 에 귀속


def test_old_files_not_correlated(result):
    """10월에 열었던 2025_예산안_old.xlsx 는 어떤 세션과도 연결되면 안 된다."""
    for f in result.findings:
        assert not any("2025_예산안" in e.path for e in f.evidence)


def test_every_fact_has_source_reference(result):
    for f in result.findings:
        assert f.facts and f.inference and f.alternatives
        assert 0 < f.confidence <= 0.95
        if f.rule_id != "SAI-001":
            assert any("[" in x and ":" in x for x in f.facts)


def test_report_outputs(result, tmp_path):
    paths = write_all(result, tmp_path)
    html = paths["report"].read_text(encoding="utf-8")
    assert "Shadow AI Forensics Report" in html and "/*__DATA__*/" not in html
    assert paths["timeline"].stat().st_size > 0


def test_winevent_jsonl_from_collector(tmp_path):
    """collect_artifacts.ps1 가 내보내는 Get-WinEvent JSONL 형식 파싱."""
    import json
    p = tmp_path / "sysmon.jsonl"
    rec = {"TimeCreated": "2026-11-10T05:01:18.0000000Z", "Id": 22, "ProviderName": "Microsoft-Windows-Sysmon",
           "MachineName": "FIN-PC-07", "RecordId": 1,
           "EventData": {"UtcTime": "2026-11-10 05:01:18.123", "Image": r"C:\x\chrome.exe",
                         "QueryName": "chatgpt.com", "QueryResults": "::ffff:1.2.3.4;", "ProcessId": "4120"}}
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    assert detect(p) == "winevent"
    from shadow_ai_forensics.parsers.eventlog import parse_winevent_jsonl
    ev = parse_winevent_jsonl(p)
    assert len(ev) == 1 and ev[0].domain == "chatgpt.com" and ev[0].pid == 4120
