@echo off
title Content Scraper Installer
color 0b

echo.
echo ===================================================
echo   Telegram Content Scraper - Installation Script
echo ===================================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b
)
echo Python found.

echo.
echo [2/3] Installing/Updating dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies.
    pause
    exit /b
)

echo.
echo [3/3] Checking configuration...
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo [!] Please edit .env with your Bot Token and Admin ID.
)

if not exist keys.py (
    echo Creating keys.py from template...
    copy keys.py.example keys.py
    echo [!] Please edit keys.py with your API_ID and API_HASH.
)

echo.
echo ===================================================
echo   Installation Complete!
echo ===================================================
echo.
echo To start the bot:
echo 1. Edit .env and keys.py with your data
echo 2. Run 'python main.py'
echo.
pause
