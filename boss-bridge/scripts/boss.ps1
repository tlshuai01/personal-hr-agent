# 本机 boss CLI 包装（未加入 PATH 时用）
# 用法: .\scripts\boss.ps1 login --qrcode
#       .\scripts\boss.ps1 status --json

$BossExe = $env:BOSS_CLI_BIN
if (-not $BossExe) {
    $BossExe = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\Scripts\boss.exe"
}
if (-not (Test-Path $BossExe)) {
    $found = Get-Command boss -ErrorAction SilentlyContinue
    if ($found) { $BossExe = $found.Source }
    else {
        Write-Error "找不到 boss.exe。请先: pip install kabi-boss-cli"
        exit 1
    }
}
$env:PYTHONIOENCODING = 'utf-8'
& $BossExe @args
