@echo off
REM Простой batch файл для запуска PowerShell скрипта
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
