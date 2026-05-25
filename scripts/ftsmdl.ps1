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
$script:LogFile = Join-Path $logDir ("ftsmdl_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

$envMap = Read-EnvMap (Join-Path $ProjectRoot ".env")
$musicDir = if ($envMap.ContainsKey("MUSIC_LIBRARY_PATH") -and $envMap["MUSIC_LIBRARY_PATH"]) { $envMap["MUSIC_LIBRARY_PATH"] } else { Join-Path $HOME "Music/freetopify" }
$ytdlpPath = if ($envMap.ContainsKey("YTDLP_PATH") -and $envMap["YTDLP_PATH"]) { $envMap["YTDLP_PATH"] } else { ".\\venv\\Scripts\\yt-dlp.exe" }
$ytdlpBrowser = if ($envMap.ContainsKey("YTDLP_BROWSER")) { $envMap["YTDLP_BROWSER"] } else { "" }
$musicDir = [System.IO.Path]::GetFullPath($musicDir)
$ytdlpPath = [System.IO.Path]::GetFullPath($ytdlpPath)

if (-not (Test-Path -LiteralPath $musicDir)) {
    try {
        New-Item -ItemType Directory -Force -Path $musicDir | Out-Null
    } catch {
        Write-Error "Cannot create music directory: $musicDir"
        exit 1
    }
}

if (-not (Test-Path -LiteralPath $ytdlpPath)) {
    $cmd = Get-Command yt-dlp -ErrorAction SilentlyContinue
    if ($cmd) { $ytdlpPath = $cmd.Source }
}

if (-not (Test-Path -LiteralPath $ytdlpPath)) {
    Write-Error "yt-dlp not found. Run: python freetopify.py install"
    exit 1
}

Write-Host "ftsmdl (Windows) - Freetopify Downloader"
Write-Host "Log: $script:LogFile"
Write-Host "Music root: $musicDir"

while ($true) {
    $folder = Read-Host "Destination folder path under music root [Music/Singles]"
    if ([string]::IsNullOrWhiteSpace($folder)) { $folder = "Music/Singles" }
    $destDir = Join-Path $musicDir $folder
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    $url = Read-Host "Enter YouTube URL (or q to quit)"
    if ($url -in @("q", "quit", "exit")) { break }
    if ([string]::IsNullOrWhiteSpace($url)) {
        Write-Host "URL is required."
        continue
    }

    $formatInput = Read-Host "Choose format [1=mp3, 2=flac] (default 1)"
    $audioFormat = if ($formatInput -eq "2" -or $formatInput -eq "flac") { "flac" } else { "mp3" }

    $outTpl = Join-Path $destDir "%(title)s.%(ext)s"
    $args = @(
        "--extract-audio",
        "--audio-format", $audioFormat,
        "--embed-metadata",
        "--embed-thumbnail",
        "--newline",
        "--retries", "10",
        "--retry-sleep", "5",
        "--sleep-interval", "2",
        "--max-sleep-interval", "5",
        "-o", $outTpl,
        "--remote-components", "ejs:github"
    )

    if ($audioFormat -eq "mp3") {
        $args += @("--audio-quality", "320k")
    }
    if (-not [string]::IsNullOrWhiteSpace($ytdlpBrowser)) {
        $args += @("--cookies-from-browser", $ytdlpBrowser)
    }

    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($node) {
        $args += @("--js-runtimes", "node:$($node.Source)")
    }

    $args += $url
    Write-Log "INFO" "Starting download format=$audioFormat url=$url"
    & $ytdlpPath @args 2>&1 | Tee-Object -FilePath $script:LogFile -Append
    if ($LASTEXITCODE -eq 0) {
        Write-Log "INFO" "Download completed"
    } else {
        Write-Log "ERROR" "Download failed with exit=$LASTEXITCODE"
    }

    $again = Read-Host "Download another? [Y/n]"
    if ($again -match '^(n|no)$') { break }
}
