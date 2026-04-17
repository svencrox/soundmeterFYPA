#!/bin/bash
VENV_DIR=".venv"
REQUIREMENTS="sound_meter_FYP/requirements_pip.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "No virtual environment found. Creating one..."
    python -m venv "$VENV_DIR"
fi

# Activate — Scripts/ on Windows, bin/ on Linux/macOS
source "$VENV_DIR/Scripts/activate" 2>/dev/null || source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install -q -r "$REQUIREMENTS"

echo "Starting sound meter (Ctrl+C to stop)..."
python sound_meter_FYP/sound_meter_local.py
