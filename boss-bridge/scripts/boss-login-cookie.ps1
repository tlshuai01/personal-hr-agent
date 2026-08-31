# 从浏览器 Cookie 登录（无二维码）
# 用法:
#   .\scripts\boss-login-cookie.ps1
#   .\scripts\boss-login-cookie.ps1 -VerifyOnly
#   .\scripts\boss-login-cookie.ps1 -Browser edge   # Edge 需管理员 PowerShell

param(
    [string[]]$Browser = @(),
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$Root = Split-Path -Parent $PSScriptRoot
$BossPy = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path $BossPy)) { $BossPy = 'python' }

$Args = @("$Root\scripts\boss-login-cookie.py")
foreach ($b in $Browser) { $Args += @('--browser', $b) }
if ($VerifyOnly) { $Args += '--verify-only' }

Write-Host "使用 Python: $BossPy" -ForegroundColor DarkGray
Write-Host "提示: 请先在 Chrome 登录 zhipin.com，然后完全退出 Chrome`n" -ForegroundColor Yellow

& $BossPy @Args
exit $LASTEXITCODE
