<#
.SYNOPSIS
  Shadow AI 분석용 Windows 아티팩트 수집 스크립트 (분석 엔진 입력 폴더를 만든다).

.DESCRIPTION
  1. 브라우저 히스토리 DB 복사 (Chrome / Edge / Whale / Firefox, 모든 프로필, -wal 포함)
  2. LECmd / JLECmd 로 LNK·JumpList 파싱 (EZ Tools 가 -ToolsDir 에 있을 때)
  3. KAPE 로 $MFT·$J 원시 추출 후 MFTECmd 파싱 (KAPE 가 있을 때)
  4. Sysmon / DNS-Client 이벤트 로그를 JSONL 로 내보내기 + 원본 .evtx 복사
  5. 수집 파일 SHA-256 해시 목록(manifest.csv) 작성 — 무결성 증빙

.NOTES
  - 관리자 권한 PowerShell 에서 실행. 실험용 VM 에서 먼저 검증할 것.
  - ⚠ 이 스크립트는 리눅스 환경에서 작성되어 아직 실제 Windows 에서 검증되지 않았다.
    02_windows-forensics 실험 시 동작을 확인하고 results.md 에 기록할 것.

.EXAMPLE
  .\collect_artifacts.ps1 -Out D:\case01 -User kim.analyst -ToolsDir C:\Tools\EZ -KapeDir C:\Tools\KAPE
  python -m shadow_ai_forensics analyze D:\case01 -o D:\case01_report
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Out,
    [string]$User = $env:USERNAME,
    [string]$ToolsDir = "C:\Tools\EZ",
    [string]$KapeDir = "C:\Tools\KAPE",
    [int]$Days = 14
)
$ErrorActionPreference = "Continue"
$Prof = "C:\Users\$User"
$since = (Get-Date).AddDays(-$Days)
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$log = Join-Path $Out "collect.log"
function Log($m) { $line = "$(Get-Date -Format o) $m"; Write-Host $line; Add-Content -Path $log -Value $line -Encoding UTF8 }

Log "host=$env:COMPUTERNAME user=$User since=$since"

# ---------------------------------------------------------------- 1. 브라우저
$browsers = @{
    "Chrome" = "$Prof\AppData\Local\Google\Chrome\User Data"
    "Edge"   = "$Prof\AppData\Local\Microsoft\Edge\User Data"
    "Whale"  = "$Prof\AppData\Local\Naver\Naver Whale\User Data"
}
foreach ($b in $browsers.GetEnumerator()) {
    if (-not (Test-Path $b.Value)) { continue }
    Get-ChildItem $b.Value -Directory | Where-Object { Test-Path (Join-Path $_.FullName "History") } | ForEach-Object {
        $dst = Join-Path $Out "browser\$($b.Key)\$($_.Name)"
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
        foreach ($f in "History", "History-wal", "History-journal") {
            $src = Join-Path $_.FullName $f
            if (Test-Path $src) { Copy-Item $src $dst -ErrorAction SilentlyContinue }
        }
        Log "browser $($b.Key)/$($_.Name) copied"
    }
}
$ff = "$Prof\AppData\Roaming\Mozilla\Firefox\Profiles"
if (Test-Path $ff) {
    Get-ChildItem $ff -Directory | ForEach-Object {
        $dst = Join-Path $Out "browser\Firefox\$($_.Name)"
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
        Copy-Item (Join-Path $_.FullName "places.sqlite*") $dst -ErrorAction SilentlyContinue
        Log "browser Firefox/$($_.Name) copied"
    }
}

# ---------------------------------------------------------------- 2. LNK / JumpList
$recent = "$Prof\AppData\Roaming\Microsoft\Windows\Recent"
$shellOut = Join-Path $Out "shell"
New-Item -ItemType Directory -Force -Path $shellOut | Out-Null
if (Test-Path "$ToolsDir\LECmd.exe") {
    & "$ToolsDir\LECmd.exe" -d $recent --csv $shellOut --csvf lnk.csv -q | Out-Null
    Log "LECmd done"
} else { Log "LECmd.exe not found in $ToolsDir (skip)" }
if (Test-Path "$ToolsDir\JLECmd.exe") {
    & "$ToolsDir\JLECmd.exe" -d "$recent\AutomaticDestinations" --csv $shellOut -q | Out-Null
    Log "JLECmd done"
} else { Log "JLECmd.exe not found (skip)" }

