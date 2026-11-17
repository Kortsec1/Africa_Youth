<# Offline helper for a dedicated lab profile only; not a forensic imaging tool. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProfilePath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $ProfilePath).Path
$target = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $target) { throw 'Output must be a new directory.' }
if ($target.StartsWith($source.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Output must be outside the source profile.'
}
if (Get-Process -Name chrome,msedge -ErrorAction SilentlyContinue) {
    throw 'Close Chrome and Edge normally before offline collection. No processes are terminated.'
}
$null = New-Item -ItemType Directory -Path $target
$records = [Collections.Generic.List[object]]::new()
# Cookies, Login Data, and unrelated user files are intentionally not collected.
$selected = @('History','History-wal','History-shm','History-journal','Local Storage',
              'Session Storage','IndexedDB','Sessions','Cache','Code Cache','Service Worker')
foreach ($relative in $selected) {
    $itemPath = Join-Path $source $relative
    if (-not (Test-Path -LiteralPath $itemPath)) {
        $records.Add([pscustomobject]@{relative_path=$relative;status='missing'})
        continue
    }
    try {
        $item = Get-Item -LiteralPath $itemPath
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point refused.' }
        if ($item.PSIsContainer) {
            # Refuse links anywhere in the selected subtree before traversing files.
            $children = @(Get-ChildItem -LiteralPath $itemPath -Recurse -Force)
            if ($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
                throw 'Subtree contains a reparse point; collection refused.'
            }
            $files = @($children | Where-Object { -not $_.PSIsContainer })
        } else { $files = @($item) }
        foreach ($file in $files) {
            $rel = $file.FullName.Substring($source.TrimEnd('\').Length + 1)
            try {
                $hashBefore = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                $destination = Join-Path $target $rel
                $null = New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force
                Copy-Item -LiteralPath $file.FullName -Destination $destination
                $hashCopy = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
                $hashAfter = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                $state = if ($hashBefore -eq $hashCopy -and $hashBefore -eq $hashAfter) { 'copied' } else { 'unstable' }
                $records.Add([pscustomobject]@{relative_path=$rel;status=$state;
                    source_sha256_before=$hashBefore;source_sha256_after=$hashAfter;copy_sha256=$hashCopy;
                    source_last_write_utc=$file.LastWriteTimeUtc.ToString('o');length=$file.Length})
            } catch {
                $records.Add([pscustomobject]@{relative_path=$rel;status='error';error=$_.Exception.Message})
            }
        }
    } catch {
        $records.Add([pscustomobject]@{relative_path=$relative;status='error';error=$_.Exception.Message})
    }
}
$manifest = [ordered]@{collected_utc=[DateTime]::UtcNow.ToString('o');
    collection_method='offline selected-file copy; no atomic snapshot';
    profile_path=$source;os_version=[Environment]::OSVersion.VersionString;
    powershell_version=$PSVersionTable.PSVersion.ToString();files=@($records.ToArray())}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $target 'manifest.json') -Encoding utf8
if ($records | Where-Object { $_.status -in @('unstable','error') }) {
    throw 'Partial/unstable collection. Inspect manifest.json; do not classify missing evidence as absence.'
}
Write-Output "Collected selected artifacts. Review manifest at $target"
