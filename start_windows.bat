@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 launch.py
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    python launch.py
  ) else (
    echo Python 3.10+ not found. Install Python from https://www.python.org/downloads/
    echo During installation, enable "Add python.exe to PATH".
  )
)
if errorlevel 1 pause
