@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON=%USERPROFILE%\miniconda3\envs\pmsm-ai\python.exe"
if not exist "%PYTHON%" (
    echo 未找到 pmsm-ai Python 环境。
    echo 预期路径：%PYTHON%
    pause
    exit /b 1
)

"%PYTHON%" -m pmsm_ai
if errorlevel 1 (
    echo.
    echo 图形界面启动失败，请把上面的错误信息发给 Codex。
    pause
)
