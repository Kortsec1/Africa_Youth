$ErrorActionPreference = 'Stop'
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (!([Security.Principal.WindowsPrincipal]::new($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw '관리자 PowerShell에서 실행하세요.' }
$dir = Join-Path $PSScriptRoot ('process-etw-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
New-Item -ItemType Directory -Path $dir | Out-Null
Start-Transcript -LiteralPath (Join-Path $dir 'execution.txt')
$traceName = 'Capstone-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$traceActive = $false
try {
 $etl = Join-Path $dir 'process.etl'
 & logman create trace $traceName -p Microsoft-Windows-Kernel-Process 0x10 4 -o $etl -ets
 $traceActive = $LASTEXITCODE -eq 0
 $exe = Join-Path (Split-Path $PSScriptRoot) 'bin\Release\net8.0-windows\RealtimeCollector.exe'
 $out = Join-Path $dir 'collector'
 $collector = Start-Process -FilePath $exe -ArgumentList "--seconds 15 --out `"$out`"" -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dir 'stdout.txt') -RedirectStandardError (Join-Path $dir 'stderr.txt')
 Start-Sleep -Seconds 3
 $p = Start-Process -FilePath "$env:WINDIR\System32\cmd.exe" -ArgumentList '/c ping -n 4 127.0.0.1 > nul' -WindowStyle Hidden -PassThru
 $targetPid = $p.Id
 $targetSession = $p.SessionId
 $startObserved = [DateTime]::UtcNow.ToString('O')
 $p.WaitForExit()
 @{pid=$targetPid; session_id=$targetSession; process='cmd.exe'; start_observed_utc=$startObserved; exit_observed_utc=[DateTime]::UtcNow.ToString('O'); exit_code=$p.ExitCode; actor='automated_test'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'ground-truth.json') -Encoding utf8
 $collector.WaitForExit()
 "collector_exit=$($collector.ExitCode)"
} finally {
 if ($traceActive) {
  & logman stop $traceName -ets
  & tracerpt (Join-Path $dir 'process.etl') -of XML -o (Join-Path $dir 'process.xml') -summary (Join-Path $dir 'summary.txt') -y
 }
 Stop-Transcript
}
Write-Output "완료: $dir"
