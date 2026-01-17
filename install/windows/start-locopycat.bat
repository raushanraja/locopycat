@echo off
REM Locopycat Client Startup Script
REM This script starts the locopycat client

REM Change to the directory where this script is located
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Start the client
echo Starting Locopycat Client...
python client.py

REM If the client exits unexpectedly, pause so you can see any error messages
if %ERRORLEVEL% NEQ 0 (
    echo Client exited with error code %ERRORLEVEL%
    pause
)
