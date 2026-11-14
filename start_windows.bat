@echo off
setlocal
cd /d "%~dp0"

echo === Updating Forever Vendor Flip Lab ===
git pull --ff-only
if errorlevel 1 (
    echo Git update failed. App not launched.
    pause
    exit /b 1
)

echo.
echo === Running tests ===
call "%~dp0test_windows.bat"
if errorlevel 1 (
    echo Tests failed. App not launched.
    pause
    exit /b 1
)

echo.
echo === Starting app ===
where py >nul 2>&1
if not errorlevel 1 (
    py -3 launch.py
) else (
    python launch.py
)
if errorlevel 1 pause
exit /b %ERRORLEVEL%