# ---------------------------------------------------------------- 3. $MFT / $J
if (Test-Path "$KapeDir\kape.exe") {
    $raw = Join-Path $Out "_raw"
    & "$KapeDir\kape.exe" --tsource C: --tdest $raw --target "`$MFT,`$J" --vss false | Out-Null
    $mft = Get-ChildItem $raw -Recurse -Filter '$MFT' | Select-Object -First 1
    $j = Get-ChildItem $raw -Recurse -Filter '$J' | Select-Object -First 1
    $fsOut = Join-Path $Out "filesystem"
    if ($mft -and (Test-Path "$ToolsDir\MFTECmd.exe")) {
        & "$ToolsDir\MFTECmd.exe" -f $mft.FullName --csv $fsOut --csvf mft.csv | Out-Null
        if ($j) { & "$ToolsDir\MFTECmd.exe" -f $j.FullName -m $mft.FullName --csv $fsOut --csvf usn.csv | Out-Null }
        Log "MFTECmd done"
    }
} else { Log "kape.exe not found — `$MFT/`$J 수집은 FTK Imager 로 수동 추출 후 MFTECmd 실행" }

# ---------------------------------------------------------------- 4. 이벤트 로그
$evOut = Join-Path $Out "eventlog"
New-Item -ItemType Directory -Force -Path $evOut | Out-Null
function Export-Jsonl([string]$logName, [string]$file) {
    try {
        $events = Get-WinEvent -FilterHashtable @{ LogName = $logName; StartTime = $since } -ErrorAction Stop
    } catch { Log "$logName : $($_.Exception.Message)"; return }
    $sw = New-Object System.IO.StreamWriter((Join-Path $evOut $file), $false, (New-Object System.Text.UTF8Encoding $false))
    foreach ($e in $events) {
        $xml = [xml]$e.ToXml()
        $data = @{}
        foreach ($d in $xml.Event.EventData.Data) { $data[$d.Name] = [string]$d.'#text' }
        $obj = [ordered]@{
            TimeCreated  = $e.TimeCreated.ToUniversalTime().ToString("o")
            Id           = $e.Id
            ProviderName = $e.ProviderName
            MachineName  = $e.MachineName
            RecordId     = $e.RecordId
            EventData    = $data
        }
        $sw.WriteLine(($obj | ConvertTo-Json -Compress -Depth 4))
    }
    $sw.Close()
    Log "$logName -> $file ($($events.Count) events)"
}
Export-Jsonl "Microsoft-Windows-Sysmon/Operational" "sysmon.jsonl"
Export-Jsonl "Microsoft-Windows-DNS-Client/Operational" "dnsclient.jsonl"
Copy-Item "C:\Windows\System32\winevt\Logs\Microsoft-Windows-Sysmon%4Operational.evtx" $evOut -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- 5. 텔레메트리 에이전트 로그
$agentLog = "$env:ProgramData\ShadowAIAgent\agent.jsonl"
if (Test-Path $agentLog) { Copy-Item $agentLog (Join-Path $Out "agent.jsonl"); Log "agent log copied" }

# ---------------------------------------------------------------- 6. 해시 목록
Get-ChildItem $Out -Recurse -File | Where-Object { $_.Name -ne "manifest.csv" } |
    Get-FileHash -Algorithm SHA256 |
    Select-Object @{n = "Path"; e = { $_.Path.Substring($Out.Length).TrimStart('\') } }, Hash |
    Export-Csv (Join-Path $Out "manifest.csv") -NoTypeInformation -Encoding UTF8
Log "manifest written. done."
