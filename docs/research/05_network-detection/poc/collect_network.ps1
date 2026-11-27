<#
  collect_network.ps1 - AI service access detection PoC (DNS cache + TCP connection polling)

  - Windows PowerShell 5.1, cmdlets only (no Add-Type / COM)
  - Run as normal user first; if values are empty, run as Administrator
  - Output: JSONL (one event per line)
  - observed_at is the polling time, NOT the real DNS query time (error up to IntervalSec)
  - Local IP, user name, host name are not recorded. Private-network destinations are skipped.
  - This file is ASCII-only on purpose, so the file encoding does not matter.

  Example:
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

# Candidate AI domains. Keep only domains confirmed by experiments.
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

  # 1) DNS cache snapshot -> record only entries seen for the first time
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

  # 2) TCP connection snapshot -> record only connections seen for the first time
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

Write-Host ("Done: {0}" -f $script:OutFile)
Write-Host ("DNS new: {0} (AI: {1}), TCP new: {2} (AI: {3}), errors: {4}" -f $cnt.dns, $cnt.dns_ai, $cnt.conn, $cnt.conn_ai, $cnt.error)
