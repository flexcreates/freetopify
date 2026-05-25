#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$ts] [INFO] Windows installer scaffold detected."
Write-Host "[$ts] [INFO] Full Windows dependency/bootstrap logic will be completed in Step 4."
Write-Host "[$ts] [INFO] For now, run this project install flow on Linux with: python3 freetopify.py install"
exit 1
