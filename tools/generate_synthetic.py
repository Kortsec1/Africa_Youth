#!/usr/bin/env python3
"""가상 시나리오 데이터 생성기.

실제 Windows 실험 전에 상관분석 엔진을 검증하기 위해, 실제 도구 출력과 '같은 형식'의 파일을 만든다.
  - MFTECmd  : mft.csv, usn.csv
  - LECmd    : lnk.csv
  - JLECmd   : jumplist_AutomaticDestinations.csv
  - Chrome   : Chrome/History (SQLite)
  - EvtxECmd : sysmon_evtxecmd.csv
  - 에이전트  : agent.jsonl

⚠ 이 데이터는 '가상'이다. 실험 결과(results.md)로 인용하지 말 것.
   실제 실험 데이터는 docs/research/*/samples 에 별도로 수집한다.

시나리오 (2026-11-10, FIN-PC-07, 사용자 kim.analyst)
  [정상] 09:05 네이버 방문, 09:10 회의록 열람, 09:30 메모장 복사(이후 AI 사용 없음)
  [정상] 10:20 openai.com 뉴스 페이지 방문 (회사 홈페이지 → '사용'으로 보면 안 됨)
  [경미] 11:00 Claude 짧은 사용 (다른 행위와 연결 없음)
  [사고] 13:40 고객DB 압축 → 13:52 재무제표 열람 → 14:01 엑셀에서 복사 → ChatGPT 전환
         14:04 파일 선택창 → 압축파일 업로드 → 14:09 AI 생성 스크립트 다운로드 → 14:12 실행
         14:48~14:50 스크립트·압축파일 삭제
  [정책] 16:20 Ollama 실행, 16:30 LM Studio 모델(.gguf) 저장, 16:45 스크립트의 OpenAI API 호출
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
UTC = timezone.utc
DAY = datetime(2026, 11, 10, tzinfo=KST)
HOST = "FIN-PC-07"
USER = "kim.analyst"
U = rf"C:\Users\{USER}"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EXCEL = r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"
WORD = r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"


def t(hms: str) -> datetime:
    h, m, *s = hms.split(":")
    sec = float(s[0]) if s else 0.0
    return (DAY + timedelta(hours=int(h), minutes=int(m), seconds=sec)).astimezone(UTC)


def ez(dt: datetime) -> str:
    """EZ Tools 형식: 'YYYY-MM-DD HH:MM:SS.fffffff' (UTC)."""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f") + "0"


def webkit(dt: datetime) -> int:
    return int((dt - datetime(1601, 1, 1, tzinfo=UTC)).total_seconds() * 1_000_000)


# ------------------------------------------------------------------ files
FILES = {
    "minutes": (rf"{U}\Documents\회의록_1110.docx", 48_211),
    "fin": (rf"{U}\Documents\재무팀\2026_Q3_재무제표.xlsx", 1_204_551),
    "zip": (rf"{U}\Documents\영업자료_고객DB.zip", 8_811_002),
    "script": (rf"{U}\Downloads\report_automation.py", 6_204),
    "gguf": (rf"{U}\.lmstudio\models\lmstudio-community\Qwen2.5-7B-Instruct-GGUF\Qwen2.5-7B-Instruct-Q4_K_M.gguf",
             4_683_073_536),
    "budget": (rf"{U}\Documents\2025_예산안_old.xlsx", 98_112),
}


def write_mft(out: Path) -> None:
    hdr = ["EntryNumber", "SequenceNumber", "InUse", "ParentEntryNumber", "ParentSequenceNumber", "ParentPath",
           "FileName", "Extension", "FileSize", "ReferenceCount", "ReparseTarget", "IsDirectory", "HasAds", "IsAds",
           "SI<FN", "uSecZeros", "Copied", "SiFlags", "NameType", "Created0x10", "Created0x30", "LastModified0x10",
           "LastModified0x30", "LastRecordChange0x10", "LastRecordChange0x30", "LastAccess0x10", "LastAccess0x30",
           "UpdateSequenceNumber", "LogfileSequenceNumber", "SecurityId", "ObjectIdFileDroid", "LoggedUtilStream",
           "ZoneIdContents", "SourceFile"]
    rows = []

    def add(entry, key, created, modified, in_use=True, zone="", copied=False):
        path, size = FILES[key]
        parent, name = path.rsplit("\\", 1)
        rows.append({
            "EntryNumber": entry, "SequenceNumber": 3, "InUse": str(in_use), "ParentEntryNumber": entry - 7,
            "ParentSequenceNumber": 1, "ParentPath": "." + parent[2:], "FileName": name,
            "Extension": "." + name.rsplit(".", 1)[-1], "FileSize": size, "ReferenceCount": 1, "ReparseTarget": "",
            "IsDirectory": "False", "HasAds": str(bool(zone)), "IsAds": "False", "SI<FN": "False",
            "uSecZeros": "False", "Copied": str(copied), "SiFlags": "Archive", "NameType": "DosWindows",
            "Created0x10": ez(created), "Created0x30": ez(created), "LastModified0x10": ez(modified),
            "LastModified0x30": ez(created), "LastRecordChange0x10": ez(modified), "LastRecordChange0x30": ez(created),
            "LastAccess0x10": ez(modified), "LastAccess0x30": ez(created), "UpdateSequenceNumber": 0,
            "LogfileSequenceNumber": 0, "SecurityId": 1832, "ObjectIdFileDroid": "", "LoggedUtilStream": "",
            "ZoneIdContents": zone, "SourceFile": r"E:\KAPE\C\$MFT",
        })

    add(104221, "minutes", t("08:55"), t("08:58"))
    add(104377, "budget", t("08:20"), t("08:21"))
    add(98812, "fin", datetime(2026, 10, 30, 2, 11, tzinfo=UTC), datetime(2026, 11, 7, 8, 40, tzinfo=UTC))
    add(118004, "zip", t("13:40:12"), t("13:40:31"), in_use=False)
    zone = ("[ZoneTransfer]\\r\\nZoneId=3\\r\\nReferrerUrl=https://chatgpt.com/\\r\\n"
            "HostUrl=https://files.oaiusercontent.com/file-7Hq2aXbP9kE?se=2026-11-10T05%3A14%3A40Z\\r\\n")
    add(118090, "script", t("14:09:38"), t("14:09:40"), in_use=False, zone=zone)
    add(120551, "gguf", t("16:30:02"), t("16:41:55"))
    with open(out / "mft.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, hdr)
        w.writeheader()
        w.writerows(rows)


def write_usn(out: Path) -> None:
    hdr = ["Name", "Extension", "EntryNumber", "SequenceNumber", "ParentEntryNumber", "ParentSequenceNumber",
           "ParentPath", "UpdateSequenceNumber", "UpdateTimestamp", "UpdateReasons", "FileAttributes",
           "OffsetToData", "SourceFile"]
    usn = [8_102_334_000]
    rows = []

    def rec(path, ts, reasons, entry):
        parent, name = path.rsplit("\\", 1)
        usn[0] += 96
        rows.append({"Name": name, "Extension": "." + name.rsplit(".", 1)[-1], "EntryNumber": entry,
                     "SequenceNumber": 3, "ParentEntryNumber": entry - 7, "ParentSequenceNumber": 1,
                     "ParentPath": "." + parent[2:], "UpdateSequenceNumber": usn[0], "UpdateTimestamp": ez(ts),
                     "UpdateReasons": reasons, "FileAttributes": "Archive", "OffsetToData": usn[0],
                     "SourceFile": r"E:\KAPE\C\$Extend\$J"})

    z, s, g = FILES["zip"][0], FILES["script"][0], FILES["gguf"][0]
    rec(z, t("13:40:12"), "FileCreate", 118004)
    rec(z, t("13:40:12.2"), "DataExtend|FileCreate", 118004)
    rec(z, t("13:40:31"), "DataExtend|FileCreate|Close", 118004)
    cr = s.replace(".py", ".py.crdownload").replace("report_automation", "Unconfirmed 381022")
    rec(cr, t("14:09:38"), "FileCreate", 118090)
    rec(cr, t("14:09:39"), "DataExtend|FileCreate|Close", 118090)
    rec(cr, t("14:09:40"), "RenameOldName", 118090)
    rec(s, t("14:09:40.1"), "RenameNewName", 118090)
    rec(s + ":Zone.Identifier", t("14:09:40.2"), "NamedDataExtend|StreamChange", 118090)
    rec(s, t("14:09:40.3"), "FileCreate|Close", 118090)    # 이름 변경 후 확정 기록 (분석 편의용 단순화)
    rec(FILES["minutes"][0], t("09:12:44"), "DataOverwrite|DataExtend|Close", 104221)
    rec(s, t("14:48:03"), "FileDelete|Close", 118090)
    rec(z, t("14:50:17"), "FileDelete|Close", 118004)
    rec(g, t("16:30:02"), "FileCreate", 120551)
    rec(g, t("16:41:55"), "DataExtend|Close", 120551)
    rows.sort(key=lambda r: r["UpdateTimestamp"])
    with open(out / "usn.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, hdr)
        w.writeheader()
        w.writerows(rows)


def write_lnk(out: Path) -> None:
    hdr = ["SourceFile", "SourceCreated", "SourceModified", "SourceAccessed", "TargetCreated", "TargetModified",
           "TargetAccessed", "FileSize", "RelativePath", "WorkingDirectory", "FileAttributes", "HeaderFlags",
           "DriveType", "VolumeSerialNumber", "VolumeLabel", "LocalPath", "NetworkPath", "CommonPath", "Arguments",
           "TargetIDAbsolutePath", "TargetMFTEntryNumber", "TargetMFTSequenceNumber", "MachineID",
           "MachineMACAddress", "MACVendor", "TrackerCreatedOn", "ExtraBlocksPresent"]
    recent = rf"{U}\AppData\Roaming\Microsoft\Windows\Recent"
    rows = []

    def add(key, created, modified):
        path, size = FILES[key]
        name = path.rsplit("\\", 1)[1]
        rows.append({"SourceFile": rf"{recent}\{name}.lnk", "SourceCreated": ez(created),
                     "SourceModified": ez(modified), "SourceAccessed": ez(modified), "TargetCreated": ez(created),
                     "TargetModified": ez(modified), "TargetAccessed": ez(modified), "FileSize": size,
                     "RelativePath": "", "WorkingDirectory": path.rsplit("\\", 1)[0], "FileAttributes": "Archive",
                     "HeaderFlags": "HasTargetIdList, HasLinkInfo, IsUnicode", "DriveType": "Fixed storage media (Hard drive)",
                     "VolumeSerialNumber": "A41C-77E0", "VolumeLabel": "", "LocalPath": path, "NetworkPath": "",
                     "CommonPath": "", "Arguments": "", "TargetIDAbsolutePath": path, "TargetMFTEntryNumber": "",
                     "TargetMFTSequenceNumber": "", "MachineID": HOST.lower(), "MachineMACAddress": "00:15:5d:01:02:03",
                     "MACVendor": "Microsoft", "TrackerCreatedOn": "", "ExtraBlocksPresent": "TrackerDataBaseBlock"})

    add("minutes", t("09:10:03"), t("09:10:03"))
    add("budget", datetime(2026, 10, 2, 1, 0, tzinfo=UTC), datetime(2026, 10, 2, 1, 0, tzinfo=UTC))
    add("fin", datetime(2026, 11, 3, 0, 40, tzinfo=UTC), t("13:52:41"))
    add("zip", t("14:04:25"), t("14:04:25"))          # 파일 선택창에서 선택 → 최근 문서 등록
    with open(out / "lnk.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, hdr)
        w.writeheader()
        w.writerows(rows)


def write_jumplist(out: Path) -> None:
    hdr = ["SourceFile", "SourceCreated", "SourceModified", "SourceAccessed", "AppId", "AppIdDescription",
           "DestListVersion", "LastUsedEntryNumber", "MRU", "EntryNumber", "CreationTime", "LastModified",
           "Hostname", "MacAddress", "Path", "PinStatus", "InteractionCount", "TargetCreated", "TargetModified",
           "TargetAccessed", "FileSize", "LocalPath", "TargetIDAbsolutePath"]
    ad = rf"{U}\AppData\Roaming\Microsoft\Windows\Recent\AutomaticDestinations"
    rows = [
        ("a7bd71699cd38d1c", "Word 2016 x64", "minutes", t("09:10:03")),
        ("d00655d2aa12ff6d", "Excel 2016 x64", "fin", t("13:52:41")),
        ("d00655d2aa12ff6d", "Excel 2016 x64", "budget", datetime(2026, 10, 2, 1, 0, tzinfo=UTC)),
    ]
    with open(out / "jumplist_AutomaticDestinations.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, hdr)
        w.writeheader()
        for i, (appid, desc, key, ts) in enumerate(rows):
            path, size = FILES[key]
            w.writerow({"SourceFile": rf"{ad}\{appid}.automaticDestinations-ms", "SourceCreated": ez(ts),
                        "SourceModified": ez(ts), "SourceAccessed": ez(ts), "AppId": appid, "AppIdDescription": desc,
                        "DestListVersion": 4, "LastUsedEntryNumber": i + 1, "MRU": 0, "EntryNumber": i + 1,
                        "CreationTime": ez(ts - timedelta(days=3)), "LastModified": ez(ts), "Hostname": HOST.lower(),
                        "MacAddress": "00:15:5d:01:02:03", "Path": path, "PinStatus": "Unpinned",
                        "InteractionCount": 3, "TargetCreated": "", "TargetModified": "", "TargetAccessed": "",
                        "FileSize": size, "LocalPath": path, "TargetIDAbsolutePath": path})


def write_chrome(out: Path) -> None:
    d = out / "Chrome"
    d.mkdir(exist_ok=True)
    db = d / "History"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE urls(id INTEGER PRIMARY KEY AUTOINCREMENT,url LONGVARCHAR,title LONGVARCHAR,visit_count INTEGER DEFAULT 0 NOT NULL,
      typed_count INTEGER DEFAULT 0 NOT NULL,last_visit_time INTEGER NOT NULL,hidden INTEGER DEFAULT 0 NOT NULL);
    CREATE TABLE visits(id INTEGER PRIMARY KEY AUTOINCREMENT,url INTEGER NOT NULL,visit_time INTEGER NOT NULL,from_visit INTEGER,
      transition INTEGER DEFAULT 0 NOT NULL,segment_id INTEGER,visit_duration INTEGER DEFAULT 0 NOT NULL);
    CREATE TABLE downloads(id INTEGER PRIMARY KEY,guid VARCHAR NOT NULL,current_path LONGVARCHAR NOT NULL,target_path LONGVARCHAR NOT NULL,
      start_time INTEGER NOT NULL,received_bytes INTEGER NOT NULL,total_bytes INTEGER NOT NULL,state INTEGER NOT NULL,danger_type INTEGER NOT NULL,
      interrupt_reason INTEGER NOT NULL,hash BLOB NOT NULL,end_time INTEGER NOT NULL,opened INTEGER NOT NULL,last_access_time INTEGER NOT NULL,
      transient INTEGER NOT NULL,referrer VARCHAR NOT NULL,site_url VARCHAR NOT NULL,embedder_download_data VARCHAR NOT NULL,
      tab_url VARCHAR NOT NULL,tab_referrer_url VARCHAR NOT NULL,http_method VARCHAR NOT NULL,by_ext_id VARCHAR NOT NULL,
      by_ext_name VARCHAR NOT NULL,by_web_app_id VARCHAR NOT NULL,etag VARCHAR NOT NULL,last_modified VARCHAR NOT NULL,
      mime_type VARCHAR(255) NOT NULL,original_mime_type VARCHAR(255) NOT NULL);
    CREATE TABLE downloads_url_chains(id INTEGER NOT NULL,chain_index INTEGER NOT NULL,url LONGVARCHAR NOT NULL,PRIMARY KEY(id,chain_index));
    CREATE TABLE meta(key LONGVARCHAR NOT NULL UNIQUE PRIMARY KEY, value LONGVARCHAR);
    INSERT INTO meta VALUES('version','69');
    """)
    visits = [
        ("09:05:11", "https://www.naver.com/", "NAVER", 1, 40),
        ("09:31:50", "https://mail.corp.example/owa/", "Outlook", 1, 600),
        ("10:20:03", "https://openai.com/news/", "News | OpenAI", 0, 95),
        ("11:00:12", "https://claude.ai/new", "Claude", 1, 30),
        ("11:00:58", "https://claude.ai/chat/2f1e7c9a-6b0d-4b4e-9a51-0d3e1c2b7a10", "엑셀 함수 질문 - Claude", 0, 300),
        ("14:01:19", "https://chatgpt.com/", "ChatGPT", 1, 50),
        ("14:02:10", "https://chatgpt.com/c/6731a0f2-8c44-8008-9d2e-5b1f0c7e2a11", "재무 데이터 요약 및 분석", 0, 790),
        ("15:10:40", "https://www.naver.com/", "NAVER", 0, 20),
    ]
    for i, (hms, url, title, trans, dur) in enumerate(visits, start=1):
        vt = webkit(t(hms))
        con.execute("INSERT INTO urls(id,url,title,visit_count,typed_count,last_visit_time) VALUES(?,?,?,?,?,?)",
                    (i, url, title, 1, 1 if trans == 1 else 0, vt))
        con.execute("INSERT INTO visits(url,visit_time,from_visit,transition,segment_id,visit_duration) VALUES(?,?,?,?,?,?)",
                    (i, vt, 0, 0x30000000 | trans, 0, dur * 1_000_000))
    path = FILES["script"][0]
    url = "https://files.oaiusercontent.com/file-7Hq2aXbP9kE?se=2026-11-10T05%3A14%3A40Z&sp=r&sig=REDACTED"
    tab = "https://chatgpt.com/c/6731a0f2-8c44-8008-9d2e-5b1f0c7e2a11"
    con.execute("INSERT INTO downloads VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (1, "9f0c3e2a-77b1-4b8e-8a0e-3c2d1b0a9f88", path, path, webkit(t("14:09:38")), 6204, 6204, 1, 0, 0,
                 b"", webkit(t("14:09:40")), 0, 0, 0, "https://chatgpt.com/", "https://chatgpt.com/", "", tab,
                 "", "GET", "", "", "", "", "", "text/x-python", "text/x-python"))
    con.execute("INSERT INTO downloads_url_chains VALUES(1,0,?)", (url,))
    con.commit()
    con.close()


