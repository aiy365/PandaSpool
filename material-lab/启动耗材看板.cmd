@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pandaspool-material.exe" (
  echo [PandaSpool] 尚未找到本地运行环境。
  echo 请先按照 README.md 的安装步骤创建 .venv 并安装项目。
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\start-dashboard.ps1"

if errorlevel 1 (
  echo.
  echo [PandaSpool] 启动失败，请检查上方错误和数据目录权限。
  pause
)
