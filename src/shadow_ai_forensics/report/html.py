"""단일 파일 HTML 리포트 (외부 라이브러리·네트워크 불필요, 오프라인 분석 PC 에서 열람 가능)."""
from __future__ import annotations

import json

from ..schema import Event
from ..timeutil import fmt_kst, iso

LANES = ["Agent", "ChromeHistory", "FirefoxHistory", "ChromeDownloads", "Sysmon", "DNSClient",
         "LNK", "JumpList", "USN", "MFT"]


def _ev(e: Event) -> dict:
    return {
        "id": e.id, "t": iso(e.ts), "k": fmt_kst(e.ts), "src": e.source, "act": e.action.value,
        "svc": e.ai_service, "role": e.ai_role, "proc": e.process_name, "target": e.path or e.url or e.domain or e.title,
        "title": e.title, "meaning": e.time_meaning, "tags": e.tags, "ref": e.raw_ref, "sens": e.sensitive,
    }


def render_html(res) -> str:
    data = {
        "host": res.host,
        "events": [_ev(e) for e in res.events],
        "sessions": [s.to_dict() | {"k_start": fmt_kst(s.start), "k_end": fmt_kst(s.end)} for s in res.sessions],
        "findings": [f.to_dict() | {"k": fmt_kst(f.ts)} for f in res.findings],
        "inventory": res.inventory,
        "lanes": [l for l in LANES if any(e.source == l for e in res.events)],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("/*__DATA__*/null", payload)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shadow AI Forensics Report</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3e3e0;--accent:#2f5fd0;
--crit:#8b1a1a;--high:#c0392b;--med:#d68910;--low:#2e86c1;--info:#7f8c8d;--band:rgba(47,95,208,.10)}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d21;--ink:#ececef;--mute:#9a9aa2;--line:#303036;--band:rgba(110,150,255,.14)}}
*{box-sizing:border-box}body{margin:0;font:14px/1.55 -apple-system,"Segoe UI","Malgun Gothic",sans-serif;background:var(--bg);color:var(--ink)}
header{padding:28px 32px 12px}h1{margin:0 0 4px;font-size:22px}h2{font-size:16px;margin:28px 0 10px}
.sub{color:var(--mute)}main{padding:0 32px 48px;max-width:1400px}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;min-width:120px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--mute);font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:10px}
.sev{display:inline-block;font-size:11px;font-weight:700;color:#fff;border-radius:4px;padding:1px 7px;margin-right:6px;text-transform:uppercase}
.sev.critical{background:var(--crit)}.sev.high{background:var(--high)}.sev.medium{background:var(--med)}.sev.low{background:var(--low)}.sev.info{background:var(--info)}
.f-head{display:flex;align-items:center;gap:8px;cursor:pointer}.f-head .t{font-weight:600;flex:1}.f-head .m{color:var(--mute);font-size:12px;white-space:nowrap}
.conf{width:70px;height:6px;background:var(--line);border-radius:3px;overflow:hidden;display:inline-block;vertical-align:middle}.conf i{display:block;height:100%;background:var(--accent)}
.f-body{display:none;margin-top:10px;border-top:1px solid var(--line);padding-top:10px}.open .f-body{display:block}
.blk{margin:8px 0}.blk h4{margin:0 0 4px;font-size:12px;letter-spacing:.02em;color:var(--mute)}
.blk.fact{border-left:3px solid #27ae60;padding-left:10px}.blk.inf{border-left:3px solid var(--accent);padding-left:10px}
.blk.alt{border-left:3px solid var(--med);padding-left:10px}.blk.gap{border-left:3px solid var(--info);padding-left:10px}
.blk ul{margin:0;padding-left:18px}.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.filters input,.filters select,button{font:inherit;padding:5px 9px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
button{cursor:pointer}button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
#tl{width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px}
#tl text{fill:var(--mute);font-size:11px}.lane{stroke:var(--line)}.dot{cursor:pointer}.dot:hover{stroke:var(--ink);stroke-width:2}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-size:12.5px}th{background:var(--bg);position:sticky;top:0}
tr.hl td{background:rgba(214,137,16,.16)}tr.ai td:first-child{border-left:3px solid var(--accent)}
.tag{display:inline-block;font-size:10.5px;border:1px solid var(--line);border-radius:3px;padding:0 4px;margin:1px;color:var(--mute)}
.tag.ai{color:var(--accent);border-color:var(--accent)}.tag.sensitive{color:var(--high);border-color:var(--high)}
.legend{font-size:12px;color:var(--mute);margin:6px 0}.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px;vertical-align:-1px}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:6px 9px;border-radius:6px;font-size:12px;max-width:460px;display:none;z-index:9}
.note{font-size:12px;color:var(--mute)}
</style></head><body>
<header><h1>Shadow AI Forensics Report</h1><div class="sub" id="sub"></div><div class="kpis" id="kpis"></div></header>
<main>
<h2>탐지 결과</h2>
<div class="note">각 항목은 <b style="color:#27ae60">확인된 사실(증거)</b>과 <b style="color:var(--accent)">추론</b>을 분리해 표시합니다. 신뢰도는 정황의 강도이며 확정 판단이 아닙니다.</div>
<div class="filters" style="margin-top:10px" id="sevf"></div>
<div id="findings"></div>
<h2>타임라인</h2>
<div class="filters"><select id="range"></select><button id="reset">전체 보기</button></div>
<div class="legend" id="legend"></div>
<svg id="tl"></svg>
<h2>이벤트</h2>
<div class="filters"><input id="q" placeholder="검색 (경로, URL, 프로세스, 태그)" size="40">
<select id="srcf"><option value="">모든 출처</option></select>
<label><input type="checkbox" id="aionly"> AI/민감/세션 관련만</label><span class="note" id="cnt"></span></div>
<div style="max-height:560px;overflow:auto;border-radius:10px"><table><thead><tr><th>시각(KST)</th><th>출처</th><th>행위</th><th>대상</th><th>프로세스</th><th>태그</th><th>원본</th></tr></thead><tbody id="rows"></tbody></table></div>
<h2>입력 아티팩트</h2><div class="card mono" id="inv"></div>
</main><div id="tip"></div>
<script>
const D=/*__DATA__*/null;
const $=s=>document.querySelector(s);const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const SEV=["critical","high","medium","low","info"];const ACOL={file_open:"#16a085",file_create:"#27ae60",file_modify:"#8e44ad",file_delete:"#c0392b",file_rename:"#9b59b6",
web_visit:"#2f5fd0",download:"#e67e22",process_start:"#34495e",net_connect:"#5d6d7e",dns_query:"#85929e",clipboard_change:"#d4ac0d",window_focus:"#1abc9c",file_dialog:"#e74c3c",file_access:"#aab7b8"};
const evById=Object.fromEntries(D.events.map(e=>[e.id,e]));let hl=new Set();
const t0=D.events.length?D.events[0].k:"",t1=D.events.length?D.events[D.events.length-1].k:"";
$("#sub").textContent=`Host: ${D.host||"-"} · 분석 구간 ${t0} ~ ${t1} (KST)`;
const sc=Object.fromEntries(SEV.map(s=>[s,D.findings.filter(f=>f.severity===s).length]));
$("#kpis").innerHTML=[["이벤트",D.events.length],["AI 세션",D.sessions.length],["탐지",D.findings.length],["High+",sc.critical+sc.high],["Medium",sc.medium]]
 .map(([a,b])=>`<div class="kpi"><b>${b}</b><span>${a}</span></div>`).join("");
let sevOn=new Set(["critical","high","medium","low","info"]);
$("#sevf").innerHTML=SEV.map(s=>`<button class="on" data-s="${s}">${s} (${sc[s]})</button>`).join("");
$("#sevf").onclick=ev=>{const b=ev.target.closest("button");if(!b)return;const s=b.dataset.s;sevOn.has(s)?sevOn.delete(s):sevOn.add(s);b.classList.toggle("on");drawFindings()};
function list(a){return a&&a.length?`<ul>${a.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:"<span class=note>-</span>"}
function drawFindings(){const fs=D.findings.filter(f=>sevOn.has(f.severity)).sort((a,b)=>SEV.indexOf(a.severity)-SEV.indexOf(b.severity)||a.ts.localeCompare(b.ts));
$("#findings").innerHTML=fs.map((f,i)=>`<div class="card" data-i="${D.findings.indexOf(f)}"><div class="f-head"><span class="sev ${f.severity}">${f.severity}</span>
<span class="mono">${f.rule_id}</span><span class="t">${esc(f.title)}</span><span class="m">${f.k} · ${f.session_id||"-"} · 신뢰도 ${f.confidence.toFixed(2)} <span class="conf"><i style="width:${f.confidence*100}%"></i></span></span></div>
<div class="f-body"><div class="blk fact"><h4>확인된 사실 (아티팩트 증거)</h4>${list(f.facts)}</div><div class="blk inf"><h4>추론</h4>${esc(f.inference)}</div>
<div class="blk alt"><h4>다른 가능성 / 오탐 요인</h4>${list(f.alternatives)}</div><div class="blk gap"><h4>확정에 필요한 추가 증거</h4>${list(f.gaps)}</div>
${f.mitre.length?`<div class="note">MITRE ATT&CK: ${f.mitre.join(", ")}</div>`:""}<div class="note">증거 이벤트 ${f.evidence.length}건 — 클릭 시 타임라인/표에서 강조</div></div></div>`).join("")||"<div class=note>해당 없음</div>"}
$("#findings").onclick=ev=>{const c=ev.target.closest(".card");if(!c)return;const f=D.findings[+c.dataset.i];c.classList.toggle("open");
 hl=new Set(f.evidence);const s=D.sessions.find(s=>s.id===f.session_id);const ts=f.evidence.map(id=>evById[id]).filter(Boolean).map(e=>Date.parse(e.t));
 if(s){ts.push(Date.parse(s.start),Date.parse(s.end))}if(ts.length){const lo=Math.min(...ts),hi=Math.max(...ts),pad=Math.max(60e3,(hi-lo)*.15);view=[lo-pad,hi+pad]}drawTL();drawRows()};
// ---- timeline
const allT=D.events.map(e=>Date.parse(e.t));let full=[Math.min(...allT),Math.max(...allT)];if(full[0]===full[1])full=[full[0]-6e4,full[1]+6e4];let view=[...full];
$("#range").innerHTML=`<option value="">구간 선택…</option>`+D.sessions.map(s=>`<option value="${s.id}">${s.id} ${s.service} (${s.channel}) ${s.k_start}~${s.k_end.slice(11)}</option>`).join("");
$("#range").onchange=ev=>{const s=D.sessions.find(s=>s.id===ev.target.value);if(!s)return;const lo=Date.parse(s.start)-20*60e3,hi=Date.parse(s.end)+30*60e3;view=[lo,hi];hl=new Set();drawTL();drawRows()};
$("#reset").onclick=()=>{view=[...full];hl=new Set();$("#range").value="";drawTL();drawRows()};
$("#legend").innerHTML=Object.entries(ACOL).filter(([a])=>D.events.some(e=>e.act===a)).map(([a,c])=>`<i style="background:${c}"></i>${a}`).join("")+`<i style="background:var(--band);border-radius:2px"></i>AI 세션`;
const KST=9*3600e3;function lbl(ms){const d=new Date(ms+KST).toISOString();return (view[1]-view[0]>36*3600e3?d.slice(5,10)+" ":"")+d.slice(11,16)}
const tip=$("#tip");
function drawTL(){const svg=$("#tl"),W=svg.clientWidth||1200,L=110,R=16,lh=30,H=D.lanes.length*lh+40;svg.setAttribute("height",H);svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
 const x=t=>L+(t-view[0])/(view[1]-view[0])*(W-L-R);let h="";
 for(const s of D.sessions){const a=Math.max(L,x(Date.parse(s.start))),b=Math.min(W-R,x(Date.parse(s.end)));if(b<L||a>W-R)continue;
  h+=`<rect x="${a}" y="4" width="${Math.max(3,b-a)}" height="${H-34}" fill="var(--band)"/><text x="${a+3}" y="16">${s.id} ${esc(s.service)}</text>`}
 D.lanes.forEach((l,i)=>{const y=28+i*lh;h+=`<line class="lane" x1="${L}" x2="${W-R}" y1="${y}" y2="${y}"/><text x="8" y="${y+4}">${l}</text>`});
 for(let k=0;k<=6;k++){const t=view[0]+(view[1]-view[0])*k/6;h+=`<text x="${x(t)-14}" y="${H-8}">${lbl(t)}</text>`}
 for(const e of D.events){const t=Date.parse(e.t);if(t<view[0]||t>view[1])continue;const li=D.lanes.indexOf(e.src);if(li<0)continue;const y=28+li*lh,on=hl.has(e.id);
  h+=`<circle class="dot" data-id="${e.id}" cx="${x(t)}" cy="${y}" r="${on?7:(e.svc||e.sens?5:3.5)}" fill="${ACOL[e.act]||"#999"}" ${on?'stroke="#d68910" stroke-width="3"':""} opacity="${hl.size&&!on?.35:.9}"/>`}
 svg.innerHTML=h}
$("#tl").onmousemove=ev=>{const id=ev.target.dataset&&ev.target.dataset.id;if(!id){tip.style.display="none";return}const e=evById[id];
 tip.innerHTML=`<b>${e.k}</b> ${esc(e.src)} · ${e.act}<br>${esc(e.target)}<br><span style="opacity:.75">${esc(e.meaning)}</span>`;tip.style.display="block";tip.style.left=Math.min(ev.clientX+12,innerWidth-480)+"px";tip.style.top=ev.clientY+12+"px"};
$("#tl").onmouseleave=()=>tip.style.display="none";
$("#tl").onclick=ev=>{const id=ev.target.dataset&&ev.target.dataset.id;if(!id)return;hl=new Set([id]);drawTL();drawRows();const r=document.querySelector(`tr[data-id="${id}"]`);r&&r.scrollIntoView({block:"center"})};
// ---- table
const srcs=[...new Set(D.events.map(e=>e.src))];$("#srcf").innerHTML+=srcs.map(s=>`<option>${s}</option>`).join("");
function drawRows(){const q=$("#q").value.toLowerCase(),sf=$("#srcf").value,ao=$("#aionly").checked;
 const rows=D.events.filter(e=>{const t=Date.parse(e.t);if(t<view[0]||t>view[1])return false;if(sf&&e.src!==sf)return false;
  if(ao&&!(e.svc||e.sens||e.tags.some(t=>t.startsWith("session")||t==="origin:ai"||t==="archive"||t==="local_model")||hl.has(e.id)))return false;
  if(q&&!(e.target+" "+e.proc+" "+e.tags.join(" ")+" "+e.src+" "+e.act).toLowerCase().includes(q))return false;return true});
 $("#cnt").textContent=`${rows.length}건`;
 $("#rows").innerHTML=rows.slice(0,3000).map(e=>`<tr data-id="${e.id}" class="${hl.has(e.id)?"hl":""} ${e.svc?"ai":""}"><td class="mono">${e.k}</td><td>${e.src}</td><td>${e.act}</td>
<td class="mono" title="${esc(e.meaning)}">${esc(e.target)}</td><td>${esc(e.proc)}</td><td>${e.tags.map(t=>`<span class="tag ${t.startsWith("ai:")?"ai":t==="sensitive"?"sensitive":""}">${esc(t)}</span>`).join("")}</td><td class="mono note">${esc(e.ref)}</td></tr>`).join("")}
$("#q").oninput=drawRows;$("#srcf").onchange=drawRows;$("#aionly").onchange=drawRows;
$("#inv").innerHTML=Object.entries(D.inventory).map(([k,v])=>`${esc(k)} → ${esc(v)}`).join("<br>")||"-";
addEventListener("resize",drawTL);drawFindings();drawTL();drawRows();
</script></body></html>"""
