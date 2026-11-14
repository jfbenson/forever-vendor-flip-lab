@echo off
setlocal
cd /d "%~dp0"
echo.
echo =========================================
echo     Forever Vendor Flip Lab - Setup
echo =========================================
echo.
if not exist "launch.py" (
  echo ERROR: launch.py is missing.
  echo Download the complete repository ZIP from:
  echo https://github.com/jfbenson/forever-vendor-flip-lab
  echo Extract ALL files into a normal folder, then double-click start_windows.bat there.
  pause
  exit /b 1
)
set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
  )
)
if not defined PYTHON_CMD (
  echo [ACTION REQUIRED] Python 3.10 or newer was not found.
  echo.
  echo 1. Download Python 3.11 or 3.12 from:
  echo    https://www.python.org/downloads/
  echo 2. Run the installer. Select "Add Python to PATH" if shown.
  echo 3. Finish installation, then CLOSE this window.
  echo 4. Double-click start_windows.bat again.
  echo.
  choice /C YN /M "Open the Python download page now"
  if not errorlevel 2 start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)
echo [OK] Compatible Python found.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo [FIRST RUN] Creating the local Python environment and installing packages.
  echo This can take several minutes. Internet access is required.
  echo You do not need to install Git or run any commands.
  echo.
)
%PYTHON_CMD% launch.py
if errorlevel 1 (
  echo.
  echo [ACTION REQUIRED] Startup failed. Read the error above.
  echo If packages could not download, check your internet connection.
  echo For help, see README.md in this folder.
  pause
  exit /b 1
)
exit /b 0
