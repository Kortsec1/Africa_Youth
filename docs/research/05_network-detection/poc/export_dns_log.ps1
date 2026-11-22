<#
  export_dns_log.ps1 - (선택, 관리자 권한) DNS-Client Operational 로그 내보내기

  이 로그 채널은 기본값이 꺼져 있을 수 있다. 실험 전에 관리자 PowerShell에서 활성화:
    wevtutil sl Microsoft-Windows-DNS-Client/Operational /e:true
  채널 이름과 이벤트 ID는 실제 환경에서 확인하고 results.md에 기록할 것.
  Message에는 다른 사이트 접속 기록이 섞일 수 있으니 보내기 전에 직접 훑어볼 것.
  작성 환경(Linux)에서 실행해 보지 않았다.

  사용 예:  .\export_dns_log.ps1 -Minutes 30 -OutFile .\out\dns_client_log.jsonl
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

Write-Host ("완료: {0}" -f $OutFile)
