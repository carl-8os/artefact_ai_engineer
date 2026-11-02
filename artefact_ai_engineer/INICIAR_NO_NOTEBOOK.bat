@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
  if errorlevel 1 (
    echo ERROR: Install Python 3.10+ and enable Add Python to PATH.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" run.py --check-data
if errorlevel 1 (echo ERROR: CSV validation failed. Check the data folder.& pause & exit /b 1)
if "%OPENAI_API_KEY%"=="" (
  echo.
  echo Data check passed. Set OPENAI_API_KEY to chat with the agent.
  echo PowerShell: $env:OPENAI_API_KEY = "your-api-key"
  pause
  exit /b 0
)
".venv\Scripts\python.exe" run.py
pause
