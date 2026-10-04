@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\install.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not complete. Review the message above and try again.
  pause
  exit /b 1
)
echo.
echo Installation is ready. Double-click Start-FindMyThingy.bat to launch.
pause
