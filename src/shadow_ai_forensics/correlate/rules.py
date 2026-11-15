"""Shadow AI 탐지·재구성 규칙.

각 규칙은 '사실(facts)'과 '추론(inference)'을 분리해 Finding 을 만든다.
- facts       : 특정 아티팩트의 특정 행에서 그대로 확인되는 내용 (시각·출처 포함)
- inference   : 사실들의 시간적·논리적 결합으로 도출한 해석
- alternatives: 같은 사실을 설명하는 정상 행위 / 오탐 요인
- gaps        : 추론을 '확정'으로 올리려면 추가로 확보해야 할 증거

신뢰도(confidence)는 '규칙 기본값 + 독립 출처의 교차 확인 가산 - 약한 근거 감산'으로 계산하며
0.95 를 넘지 않는다. 포렌식 결론은 어디까지나 정황이므로 1.0(확정)은 부여하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from ..catalog import Catalog
from ..parsers.common import norm_path
from ..schema import Action, AISession, Event, Finding
from ..timeutil import fmt_kst

MAX_CONF = 0.95
EXEC_EXTS = {".exe", ".dll", ".ps1", ".bat", ".cmd", ".vbs", ".js", ".py", ".hta", ".msi", ".jar", ".scr"}


@dataclass
class Config:
    pre_window: timedelta = timedelta(minutes=15)      # 세션 시작 전 파일 열람을 볼 범위
    clip_to_ai: timedelta = timedelta(seconds=120)     # 복사 → AI 창 전환 허용 간격
    paste_window: timedelta = timedelta(minutes=5)     # AI 창 전환 → paste 이벤트 허용 간격
    dialog_to_file: timedelta = timedelta(seconds=60)  # 파일 대화상자 → LNK 갱신 간격
    upload_net: timedelta = timedelta(seconds=90)      # LNK 갱신 ↔ 업로드 엔드포인트 통신 간격
    download_exec: timedelta = timedelta(hours=24)     # 다운로드 → 실행 추적 범위
    archive_before: timedelta = timedelta(minutes=60)  # 압축 생성 → 세션 시작 범위
    cleanup_after: timedelta = timedelta(hours=2)      # 세션 종료 → 삭제 추적 범위


@dataclass
class Context:
    events: list[Event]
    sessions: list[AISession]
    cat: Catalog
    cfg: Config = field(default_factory=Config)
    findings: list[Finding] = field(default_factory=list)

    def between(self, start, end, *actions: Action) -> list[Event]:
        return [e for e in self.events if start <= e.ts <= end and (not actions or e.action in actions)]


def _src(e: Event) -> str:
    return f"[{e.source} {e.raw_ref}]"


def _fact(e: Event, text: str) -> str:
    return f"{fmt_kst(e.ts)} {text} {_src(e)}"


def _conf(base: float, bonus: float = 0.0) -> float:
    return round(min(MAX_CONF, max(0.05, base + bonus)), 2)


def _cluster(evs: list[Event], window: timedelta, key=lambda e: "") -> list[list[Event]]:
    """같은 행위가 여러 아티팩트에 남은 경우(예: Agent·Sysmon 클립보드, USN·Sysmon 삭제)를 하나로 묶는다.
    대표 이벤트는 각 묶음의 첫 번째(가장 이른) 이벤트."""
    groups: list[list[Event]] = []
    open_: dict[str, list[Event]] = {}
    for e in sorted(evs, key=lambda e: e.ts):
        k = key(e)
        g = open_.get(k)
        if g and e.ts - g[0].ts <= window:
            g.append(e)
        else:
            g = [e]
            open_[k] = g
            groups.append(g)
    return groups


def _independent_sources(evs: list[Event]) -> set[str]:
    """Sysmon DNS 와 DNSClient 는 같은 관찰(DNS)이므로 하나로 본다."""
    out = set()
    for e in evs:
        if e.action == Action.DNS_QUERY:
            out.add("DNS")
        else:
            out.add(e.source)
    return out


# --------------------------------------------------------------------------- SAI-001
def r001_sessions(ctx: Context) -> None:
    """AI 서비스 사용 세션 식별 (모든 상관분석의 기준점)."""
    for s in ctx.sessions:
        srcs = _independent_sources(s.events)
        by_src: dict[str, list[Event]] = {}
        for e in s.events:
            by_src.setdefault(e.source, []).append(e)
        facts = []
        for src, evs in sorted(by_src.items()):
            sample = evs[0]
            what = sample.url or sample.domain or sample.title or sample.process
            facts.append(f"{src}: {len(evs)}건 ({fmt_kst(evs[0].ts)}~{fmt_kst(evs[-1].ts)}) 예: {what} "
                         f"{_src(sample)}")
        only_dns = srcs == {"DNS"}
        base = 0.45 if only_dns else 0.55
        bonus = 0.15 * (len(srcs) - 1)
        if any(e.action == Action.WINDOW_FOCUS for e in s.events):
            bonus += 0.1      # 사용자가 실제로 화면을 보고 있었다는 직접 근거
        alternatives = {
            "browser": ["브라우저 세션 복원·탭 프리로드로 인한 자동 접속"],
            "desktop_app": ["앱의 자동 시작·백그라운드 업데이트 통신"],
            "local_llm": ["다른 프로그램이 로컬 모델 서버를 호출(개발·테스트 목적)"],
            "api": ["승인된 사내 도구·IDE 플러그인이 API 를 호출했을 가능성 (명령줄·부모 프로세스 확인)"],
        }.get(s.channel, [])[:] + ["공용 PC 또는 원격 세션에서 다른 사용자의 사용"]
        if only_dns:
            alternatives.insert(0, "DNS 프리페치/백그라운드 갱신: DNS 질의만으로는 사용자 조작을 증명할 수 없음")
        gaps = {
            "browser": ["로그인 계정(개인/회사) 식별: 브라우저 Cookies·Login Data 또는 프록시 로그"],
            "desktop_app": ["앱 데이터 폴더(%APPDATA%) 대화 캐시·로그 확인"],
            "local_llm": ["모델 목록·프롬프트 기록: 앱 데이터 폴더, 로컬 API 포트(예: 11434) 연결 기록"],
            "api": ["API 키 출처(환경변수·설정파일)와 호출 스크립트 내용 확인"],
        }.get(s.channel, [])
        ctx.findings.append(Finding(
            rule_id="SAI-001", title=f"{s.service} 사용 세션 ({s.channel})", severity="info",
            confidence=_conf(base, bonus), ts=s.start, session_id=s.id, evidence=list(s.events),
            facts=facts,
            inference=(f"{fmt_kst(s.start)}~{fmt_kst(s.end)} 사이 {s.service}를 {s.channel} 경로로 사용한 것으로 "
                       f"판단 (독립 출처 {len(srcs)}종: {', '.join(sorted(srcs))})."),
            alternatives=alternatives,
            gaps=gaps,
        ))


# --------------------------------------------------------------------------- SAI-002
def r002_file_before_ai(ctx: Context) -> None:
    """AI 사용 직전·도중 문서 열람."""
    for s in ctx.sessions:
        if s.channel == "local_llm":
            continue
        opened = [e for e in ctx.between(s.start - ctx.cfg.pre_window, s.end, Action.FILE_OPEN)
                  if "document" in e.tags or e.sensitive]
        if not opened:
            continue
        # 같은 파일은 하나로 묶되 출처는 모두 남김
        by_file: dict[str, list[Event]] = {}
        for e in opened:
            by_file.setdefault(norm_path(e.path), []).append(e)
        sensitive = any(e.sensitive for e in opened)
        facts = []
        for evs in by_file.values():
            for e in evs:
                facts.append(_fact(e, f"'{e.path}' 열람 흔적 ({e.time_meaning})"))
        facts.append(f"세션 {s.id}: {s.service} {fmt_kst(s.start)}~{fmt_kst(s.end)}")
        in_session = any(e.ts >= s.start for e in opened)
        ctx.findings.append(Finding(
            rule_id="SAI-002", title=f"{s.service} 사용 전후 문서 열람 ({len(by_file)}개)",
            severity="medium" if sensitive else "low",
            confidence=_conf(0.35, (0.15 if sensitive else 0) + (0.1 if in_session else 0)
                             + 0.05 * (len(_independent_sources(opened)) - 1)),
            ts=min(e.ts for e in opened), session_id=s.id, evidence=opened,
            facts=facts,
            inference="AI 사용 시점과 근접하여 문서를 열람함. 해당 문서 내용이 프롬프트 작성에 활용되었을 가능성이 있음.",
            alternatives=["AI 사용과 무관한 정상 업무 열람(병행 작업)", "LNK/JumpList 시각은 '열람' 시각이며 내용 전송을 의미하지 않음"],
            gaps=["클립보드 텔레메트리(SAI-003) 또는 업로드 흔적(SAI-004)과 결합되어야 유출 정황으로 상향 가능"],
        ))


# --------------------------------------------------------------------------- SAI-003
def r003_clipboard_to_ai(ctx: Context) -> None:
    """다른 앱에서 복사 → AI 창 전환 (붙여넣기 정황), Chrome paste 이벤트가 있으면 직접 근거로 상향.

    04 실측(동훈, 2026-11) 반영:
    - 복사 → ChatGPT 창 전환만으로는 붙여넣기 유무를 구분할 수 없었음 (실험 3) → 기본 신뢰도를 낮게 둠
    - 클립보드 변경 횟수 ≠ 붙여넣기 횟수 (실험 2: 복사1·붙여넣기3 → 알림1)
    - Chrome 확장 paste_event 는 붙여넣기 1건/대조 0건으로 일치 (실험 4) → 직접 근거로 가산
    """
    clips = [e for e in ctx.events if e.action == Action.CLIPBOARD_CHANGE]
    focus = sorted((e for e in ctx.events if e.action == Action.WINDOW_FOCUS), key=lambda e: e.ts)
    pastes = sorted((e for e in ctx.events if e.action == Action.WEB_PASTE and e.ai_service), key=lambda e: e.ts)
    used_paste: set[str] = set()
    pref = {"Agent": 0, "RealtimeCollector": 1}
    for group in _cluster(clips, timedelta(seconds=2)):
        # 창 제목이 있는 텔레메트리 레코드를 대표로, 나머지(Sysmon EID 24 등)는 교차 확인 증거로 사용
        c = min(group, key=lambda x: pref.get(x.source, 9))
        corroborating = [x for x in group if x is not c]
        if c.ai_service:     # AI 앱 자체에서 복사한 것은 '가져오기'가 아니라 '결과물 반출'
            continue
        if ctx.cat.is_browser(c.process) and ctx.cat.match_title(c.title, c.process_name):
            continue
        nxt = [f for f in focus if c.ts < f.ts <= c.ts + ctx.cfg.clip_to_ai and f.ai_service]
        if not nxt:
            continue
        f = nxt[0]
        # 다음 복사 전까지, AI 창 전환 후 paste_window 안의 같은 서비스 paste 이벤트
        next_clip = next((x.ts for x in clips if x.ts > c.ts + timedelta(seconds=2)), None)
        p_hi = f.ts + ctx.cfg.paste_window
        if next_clip and next_clip < p_hi:
            p_hi = next_clip
        paste = next((p for p in pastes if c.ts <= p.ts <= p_hi and p.ai_service == f.ai_service
                      and p.id not in used_paste), None)
        if paste:
            used_paste.add(paste.id)
        intervening = [x for x in focus if c.ts < x.ts < f.ts and not x.ai_service]
        session = next((s for s in ctx.sessions if s.start - ctx.cfg.clip_to_ai <= f.ts <= s.end + ctx.cfg.clip_to_ai
                        and s.service == f.ai_service), None)
        src_title = c.title or c.attrs.get("source_title", "")
        sensitive = c.sensitive or ctx.cat.is_sensitive(src_title)
        facts = [_fact(c, f"{c.process_name or '알 수 없는 프로세스'}에서 클립보드 변경"
                          + (f" (창: '{src_title}')" if src_title else "")
                          + (f", 길이 {c.attrs['length']}자" if c.attrs.get("length") else "")),
                 _fact(f, f"{int((f.ts - c.ts).total_seconds())}초 후 {f.ai_service} 창으로 포커스 전환 ('{f.title}')")]
        for x in corroborating:
            facts.insert(1, _fact(x, f"동일 시각 클립보드 변경 교차 확인 ({x.process_name or x.source})"))
        if intervening:
            facts.append(f"사이에 다른 창 전환 {len(intervening)}회")
        if paste:
            facts.append(_fact(paste, f"{paste.domain} 페이지에서 paste 이벤트 관측 "
                                      f"(trusted={paste.attrs.get('trusted')}, editable={paste.attrs.get('target_editable')})"))
        bonus = ((0.1 if not intervening else 0) + (0.1 if sensitive else 0)
                 + (0.05 if (f.ts - c.ts) <= timedelta(seconds=30) else 0) + (0.05 if corroborating else 0)
                 + (0.3 if paste else 0))
        if paste:
            inference = (f"{c.process_name or '다른 앱'}에서 복사한 직후 {f.ai_service} 페이지에서 붙여넣기 이벤트가 관측됨 → "
                         f"복사한 내용을 AI 입력창에 붙여넣은 것으로 판단 (전송 여부는 미확인)")
        else:
            inference = (f"{c.process_name or '다른 앱'}에서 복사 후 {f.ai_service}로 전환함. 붙여넣기 가능성이 있으나 "
                         "OS 텔레메트리만으로는 붙여넣기 여부를 구분할 수 없음")
        ctx.findings.append(Finding(
            rule_id="SAI-003",
            title=f"클립보드 복사 → {f.ai_service} " + ("붙여넣기 관측" if paste else "전환 (붙여넣기 미확인)"),
            severity="high" if sensitive else "medium",
            confidence=_conf(0.35, bonus),
            ts=c.ts, session_id=session.id if session else "", evidence=[c, *corroborating, f] + ([paste] if paste else []),
            facts=facts,
            inference=inference + (" (원본 창 제목상 민감 문서)." if sensitive else "."),
            alternatives=(["paste 이벤트는 삽입·전송 성공을 보장하지 않음 (페이지가 기본 동작을 취소할 수 있음)"] if paste else
                          ["복사 후 AI 창을 확인만 하고 붙여넣지 않았을 가능성 — 04 실측에서 '붙여넣기 함/안 함'이 "
                           "Windows 수집기 기록상 동일하게 나타남"]) +
                         ["복사한 내용이 문서 본문이 아닌 짧은 키워드·URL일 가능성",
                          "클립보드 변경 1회에 붙여넣기가 여러 번일 수 있음 (변경 횟수 ≠ 붙여넣기 횟수)"],
            gaps=(["전송 여부: 브라우저 네트워크 기록(HAR) 또는 서비스 대화 기록"] if paste else
                  ["붙여넣기 직접 근거: Chrome 붙여넣기 관측 확장(04) paste_event, 또는 서비스 대화 기록"]) +
                 ["복사 내용과 원본 문서의 대조: Sysmon EID 24 아카이브 해시"],
            mitre=["T1567"],
        ))
    # 클립보드 기록과 연결되지 않은 AI 페이지 붙여넣기 (출처 불명 붙여넣기)
    for p in pastes:
        if p.id in used_paste:
            continue
        session = next((s for s in ctx.sessions if s.start - timedelta(minutes=1) <= p.ts <= s.end + timedelta(minutes=1)
                        and s.service == p.ai_service), None)
        ctx.findings.append(Finding(
            rule_id="SAI-003", title=f"{p.ai_service} 입력창 붙여넣기 (복사 출처 미상)", severity="low",
            confidence=_conf(0.6, 0.05 if p.attrs.get("target_editable") else 0), ts=p.ts,
            session_id=session.id if session else "", evidence=[p],
            facts=[_fact(p, f"{p.domain} 페이지에서 paste 이벤트 관측 (trusted={p.attrs.get('trusted')}, "
                            f"editable={p.attrs.get('target_editable')})")],
            inference=f"{p.ai_service}에 무언가를 붙여넣음. 무엇을 어디서 복사했는지는 이 기록만으로 알 수 없음.",
            alternatives=["자신이 직접 작성한 짧은 문장·AI 응답 일부를 다시 붙여넣었을 가능성",
                          "paste 이벤트는 삽입·전송 성공을 보장하지 않음"],
            gaps=["같은 시간대 Windows 클립보드 텔레메트리(복사 출처) 확보"],
            mitre=["T1567"],
        ))


# --------------------------------------------------------------------------- SAI-004
def r004_upload(ctx: Context) -> None:
    """브라우저 파일 선택 대화상자 → 파일 LNK 갱신 (업로드 정황)."""
    used: set[str] = set()
    for s in ctx.sessions:
        if s.channel != "browser":
            continue
        lo, hi = s.start - timedelta(seconds=30), s.end + timedelta(seconds=30)
        dialogs = [d for d in ctx.between(lo, hi, Action.FILE_DIALOG) if ctx.cat.is_browser(d.process)]
        upload_net = [e for e in ctx.between(lo, hi + ctx.cfg.upload_net, Action.DNS_QUERY, Action.NET_CONNECT,
                                             Action.WEB_VISIT)
                      if e.ai_role == "upload"]
        opens = ctx.between(lo, hi + ctx.cfg.dialog_to_file, Action.FILE_OPEN)
        for o in opens:
            if o.id in used:
                continue
            dlg = next((d for d in dialogs if d.ts <= o.ts <= d.ts + ctx.cfg.dialog_to_file), None)
            net = next((n for n in upload_net if abs(n.ts - o.ts) <= ctx.cfg.upload_net), None)
            if not dlg and not net:
                continue
            used.add(o.id)
            evidence = [x for x in (dlg, o, net) if x]
            facts = []
            if dlg:
                facts.append(_fact(dlg, f"{dlg.process_name} 소유 파일 대화상자 포커스 ('{dlg.title}')"))
            facts.append(_fact(o, f"'{o.path}' 열람 흔적 ({o.time_meaning})"))
            if net:
                facts.append(_fact(net, f"{net.ai_service} 업로드 엔드포인트 통신 ({net.domain or net.url})"))
            base = 0.6 if dlg else 0.45
            ctx.findings.append(Finding(
                rule_id="SAI-004", title=f"{s.service}에 파일 업로드 정황: {o.file_name}",
                severity="high" if o.sensitive else "medium",
                confidence=_conf(base, (0.15 if dlg and net else 0) + (0.1 if o.sensitive else 0)),
                ts=dlg.ts if dlg else o.ts, session_id=s.id, evidence=evidence, facts=facts,
                inference=f"AI 사용 중 브라우저의 파일 선택 창에서 '{o.file_name}'을(를) 선택해 {s.service}에 첨부(업로드)한 것으로 추정.",
                alternatives=["파일 선택 후 업로드를 취소했을 가능성",
                              "같은 시각 다른 앱으로 파일을 열었을 가능성 (JumpList AppId 확인)"],
                gaps=["OpenSavePidlMRU/LastVisitedPidlMRU(NTUSER.DAT)의 chrome.exe 항목 확인",
                      "업로드 바이트 규모: SRUM 네트워크 사용량 또는 프록시 로그"],
                mitre=["T1567"],
            ))


# --------------------------------------------------------------------------- SAI-005 / 006
def _ai_downloads(ctx: Context) -> dict[str, list[Event]]:
    out: dict[str, list[Event]] = {}
    for e in ctx.events:
        is_dl = e.action == Action.DOWNLOAD and ("origin:ai" in e.tags or e.ai_role in ("upload", "chat"))
        is_motw = e.action == Action.FILE_CREATE and "origin:ai" in e.tags
        if (is_dl or is_motw) and e.path:
            out.setdefault(norm_path(e.path), []).append(e)
    # 같은 경로의 USN/Sysmon 생성 기록도 증거에 포함
    for e in ctx.events:
        if e.action == Action.FILE_CREATE and e.path and norm_path(e.path) in out and e not in out[norm_path(e.path)]:
            out[norm_path(e.path)].append(e)
    return out


def r005_006_download_exec(ctx: Context) -> None:
    """AI 도메인 출처 파일 다운로드(Zone.Identifier·downloads) 및 이후 실행 추적."""
    downloads = _ai_downloads(ctx)
    procs = [e for e in ctx.events if e.action == Action.PROCESS_START]
    for npath, evs in downloads.items():
        evs.sort(key=lambda e: e.ts)
        first = evs[0]
        svc = next((e.attrs.get("origin_ai_service") or e.ai_service for e in evs
                    if e.attrs.get("origin_ai_service") or e.ai_service), "AI")
        name = first.file_name
        ext = ctx.cat.ext(first.path)
        session = next((s for s in ctx.sessions if s.service == svc and s.start - timedelta(minutes=5)
                        <= first.ts <= s.end + timedelta(minutes=5)), None)
        facts = []
        for e in evs:
            if e.action == Action.DOWNLOAD:
                facts.append(_fact(e, f"다운로드 '{e.path}' (URL {e.url}, 탭 {e.attrs.get('tab_url') or '-'})"))
            elif e.attrs.get("host_url") or e.attrs.get("zone_referrer"):
                facts.append(_fact(e, f"Zone.Identifier HostUrl={e.attrs.get('host_url', '-')} "
                                      f"ReferrerUrl={e.attrs.get('zone_referrer', '-')}"))
            else:
                facts.append(_fact(e, f"파일 생성 '{e.path}' ({e.time_meaning})"))
        srcs = _independent_sources(evs)
        ctx.findings.append(Finding(
            rule_id="SAI-005", title=f"{svc} 생성 결과물 다운로드: {name}",
            severity="medium" if ext in EXEC_EXTS else "low",
            confidence=_conf(0.65, 0.1 * (len(srcs) - 1)), ts=first.ts,
            session_id=session.id if session else "", evidence=evs, facts=facts,
            inference=f"{svc}에서 생성·제공한 파일을 로컬에 저장함" + (" (실행 가능한 형식)" if ext in EXEC_EXTS else "") + ".",
            alternatives=["사용자가 직접 업로드했던 파일을 다시 내려받았을 가능성"],
            gaps=["파일 해시·내용 분석으로 AI 생성물 여부 확인"],
        ))
        # 실행 추적
        lname = name.lower()
        for p in procs:
            if not (first.ts <= p.ts <= first.ts + ctx.cfg.download_exec):
                continue
            exact = norm_path(p.process) == npath
            in_cmd = lname and lname in p.attrs.get("command_line", "").lower()
            if not (exact or in_cmd):
                continue
            ctx.findings.append(Finding(
                rule_id="SAI-006", title=f"AI 결과물 실행: {name}", severity="high",
                confidence=_conf(0.7, (0.15 if exact or npath in norm_path(p.attrs.get('command_line', '')) else 0.05)
                                 + 0.05 * (len(srcs) - 1)),
                ts=p.ts, session_id=session.id if session else "", evidence=evs + [p],
                facts=facts[:1] + [_fact(p, f"프로세스 실행 {p.process} (명령줄: {p.attrs.get('command_line', '')})")],
                inference=f"{svc}가 생성한 '{name}'을(를) 다운로드 {int((p.ts - first.ts).total_seconds() // 60)}분 후 실행함. "
                          "검증되지 않은 AI 생성 코드가 사내 단말에서 동작했을 수 있음.",
                alternatives=["동일 파일명의 다른 스크립트 실행 (명령줄 경로·해시 비교 필요)"],
                gaps=["실행 결과(생성 파일·네트워크 연결) 추적: Sysmon EID 3/11 의 ProcessGuid 연결"],
                mitre=["T1204.002", "T1059"],
            ))
            break


# --------------------------------------------------------------------------- SAI-007
def r007_unsanctioned_app(ctx: Context) -> None:
    """AI 데스크톱 앱·로컬 LLM 실행 및 모델 파일(.gguf 등) 생성."""
    by_svc: dict[str, list[Event]] = {}
    for e in ctx.events:
        hit = (e.action == Action.PROCESS_START and e.ai_role in ("app", "local_app")) or \
              (e.action == Action.FILE_CREATE and "local_model" in e.tags)
        if hit:
            svc = e.ai_service
            if not svc:   # 모델 파일은 저장 경로로 소속 앱 추정 (.lmstudio, .ollama 등)
                low = e.path.lower().replace(" ", "")
                svc = next((s.name for s in ctx.cat.services if s.local and s.name.lower().replace(" ", "") in low),
                           "로컬 LLM")
            by_svc.setdefault(svc, []).append(e)
    for svc, evs in by_svc.items():
        evs.sort(key=lambda e: e.ts)
        service = ctx.cat.service(svc)
        local = bool(service and service.local) or any("local_model" in e.tags for e in evs)
        facts = [_fact(e, (f"실행 {e.process}" if e.action == Action.PROCESS_START else f"모델 파일 생성 '{e.path}'"))
                 for e in evs[:6]]
        if len(evs) > 6:
            facts.append(f"외 {len(evs) - 6}건")
        ctx.findings.append(Finding(
            rule_id="SAI-007", title=f"{'로컬 LLM' if local else 'AI 데스크톱 앱'} 사용: {svc}",
            severity="medium", confidence=_conf(0.75, 0.1 if len(evs) > 1 else 0), ts=evs[0].ts,
            evidence=evs, facts=facts,
            inference=(f"승인 여부가 확인되지 않은 {svc}이(가) 단말에서 실행됨. "
                       + ("로컬 LLM 은 네트워크 탐지(프록시·DNS)를 우회하므로 엔드포인트 증거가 유일한 근거임."
                          if local else "브라우저 밖 앱 사용은 URL 필터링으로 식별되지 않음.")),
            alternatives=["IT 부서가 승인·배포한 앱일 가능성 (자산·SW 목록과 대조 필요)"],
            gaps=["설치 시점: Amcache/Uninstall 레지스트리, 앱 데이터 폴더 생성 시각($MFT $FN)"],
        ))


# --------------------------------------------------------------------------- SAI-008
def r008_archive_staging(ctx: Context) -> None:
    """AI 사용 직전 압축 파일 생성 (업로드와 연결 시 상향)."""
    for s in ctx.sessions:
        if s.channel == "local_llm":
            continue
        arcs = [e for e in ctx.between(s.start - ctx.cfg.archive_before, s.end, Action.FILE_CREATE)
                if "archive" in e.tags]
        if not arcs:
            continue
        uploaded = {norm_path(o.path) for f in ctx.findings if f.rule_id == "SAI-004" and f.session_id == s.id
                    for o in f.evidence if o.action == Action.FILE_OPEN}
        hit_upload = any(norm_path(a.path) in uploaded for a in arcs)
        seen = {norm_path(a.path) for a in arcs}
        facts = [_fact(a, f"압축 파일 생성 '{a.path}'" + (f" [{a.process_name}]" if a.process else ""))
                 for a in arcs]
        facts.append(f"세션 {s.id}: {s.service} 시작 {fmt_kst(s.start)}")
        ctx.findings.append(Finding(
            rule_id="SAI-008", title=f"{s.service} 사용 전 압축 파일 생성 ({len(seen)}개)",
            severity="high" if hit_upload else "medium",
            confidence=_conf(0.35, 0.3 if hit_upload else 0), ts=arcs[0].ts, session_id=s.id, evidence=arcs,
            facts=facts,
            inference="AI 사용 직전에 자료를 압축함" + (" — 해당 압축 파일이 업로드 정황(SAI-004)에서도 확인되어 "
                                                   "자료 수집 후 반출 흐름으로 판단." if hit_upload else
                                                   ". 업로드용 자료 준비(staging) 가능성이 있음."),
            alternatives=["정기 백업·메일 첨부 등 AI 와 무관한 압축"],
            gaps=["압축 파일 내부 목록 확인(원본 확보 시) 및 업로드 흔적과의 연결"],
            mitre=["T1560.001"],
        ))


# --------------------------------------------------------------------------- SAI-009
def r009_cleanup(ctx: Context) -> None:
    """AI 사용 후 관련 파일·브라우저 히스토리 삭제."""
    related: dict[str, tuple[str, str]] = {}   # norm_path -> (rule, session)
    for f in ctx.findings:
        if f.rule_id in ("SAI-004", "SAI-005", "SAI-008"):
            for e in f.evidence:
                if e.path:
                    related[norm_path(e.path)] = (f.rule_id, f.session_id)
    deletes = [e for e in ctx.events if e.action == Action.FILE_DELETE]
    for group in _cluster(deletes, timedelta(seconds=5), key=lambda e: norm_path(e.path)):
        d = group[0]
        np = norm_path(d.path)
        hist = np.endswith(("\\history", "\\places.sqlite"))
        rel = related.get(np)
        if not rel and not hist:
            continue
        s = next((s for s in ctx.sessions if s.end <= d.ts <= s.end + ctx.cfg.cleanup_after), None)
        if not s and not rel:
            continue
        ctx.findings.append(Finding(
            rule_id="SAI-009", title=f"AI 사용 흔적 삭제 정황: {d.file_name}", severity="medium",
            confidence=_conf(0.55, (0.15 if rel else 0) + 0.05 * (len(_independent_sources(group)) - 1)), ts=d.ts,
            session_id=(rel[1] if rel else "") or (s.id if s else ""), evidence=group,
            facts=[_fact(x, f"파일 삭제 '{x.path}'" + (f" (관련 탐지 {rel[0]})" if rel and x is d else ""))
                   for x in group],
            inference=("AI 사용과 연관된 파일을 사용 직후 삭제함." if rel else
                       "AI 사용 직후 브라우저 히스토리 DB가 삭제됨.") + " 흔적 은닉 의도 가능성.",
            alternatives=["디스크 정리·임시파일 정리 등 일상적 삭제"],
            gaps=["$Recycle.Bin 의 $I/$R 파일, VSS(볼륨 섀도 복사본)에서 원본 복구"],
            mitre=["T1070.004"],
        ))


RULES = [
    ("SAI-001", "AI 서비스 사용 세션 식별", r001_sessions),
    ("SAI-002", "AI 사용 전후 문서 열람", r002_file_before_ai),
    ("SAI-003", "클립보드 복사 → AI 창 전환", r003_clipboard_to_ai),
    ("SAI-004", "브라우저 파일 선택 → 업로드 정황", r004_upload),
    ("SAI-005/006", "AI 결과물 다운로드 및 실행", r005_006_download_exec),
    ("SAI-007", "비인가 AI 데스크톱 앱 / 로컬 LLM", r007_unsanctioned_app),
    ("SAI-008", "AI 사용 전 압축(Staging)", r008_archive_staging),
    ("SAI-009", "AI 사용 후 흔적 삭제", r009_cleanup),
]
