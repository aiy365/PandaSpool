$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$dashboardExecutable = Join-Path $repositoryRoot '.venv\Scripts\printpilot-material.exe'

if (-not (Test-Path -LiteralPath $dashboardExecutable -PathType Leaf)) {
    throw '尚未找到 .venv\Scripts\printpilot-material.exe，请先按照 README.md 完成安装。'
}

if (-not $env:PRINTPILOT_DATA_DIR) {
    $env:PRINTPILOT_DATA_DIR = Join-Path $env:LOCALAPPDATA 'PrintPilot\MaterialLab'
}

Set-Location -LiteralPath $repositoryRoot
Write-Host '[PrintPilot] 正在启动本地耗材看板...'
Write-Host "[PrintPilot] 数据目录：$env:PRINTPILOT_DATA_DIR"
Write-Host '[PrintPilot] 服务只监听 127.0.0.1，不依赖云数据库。'
& $dashboardExecutable dashboard
exit $LASTEXITCODE
