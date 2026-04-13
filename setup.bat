@echo off
REM OdinClaw Setup Script for Windows
REM Run from the OdinClaw-main directory.

echo.
echo ============================================================
echo  OdinClaw Setup
echo ============================================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12+ and try again.
    exit /b 1
)

REM Create venv if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate and install
echo Installing OdinClaw with dev dependencies...
call .venv\Scripts\activate.bat
pip install -e ".[dev]" --quiet
if errorlevel 1 (
    echo ERROR: Install failed.
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
echo  Setup complete!
echo.
echo  To activate:   .venv\Scripts\activate
echo  To run:        odinclaw start
echo  To check:      odinclaw status
echo ============================================================
echo.
