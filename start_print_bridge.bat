@echo off
title Hotel Mitraya - Hardware Print Bridge
color 0A
cd /d "%~dp0"
echo ==================================================================
echo   HOTEL MITRAYA - HARDWARE THERMAL PRINTER BRIDGE (HOIN HOP-H58)
echo ==================================================================
echo.
python printer_bridge.py %*
pause
