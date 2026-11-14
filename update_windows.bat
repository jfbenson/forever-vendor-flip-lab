@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>&1
if errorlevel 1 (
    echo Git is not installed. To update, download a new ZIP from GitHub.
    pause
    exit /b 1
)
if not exist ".git" (
    echo This folder came from a ZIP, not a Git clone.
    echo Download a fresh ZIP from GitHub to update.
    pause
    exit /b 1
)
git pull --ff-only
if errorlevel 1 (
    echo Update failed. Your existing files were not intentionally changed.
    pause
    exit /b 1
)
echo Updated. Double-click start_windows.bat to launch.
pause
