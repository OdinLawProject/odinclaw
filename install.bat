@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  OdinClaw Installer
echo  Author: Borr / OdinLawProject
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12+ from python.org
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python version: %PYVER%

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing OdinClaw...
python -m pip install -e ".[dev]" --quiet
if errorlevel 1 (
    echo ERROR: Installation failed.
    pause
    exit /b 1
)

echo.
echo Running tests...
pytest -q
if errorlevel 1 (
    echo WARNING: Some tests failed. Check output above.
) else (
    echo All tests passed.
)

echo.
echo ============================================================
echo  OdinClaw installed successfully.
echo.
echo  To activate : .venv\Scripts\activate
echo  To run      : odinclaw start
echo  To check    : odinclaw status
echo ============================================================
echo.
pause
