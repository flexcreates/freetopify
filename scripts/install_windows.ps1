#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Log "INFO" "Freetopify Windows installer starting"

$pythonCmd = $null
foreach ($candidate in @("py", "python", "python3")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        $pythonCmd = $candidate
        break
    }
}

if (-not $pythonCmd) {
    Write-Log "ERROR" "Python not found. Install Python 3.11+ and rerun."
    exit 1
}

Write-Log "INFO" "Python launcher: $pythonCmd"
Write-Log "INFO" "Dependency guidance: install FFmpeg + Node.js (Winget or manual), SQLite is bundled in Python."
Write-Host "Suggested commands:"
Write-Host "  winget install --id Gyan.FFmpeg -e"
Write-Host "  winget install --id OpenJS.NodeJS.LTS -e"

$defaultMusic = Join-Path $HOME "Music\\freetopify"
$musicInput = Read-Host "Music library path [$defaultMusic]"
$musicPath = if ([string]::IsNullOrWhiteSpace($musicInput)) { $defaultMusic } else { $musicInput }
New-Item -ItemType Directory -Force -Path $musicPath | Out-Null
$musicPath = (Resolve-Path $musicPath).Path

$adminUser = Read-Host "Admin username [admin]"
if ([string]::IsNullOrWhiteSpace($adminUser)) { $adminUser = "admin" }

$adminPass = Read-Host "Admin password [freetopify]"
if ([string]::IsNullOrWhiteSpace($adminPass)) { $adminPass = "freetopify" }

$guestPin = Read-Host "Guest PIN (blank disables guest)"
$ytBrowser = Read-Host "YouTube Cookie Browser (chrome/firefox/edge/safari, blank disables)"

$secretKey = & $pythonCmd -c "import secrets; print(secrets.token_hex(32))"
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "Failed to generate SECRET_KEY"
    exit 1
}

$ytdlpPath = ".\\venv\\Scripts\\yt-dlp.exe"

$envPath = Join-Path $ProjectRoot ".env"
if (Test-Path $envPath) {
    Write-Log "INFO" "Existing .env found; updating configurable values"
    $content = Get-Content -Raw $envPath
    $map = @{
        "MUSIC_LIBRARY_PATH" = $musicPath
        "YTDLP_PATH" = $ytdlpPath
        "YTDLP_BROWSER" = $ytBrowser
        "GUEST_PIN" = $guestPin
    }
    foreach ($key in $map.Keys) {
        $val = $map[$key]
        if ($content -match "(?m)^$key=") {
            $content = [regex]::Replace($content, "(?m)^$key=.*$", "$key=$val")
        } else {
            $content += "`r`n$key=$val"
        }
    }
    Set-Content -Encoding UTF8 $envPath $content
} else {
@"
SERVER_HOST=0.0.0.0
SERVER_PORT=7171
SECRET_KEY=$secretKey
ADMIN_USERNAME=$adminUser
ADMIN_PASSWORD=$adminPass
TOKEN_EXPIRE_HOURS=168
MUSIC_LIBRARY_PATH=$musicPath
DATABASE_PATH=./data/freetopify.db
YTDLP_PATH=$ytdlpPath
VENV_PATH=./venv
DEFAULT_DOWNLOAD_FORMAT=mp3
DEFAULT_DOWNLOAD_BITRATE=320k
YTDLP_BROWSER=$ytBrowser
LOG_LEVEL=INFO
LOG_FILE=./logs/freetopify.log
TAILSCALE_IP=
GUEST_PIN=$guestPin
GUEST_TOKEN_EXPIRE_HOURS=1
MAX_CONNECTIONS=0
"@ | Set-Content -Encoding UTF8 $envPath
}

if (-not (Test-Path "venv")) {
    Write-Log "INFO" "Creating virtual environment"
    if ($pythonCmd -eq "py") {
        & py -3 -m venv venv
    } else {
        & $pythonCmd -m venv venv
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR" "Failed to create venv"
        exit 1
    }
}

$venvPython = Join-Path $ProjectRoot "venv\\Scripts\\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Log "ERROR" "venv Python not found at $venvPython"
    exit 1
}

Write-Log "INFO" "Installing Python dependencies"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "pip upgrade failed"
    exit 1
}

& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "requirements install failed"
    exit 1
}

Write-Log "INFO" "Install complete"
Write-Host "Start server: python freetopify.py start"
