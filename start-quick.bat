@echo off
echo Starting NeuroView...
echo.

REM Start Backend
echo Starting Backend...
start "NeuroView Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate.bat && python run.py"

REM Wait a bit
timeout /t 3 /nobreak >nul

REM Start Frontend
echo Starting Frontend...
start "NeuroView Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Services started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
pause







