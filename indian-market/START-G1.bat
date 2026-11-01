@echo off
title J1 Trader (G1) - Indian Stock Market Portal
echo =======================================================
echo   J1 TRADER (G1) - INDIAN STOCK MARKET PORTAL
echo   Starting server on http://127.0.0.1:5002 ...
echo =======================================================
echo.

start "" "http://127.0.0.1:5002"
python app.py
pause
