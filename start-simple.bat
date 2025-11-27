@echo off
chcp 65001 >nul 2>&1
echo Starting NeuroView platform...
echo.

REM Check Node.js
echo Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in PATH!
    echo    Please install Node.js from https://nodejs.org/
    echo    Or add Node.js to PATH
    pause
    exit /b 1
)
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found!
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js found: %NODE_VERSION%

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo    Install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%

REM Check Backend virtual environment
echo.
echo Checking Backend dependencies...
if not exist "backend\venv" (
    echo    Creating virtual environment...
    python -m venv backend\venv
)

REM Activate venv and install dependencies
call backend\venv\Scripts\activate.bat
pip list | findstr fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo    Installing Backend dependencies...
    pip install -r backend\requirements.txt --quiet
) else (
    echo [OK] Backend dependencies installed
)

REM Check Frontend dependencies
echo.
echo Checking Frontend dependencies...
if not exist "frontend\node_modules" (
    echo    Installing Frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies installed
)

REM Start services
echo.
echo Starting services...
echo.
echo [INFO] Backend will be available at: http://localhost:8000
echo [INFO] Frontend will be available at: http://localhost:3000
echo [INFO] API documentation: http://localhost:8000/docs
echo.
echo Press Ctrl+C in each window to stop services
echo.

REM Start Backend in new window
start "NeuroView Backend" cmd /k "cd /d %~dp0 && call backend\venv\Scripts\activate.bat && python backend\run.py"

REM Small delay before starting Frontend
timeout /t 2 /nobreak >nul

REM Start Frontend in new window
start "NeuroView Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo [OK] Services started in separate windows!
echo.
echo Open in browser: http://localhost:3000
echo.
echo To stop services, close "NeuroView Backend" and "NeuroView Frontend" windows
echo.
pause
