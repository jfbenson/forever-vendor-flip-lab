@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Project virtual environment not found. Setting it up...
    py -3 launch.py --setup-only
    if errorlevel 1 (
        echo Setup failed. Check the output above.
        exit /b 1
    )
)

echo Running unit tests...
".venv\Scripts\python.exe" -m unittest discover -s . -p "test_*.py" -v
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo Tests failed with exit code %RESULT%.
    exit /b %RESULT%
)
echo All tests passed.
exit /b 0
