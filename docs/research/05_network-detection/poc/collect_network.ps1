<#
  collect_network.ps1 - AI 서비스 접속 탐지 PoC (DNS 캐시 + TCP 연결 폴링)

  - Windows PowerShell 5.1 기준, cmdlet만 사용 (Add-Type/COM 사용 안 함)
  - 일반 권한에서 먼저 실행해 보고, 값이 비면 관리자 권한으로 실행
  - 결과: JSONL (한 줄에 이벤트 하나)
  - 관측 시각은 폴링 시각이다. 실제 DNS 질의 시각이 아니며 최대 IntervalSec 만큼 오차가 있다.
  - 로컬 IP, 사용자 이름, 장치명은 기록하지 않는다. 사설망 목적지도 제외한다.
  - 주의: 이 스크립트는 작성 환경(Linux)에서 실행해 보지 않았다. 처음에는 -DurationSec 30으로 시험할 것.

  사용 예:
    Set-ExecutionPolicy -Scope Process RemoteSigned
    .\collect_network.ps1 -Label S1_run1 -DurationSec 180
#>
param(
  [int]$DurationSec = 300,
  [int]$IntervalSec = 1,
  [string]$OutDir = ".\out",
  [string]$Label = "run"
)

$ErrorActionPreference = "Stop"

# 조사 결과에 따라 수정할 것. 실측으로 확인한 도메인만 남기는 것이 원칙이다.
$AiPatterns = @(
  "chatgpt.com", "openai.com", "oaistatic.com", "oaiusercontent.com",
  "claude.ai", "anthropic.com",
  "gemini.google.com", "bard.google.com",
  "copilot.microsoft.com", "perplexity.ai", "deepseek.com"
)

function Test-AiDomain([string]$name) {
  if ([string]::IsNullOrEmpty($name)) { return $false }
  $n = $name.ToLower().TrimEnd('.')
  foreach ($p in $AiPatterns) {
    if ($n -eq $p -or $n.EndsWith("." + $p)) { return $true }
  }
  return $false
}

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$script:OutFile = Join-Path $OutDir ("{0}_{1}.jsonl" -f $Label, (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-Ev($obj) {
  $line = $obj | ConvertTo-Json -Compress
  Add-Content -Path $script:OutFile -Value $line -Encoding UTF8
}

$privateRegex = '^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|0\.0\.0\.0|::1|::|fe80|fc|fd)'

$seenDns = @{}
$seenConn = @{}
$ipToDomain = @{}
$procCache = @{}
$cnt = @{ dns = 0; dns_ai = 0; conn = 0; conn_ai = 0; error = 0 }

Write-Ev ([ordered]@{
  schema_version = 1; source = "collector"; event = "start"
  observed_at = (Get-Date).ToString("o"); label = $Label
  interval_sec = $IntervalSec; duration_sec = $DurationSec
})

$end = (Get-Date).AddSeconds($DurationSec)
while ((Get-Date) -lt $end) {
  $now = (Get-Date).ToString("o")

  # 1) DNS 캐시 스냅샷 -> 처음 보는 항목만 기록
  try {
    $dns = Get-DnsClientCache -ErrorAction Stop
    foreach ($r in $dns) {
      # Type: 1=A, 5=CNAME, 28=AAAA
      if ($r.Data -and ($r.Type -eq 1 -or $r.Type -eq 28)) { $ipToDomain[[string]$r.Data] = [string]$r.Entry }
      $key = "{0}|{1}|{2}" -f $r.Entry, $r.Type, $r.Data
      if ($seenDns.ContainsKey($key)) { continue }
      $seenDns[$key] = $true
      $ai = (Test-AiDomain $r.Entry) -or (Test-AiDomain ([string]$r.Data))
      $cnt.dns++; if ($ai) { $cnt.dns_ai++ }
      Write-Ev ([ordered]@{
        schema_version = 1; source = "dns_cache"; observed_at = $now
        domain = [string]$r.Entry; record_type = [int]$r.Type; data = [string]$r.Data
        ttl_remaining = [int]$r.TimeToLive; matched_ai = $ai
        evidence_level = "access_trace"
      })
    }
  } catch {
    $cnt.error++
    Write-Ev ([ordered]@{ schema_version = 1; source = "dns_cache"; observed_at = $now; error = $_.Exception.Message })
  }

  # 2) TCP 연결 스냅샷 -> 처음 보는 연결만 기록
  try {
    $conns = Get-NetTCPConnection -State Established -ErrorAction Stop |
      Where-Object { $_.RemoteAddress -notmatch $privateRegex }
    foreach ($c in $conns) {
      $ck = "{0}|{1}|{2}|{3}" -f $c.OwningProcess, $c.RemoteAddress, $c.RemotePort, $c.LocalPort
      if ($seenConn.ContainsKey($ck)) { continue }
      $seenConn[$ck] = $true
      $procId = [int]$c.OwningProcess
      if (-not $procCache.ContainsKey($procId)) {
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $procCache[$procId] = if ($p) { $p.ProcessName } else { $null }
      }
      $dom = $ipToDomain[[string]$c.RemoteAddress]
      $ai = Test-AiDomain $dom
      $cnt.conn++; if ($ai) { $cnt.conn_ai++ }
      Write-Ev ([ordered]@{
        schema_version = 1; source = "tcp_conn"; observed_at = $now
        pid = $procId; process_name = $procCache[$procId]
        remote_ip = [string]$c.RemoteAddress; remote_port = [int]$c.RemotePort
        domain_from_dns_cache = $dom; matched_ai = $ai
        evidence_level = "access_trace"
      })
    }
  } catch {
    $cnt.error++
    Write-Ev ([ordered]@{ schema_version = 1; source = "tcp_conn"; observed_at = $now; error = $_.Exception.Message })
  }

  Start-Sleep -Seconds $IntervalSec
}

Write-Ev ([ordered]@{
  schema_version = 1; source = "collector"; event = "end"
  observed_at = (Get-Date).ToString("o")
  dns_new = $cnt.dns; dns_ai = $cnt.dns_ai
  conn_new = $cnt.conn; conn_ai = $cnt.conn_ai; errors = $cnt.error
})

Write-Host ("완료: {0}" -f $script:OutFile)
Write-Host ("DNS 신규 {0}건(AI {1}), 연결 신규 {2}건(AI {3}), 오류 {4}건" -f $cnt.dns, $cnt.dns_ai, $cnt.conn, $cnt.conn_ai, $cnt.error)
