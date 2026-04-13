#!/usr/bin/env bash
# OdinClaw Setup Script — Linux / macOS / Git Bash on Windows
# Run from the OdinClaw-main directory.

set -e

echo ""
echo "============================================================"
echo " OdinClaw Setup"
echo "============================================================"
echo ""

# Check Python 3.12+
if ! python --version 2>&1 | grep -qE "3\.(12|13|14)"; then
    echo "ERROR: Python 3.12+ required. Found: $(python --version 2>&1)"
    echo "Install Python 3.12 and try again."
    exit 1
fi

# Detect venv activation path (Windows bash vs Unix)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -d ".venv/Scripts" ]]; then
    ACTIVATE=".venv/Scripts/activate"
else
    ACTIVATE=".venv/bin/activate"
fi

# Create venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Install
# shellcheck disable=SC1090
source "$ACTIVATE"
echo "Installing OdinClaw with dev dependencies..."
pip install -e ".[dev]" --quiet

echo ""
echo "Running tests..."
pytest -q

echo ""
echo "============================================================"
echo " Setup complete!"
echo ""
echo " To activate : source $ACTIVATE"
echo " To run      : odinclaw start"
echo " To check    : odinclaw status"
echo "============================================================"
echo ""
