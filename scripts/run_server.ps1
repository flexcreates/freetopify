#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Level,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message"
}

$runnerPath = Join-Path $ScriptDir "run_server.py"
if (-not (Test-Path -LiteralPath $runnerPath)) {
    Write-Log -Level "ERROR" -Message "Runner not found at $runnerPath"
    exit 1
}

$launchers = @(
    @{ Name = "py"; Args = @("-3", $runnerPath) + $args },
    @{ Name = "python"; Args = @($runnerPath) + $args },
    @{ Name = "python3"; Args = @($runnerPath) + $args }
)

foreach ($launcher in $launchers) {
    $cmd = Get-Command $launcher.Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Log -Level "WARN" -Message "Launcher '$($launcher.Name)' not found, trying next fallback."
        continue
    }

    Write-Log -Level "INFO" -Message "Starting server via '$($launcher.Name)'."
    & $launcher.Name @($launcher.Args)
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        exit 0
    }
    Write-Log -Level "WARN" -Message "Launcher '$($launcher.Name)' exited with code $exitCode, trying next fallback."
}

Write-Log -Level "ERROR" -Message "Could not start server. No working Python launcher was found."
exit 1
