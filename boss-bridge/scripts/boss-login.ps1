# Boss 登录脚本（Windows PowerShell 薄封装）
# 用法:
#   .\scripts\boss-login.ps1
#   .\scripts\boss-login.ps1 -Qr
#   .\scripts\boss-login.ps1 -C1
#   .\scripts\boss-login.ps1 -VerifyOnly

param(
    [string[]]$Browser = @('chrome', 'edge', 'brave'),
    [switch]$Qr,
    [switch]$LogoutFirst,
    [switch]$VerifyOnly,
    [switch]$C1
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { $Py = 'python' }

$Args = @('scripts/boss-login.py')
foreach ($b in $Browser) { $Args += @('--browser', $b) }
if ($Qr) { $Args += '--qr' }
if ($LogoutFirst) { $Args += '--logout-first' }
if ($VerifyOnly) { $Args += '--verify-only' }
if ($C1) { $Args += '--c1' }

Push-Location $Root
try {
    & $Py @Args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
