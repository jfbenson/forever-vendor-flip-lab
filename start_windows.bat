@echo off
setlocal
cd /d "%~dp0"
echo.
echo ==================================
echo   Forever Vendor Flip Lab
echo ==================================
echo.
where py >nul 2>&1
if not errorlevel 1 (
    py -3 launch.py
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python was not found.
        echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/
        echo Then reopen this file.
        pause
        exit /b 1
    )
    python launch.py
)
if errorlevel 1 (
    echo.
    echo The app could not start. See the error above.
    pause
    exit /b 1
)
exit /b 0