def write_sysmon(out: Path) -> None:
    hdr = ["RecordNumber", "EventRecordId", "TimeCreated", "EventId", "Level", "Provider", "Channel", "ProcessId",
           "ThreadId", "Computer", "ChunkNumber", "UserId", "MapDescription", "UserName", "RemoteHost",
           "PayloadData1", "PayloadData2", "PayloadData3", "PayloadData4", "PayloadData5", "PayloadData6",
           "ExecutableInfo", "HiddenRecord", "SourceFile", "Keywords", "ExtraDataOffset", "Payload"]
    desc = {1: "Process creation", 3: "Network connection", 11: "FileCreate", 15: "FileCreateStreamHash",
            22: "DNSEvent (DNS query)", 24: "ClipboardChange (New content in the clipboard)",
            26: "FileDeleteDetected (File Delete logged)"}
    rows = []
    pids = {CHROME: 4120, EXCEL: 7712, WORD: 6020}

    def ev(eid, hms, image, **data):
        ts = t(hms)
        ed = {"RuleName": "-", "UtcTime": ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
              "ProcessGuid": "{6f3c1d2e-0a11-6731-0000-0010a1b2c3d4}", "ProcessId": str(data.pop("pid", pids.get(image, 9000))),
              "Image": image, **data, "User": rf"{HOST}\{USER}"}
        payload = {"EventData": {"Data": [{"@Name": k, "#text": v} for k, v in ed.items()]}}
        n = len(rows) + 1
        rows.append({"RecordNumber": n, "EventRecordId": 51000 + n, "TimeCreated": ez(ts), "EventId": eid,
                     "Level": "Info", "Provider": "Microsoft-Windows-Sysmon",
                     "Channel": "Microsoft-Windows-Sysmon/Operational", "ProcessId": 3312, "ThreadId": 4400,
                     "Computer": HOST, "ChunkNumber": 0, "UserId": "S-1-5-18", "MapDescription": desc.get(eid, ""),
                     "UserName": r"NT AUTHORITY\SYSTEM", "RemoteHost": "", "PayloadData1": "", "PayloadData2": "",
                     "PayloadData3": "", "PayloadData4": "", "PayloadData5": "", "PayloadData6": "",
                     "ExecutableInfo": image, "HiddenRecord": "False",
                     "SourceFile": r"E:\KAPE\C\Windows\System32\winevt\Logs\Microsoft-Windows-Sysmon%4Operational.evtx",
                     "Keywords": "Classic", "ExtraDataOffset": 0, "Payload": json.dumps(payload, ensure_ascii=False)})

    def dns(hms, image, q, res="::ffff:104.18.32.47;"):
        ev(22, hms, image, QueryName=q, QueryStatus="0", QueryResults=res)

    ev(1, "09:10:01", WORD, CommandLine=f'"{WORD}" /n "{FILES["minutes"][0]}"', ParentImage=r"C:\Windows\explorer.exe")
    dns("09:05:10", CHROME, "www.naver.com")
    ev(24, "09:30:02", r"C:\Windows\System32\notepad.exe", pid=8120, Session="1", ClientInfo=f"user: {USER}",
       Hashes="SHA256=1F2E...", Archived="false")
    dns("10:20:02", CHROME, "openai.com")
    dns("11:00:11", CHROME, "claude.ai", "::ffff:160.79.104.10;")
    ev(1, "13:39:58", r"C:\Program Files\7-Zip\7zFM.exe", pid=10240, CommandLine=r'"C:\Program Files\7-Zip\7zFM.exe"',
       ParentImage=r"C:\Windows\explorer.exe")
    ev(11, "13:40:12", r"C:\Program Files\7-Zip\7zFM.exe", pid=10240, TargetFilename=FILES["zip"][0],
       CreationUtcTime=t("13:40:12").strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    ev(1, "13:52:38", EXCEL, CommandLine=f'"{EXCEL}" "{FILES["fin"][0]}"', ParentImage=r"C:\Windows\explorer.exe")
    ev(24, "14:01:05", EXCEL, Session="1", ClientInfo=f"user: {USER}", Hashes="SHA256=9A41...", Archived="true")
    dns("14:01:18", CHROME, "chatgpt.com")
    ev(3, "14:01:18.5", CHROME, Protocol="tcp", DestinationIp="104.18.32.47", DestinationHostname="chatgpt.com",
       DestinationPort="443")
    dns("14:01:19", CHROME, "cdn.oaistatic.com")
    dns("14:04:27", CHROME, "files.oaiusercontent.com", "::ffff:20.60.40.4;")
    ev(3, "14:04:27.6", CHROME, Protocol="tcp", DestinationIp="20.60.40.4",
       DestinationHostname="files.oaiusercontent.com", DestinationPort="443")
    ev(15, "14:09:40.2", CHROME, TargetFilename=FILES["script"][0] + ":Zone.Identifier",
       Hash="SHA256=AA01...",
       Contents="[ZoneTransfer]  ZoneId=3  ReferrerUrl=https://chatgpt.com/  "
                "HostUrl=https://files.oaiusercontent.com/file-7Hq2aXbP9kE".replace("  ", "\\r\\n"))
    ev(1, "14:12:30", r"C:\Users\kim.analyst\AppData\Local\Programs\Python\Python312\python.exe", pid=11880,
       CommandLine=rf'python.exe "{FILES["script"][0]}" --input "{FILES["fin"][0]}"',
       ParentImage=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    ev(26, "14:48:03", r"C:\Windows\explorer.exe", pid=5200, TargetFilename=FILES["script"][0], Hashes="SHA256=CC03...")
    ev(26, "14:50:17", r"C:\Windows\explorer.exe", pid=5200, TargetFilename=FILES["zip"][0], Hashes="SHA256=DD04...")
    ev(1, "16:20:05", rf"{U}\AppData\Local\Programs\Ollama\ollama.exe", pid=13004, CommandLine="ollama run llama3.1:8b",
       ParentImage=r"C:\Windows\System32\cmd.exe")
    dns("16:20:06", rf"{U}\AppData\Local\Programs\Ollama\ollama.exe", "registry.ollama.ai", "::ffff:104.21.75.227;")
    ev(1, "16:31:10", rf"{U}\AppData\Local\Programs\LM Studio\LM Studio.exe", pid=13900,
       CommandLine=rf'"{U}\AppData\Local\Programs\LM Studio\LM Studio.exe"', ParentImage=r"C:\Windows\explorer.exe")
    py = r"C:\Users\kim.analyst\AppData\Local\Programs\Python\Python312\python.exe"
    ev(1, "16:45:00", py, pid=14100, CommandLine=r'python.exe C:\Users\kim.analyst\work\summarize.py',
       ParentImage=r"C:\Windows\System32\cmd.exe")
    dns("16:45:01", py, "api.openai.com", "::ffff:162.159.140.245;")
    ev(3, "16:45:01.4", py, pid=14100, Protocol="tcp", DestinationIp="162.159.140.245",
       DestinationHostname="api.openai.com", DestinationPort="443")
    rows.sort(key=lambda r: r["TimeCreated"])
    with open(out / "sysmon_evtxecmd.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, hdr)
        w.writeheader()
        w.writerows(rows)


def write_agent(out: Path) -> None:
    recs = []

    def focus(hms, proc, title, cls="Chrome_WidgetWin_1", pid=None):
        recs.append({"ts": t(hms).isoformat().replace("+00:00", "Z"), "type": "window_focus", "process": proc,
                     "pid": pid or {CHROME: 4120, EXCEL: 7712, WORD: 6020}.get(proc, 9000), "title": title,
                     "class": cls, "host": HOST, "user": USER})

    def clip(hms, proc, src_title, length, pid):
        recs.append({"ts": t(hms).isoformat().replace("+00:00", "Z"), "type": "clipboard_change", "process": proc,
                     "pid": pid, "formats": ["CF_UNICODETEXT", "CF_LOCALE"], "length": length,
                     "sha256": "9a41" + "0" * 60, "source_title": src_title, "host": HOST, "user": USER})

    outlook = r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"
    notepad = r"C:\Windows\System32\notepad.exe"
    focus("09:05:00", CHROME, "NAVER - Chrome")
    focus("09:10:02", WORD, "회의록_1110.docx - Word", "OpusApp")
    focus("09:29:40", notepad, "메모 - 메모장", "Notepad", 8120)
    clip("09:30:02", notepad, "메모 - 메모장", 42, 8120)
    focus("09:31:30", outlook, "받은 편지함 - Outlook", "rctrl_renwnd32", 6500)
    focus("10:20:00", CHROME, "News | OpenAI - Chrome")
    focus("10:22:00", outlook, "받은 편지함 - Outlook", "rctrl_renwnd32", 6500)
    focus("11:00:10", CHROME, "Claude - Chrome")
    focus("11:06:00", EXCEL, "통합 문서1 - Excel", "XLMAIN")
    focus("13:39:55", r"C:\Program Files\7-Zip\7zFM.exe", "C:\\Users\\kim.analyst\\Documents\\ - 7-Zip", "FM", 10240)
    focus("13:41:00", outlook, "받은 편지함 - Outlook", "rctrl_renwnd32", 6500)
    focus("13:52:40", EXCEL, "2026_Q3_재무제표.xlsx - Excel", "XLMAIN")
    clip("14:01:05", EXCEL, "2026_Q3_재무제표.xlsx - Excel", 5832, 7712)
    focus("14:01:20", CHROME, "ChatGPT - Chrome")
    focus("14:02:12", CHROME, "재무 데이터 요약 및 분석 - ChatGPT - Chrome")
    focus("14:04:00", CHROME, "열기", "#32770")
    focus("14:04:30", CHROME, "재무 데이터 요약 및 분석 - ChatGPT - Chrome")
    focus("14:12:20", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "Windows PowerShell",
          "ConsoleWindowClass", 11800)
    focus("14:15:00", outlook, "받은 편지함 - Outlook", "rctrl_renwnd32", 6500)
    focus("15:10:38", CHROME, "NAVER - Chrome")
    focus("16:31:12", rf"{U}\AppData\Local\Programs\LM Studio\LM Studio.exe", "LM Studio", "Chrome_WidgetWin_1", 13900)
    focus("16:44:50", r"C:\Windows\System32\cmd.exe", "명령 프롬프트", "ConsoleWindowClass", 14050)
    with open(out / "agent.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", type=Path, default=Path("samples/synthetic/scenario01"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for fn in (write_mft, write_usn, write_lnk, write_jumplist, write_chrome, write_sysmon, write_agent):
        fn(args.out)
    (args.out / "README.md").write_text(__doc__ or "", encoding="utf-8")
    print(f"[+] synthetic scenario written to {args.out}")


if __name__ == "__main__":
    main()
