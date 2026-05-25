#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $script:LogFile -Value $line
}

function Read-EnvMap {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    foreach ($line in Get-Content -Path $Path) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#") -or -not $line.Contains("=")) { continue }
        $parts = $line.Split("=", 2)
        $map[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $map
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$logDir = Join-Path $HOME "Scripts/logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$script:LogFile = Join-Path $logDir ("organize_music_library_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

$envMap = Read-EnvMap (Join-Path $ProjectRoot ".env")
$root = if ($envMap.ContainsKey("MUSIC_LIBRARY_PATH") -and $envMap["MUSIC_LIBRARY_PATH"]) { $envMap["MUSIC_LIBRARY_PATH"] } else { Join-Path $HOME "Music/freetopify" }
$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($root) | Out-Null
$root = [System.IO.Path]::GetFullPath($root)

if (-not (Test-Path -LiteralPath $root)) {
    Write-Host "Root not found: $root"
    $create = Read-Host "Create this directory now? [Y/n]"
    if ([string]::IsNullOrWhiteSpace($create) -or $create -match '^(y|yes)$') {
        New-Item -ItemType Directory -Force -Path $root | Out-Null
        Write-Host "Created: $root"
    } else {
        $alt = Read-Host "Enter alternate root path (blank to cancel)"
        if ([string]::IsNullOrWhiteSpace($alt)) { exit 1 }
        $root = [System.IO.Path]::GetFullPath($alt)
        if (-not (Test-Path -LiteralPath $root)) {
            Write-Error "Root still not found: $root"
            exit 1
        }
    }
}

$singles = Join-Path $root "Music/Singles"
$playlists = Join-Path $root "_playlists"
New-Item -ItemType Directory -Force -Path $singles, $playlists | Out-Null

$audioExt = @(".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wav", ".wv")
$playlistExt = @(".m3u", ".m3u8", ".pls")
$moved = 0
$skipped = 0
$failed = 0

Write-Log "INFO" "Start organize root=$root"

$files = Get-ChildItem -Path $root -File -Recurse
foreach ($file in $files) {
    $rel = $file.FullName.Substring($root.Length).TrimStart('\\', '/')
    if ($rel.StartsWith("Music\") -or $rel.StartsWith("Podcasts\") -or $rel.StartsWith("Mixes\") -or $rel.StartsWith("_playlists\")) {
        $skipped++
        continue
    }

    $ext = $file.Extension.ToLowerInvariant()
    $destDir = $null
    if ($playlistExt -contains $ext) {
        $destDir = $playlists
    } elseif ($audioExt -contains $ext) {
        $destDir = $singles
    } else {
        $skipped++
        continue
    }

    $name = ($file.Name -replace '[\\/:*?"<>|]', '-')
    $target = Join-Path $destDir $name
    $i = 1
    while (Test-Path -LiteralPath $target) {
        $target = Join-Path $destDir ("{0}_{1}{2}" -f $file.BaseName, $i, $file.Extension)
        $i++
    }

    try {
        Move-Item -LiteralPath $file.FullName -Destination $target -ErrorAction Stop
        $moved++
        Write-Log "INFO" "Moved: $($file.FullName) -> $target"
    } catch {
        $failed++
        Write-Log "ERROR" "Failed: $($file.FullName)"
    }
}

Get-ChildItem -Path $root -Directory -Recurse |
Sort-Object FullName -Descending |
ForEach-Object {
    if (-not (Get-ChildItem -LiteralPath $_.FullName -Force)) {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    }
}

Write-Log "INFO" "Done moved=$moved skipped=$skipped failed=$failed"
Write-Host "Completed. Log: $script:LogFile"
