#!/bin/bash

# LoCopyCat Client Setup Script
# This script sets up a virtual environment and installs required dependencies

set -e  # Exit on error

VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

echo "LoCopyCat Client Setup"
echo "================================"

# Check if .venv exists
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at ./$VENV_DIR"
else
    echo "Creating virtual environment at ./$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q

# Check if requirements.txt exists
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing dependencies from $REQUIREMENTS_FILE..."
    pip install -r "$REQUIREMENTS_FILE"
    echo "Dependencies installed"
else
    echo "Warning: $REQUIREMENTS_FILE not found, skipping dependency installation"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To run the client, you can:"
echo "  1. Activate the environment: source .venv/bin/activate"
echo "  2. Run the client: python client.py"
echo ""
echo "Or use this script with --run flag:"
echo "  bash init.sh --run"
echo ""

# Check if --run flag is provided
if [ "$1" = "--run" ]; then
    echo "Starting client..."
    python client.py
fi
