<#
  export_dns_log.ps1 - (optional, Administrator) export the DNS-Client Operational event log

  This log channel may be disabled by default. Enable it before the experiment
  (Administrator PowerShell):
    wevtutil sl Microsoft-Windows-DNS-Client/Operational /e:true
  Verify the channel name and event structure on the real system and record it in results.md.
  Message text may contain other sites you visited; review the file before sharing.
  This file is ASCII-only on purpose, so the file encoding does not matter.

  Example:  .\export_dns_log.ps1 -Minutes 30 -OutFile .\out\dns_client_log.jsonl
#>
param(
  [int]$Minutes = 30,
  [string]$OutFile = ".\out\dns_client_log.jsonl"
)

$start = (Get-Date).AddMinutes(-$Minutes)
$dir = Split-Path $OutFile -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

Get-WinEvent -FilterHashtable @{ LogName = 'Microsoft-Windows-DNS-Client/Operational'; StartTime = $start } -ErrorAction Stop |
  ForEach-Object {
    ([ordered]@{
      schema_version = 1; source = "dns_client_log"
      time_created = $_.TimeCreated.ToString("o")
      event_id = $_.Id
      message = ($_.Message -replace "\s+", " ")
    }) | ConvertTo-Json -Compress
  } | Set-Content -Path $OutFile -Encoding UTF8

Write-Host ("Done: {0}" -f $OutFile)
