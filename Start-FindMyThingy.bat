@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\start.ps1"
if errorlevel 1 (
  echo.
  echo Find My Thingy could not start. Review the message and logs in storage\logs.
  pause
  exit /b 1
)
