@echo off
title Breaking Money - AI Trading Arena Setup
echo =======================================================
echo   BREAKING MONEY / THE AI TRADING ARENA
echo   Setup Installer (Windows)
echo =======================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://python.org/downloads and check 'Add python.exe to PATH'.
    pause
    exit /b 1
)

echo [1/3] Checking Python installation...
python --version

echo.
echo [2/3] Installing dependencies...
python -m pip install -r requirements.txt

echo.
echo [3/3] Creating default .env if missing...
if not exist .env (
    copy .env.example .env >nul
    echo Created local .env file.
)

echo.
echo =======================================================
echo   Setup done.
echo   You can now run START-TRADING.bat to launch the Arena!
echo =======================================================
pause
