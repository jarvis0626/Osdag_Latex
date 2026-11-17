@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" start.py --open %*
) else (
  python start.py --open %*
)
if errorlevel 1 (
  echo.
  echo Report creation failed. Read the message above for the next step.
  pause
)
