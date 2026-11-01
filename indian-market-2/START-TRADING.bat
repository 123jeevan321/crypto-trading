@echo off
title Breaking Money - AI Trading Arena
echo =======================================================
echo   BREAKING MONEY / THE AI TRADING ARENA
echo   Starting local paper trading control panel...
echo =======================================================
echo.

start "" "http://127.0.0.1:5003"
python -m arena run
pause
