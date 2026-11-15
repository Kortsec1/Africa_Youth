$ErrorActionPreference = 'Stop'
$folder = Join-Path $PSScriptRoot ('file-test-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
New-Item -ItemType Directory -Path $folder | Out-Null
$truth = Join-Path $folder 'ground-truth.jsonl'
function Record($action,$path) { @{observed_at_utc=[DateTime]::UtcNow.ToString('O');action=$action;path=$path;actor='automated_dotnet_file_api';pid=$PID} | ConvertTo-Json -Compress | Add-Content -LiteralPath $truth -Encoding utf8 }
$exe = Join-Path (Split-Path $PSScriptRoot) 'bin\Release\net8.0-windows\RealtimeCollector.exe'
$out = Join-Path $folder 'collector'
$c = Start-Process -FilePath $exe -ArgumentList "--seconds 12 --out `"$out`"" -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $folder 'stdout.txt') -RedirectStandardError (Join-Path $folder 'stderr.txt')
Start-Sleep -Seconds 2
$a = Join-Path $folder 'synthetic.txt'
$b = Join-Path $folder 'synthetic-renamed.txt'
[IO.File]::WriteAllText($a,'SYNTHETIC-FILE-TEST'); Record 'create_write' $a
$h=[IO.File]::OpenRead($a); try { $buffer = [byte[]]::new(64); $read=$h.Read($buffer,0,64); Record "open_read_bytes_$read" $a } finally { $h.Dispose() }
[IO.File]::AppendAllText($a,"`nSYNTHETIC-APPEND"); Record 'append_save' $a
[IO.File]::Move($a,$b); Record 'rename' $b
[IO.File]::Delete($b); Record 'delete_synthetic_file' $b
$c.WaitForExit(); Record "collector_exit_$($c.ExitCode)" $out
Write-Output $folder
