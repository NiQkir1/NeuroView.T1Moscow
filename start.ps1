# Скрипт для запуска NeuroView платформы
# Запускает Backend (FastAPI) и Frontend (Next.js) одновременно

Write-Host "🚀 Запуск NeuroView платформы..." -ForegroundColor Cyan
Write-Host ""

# Функция для поиска Node.js
function Find-NodeJS {
    $nodePaths = @(
        "C:\Program Files\nodejs\node.exe",
        "C:\Program Files (x86)\nodejs\node.exe",
        "$env:APPDATA\npm\node.exe",
        "$env:LOCALAPPDATA\Programs\nodejs\node.exe"
    )
    
    # Проверяем стандартные пути
    foreach ($path in $nodePaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    # Пробуем через where.exe
    try {
        $nodePath = (Get-Command node -ErrorAction SilentlyContinue).Source
        if ($nodePath) {
            return $nodePath
        }
    } catch {}
    
    return $null
}

# Проверка Node.js
Write-Host "📦 Проверка Node.js..." -ForegroundColor Yellow
$nodePath = Find-NodeJS

if (-not $nodePath) {
    Write-Host "❌ Node.js не найден!" -ForegroundColor Red
    Write-Host "   Пожалуйста, установите Node.js с https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "   Или добавьте Node.js в PATH" -ForegroundColor Yellow
    exit 1
}

$nodeVersion = & $nodePath --version
Write-Host "✅ Node.js найден: $nodeVersion ($nodePath)" -ForegroundColor Green

# Проверка Python
Write-Host "🐍 Проверка Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python найден: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python не найден!" -ForegroundColor Red
    Write-Host "   Установите Python 3.11+ с https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Проверка и установка зависимостей Backend
Write-Host ""
Write-Host "📦 Проверка зависимостей Backend..." -ForegroundColor Yellow
$backendVenv = "backend\venv"

if (-not (Test-Path $backendVenv)) {
    Write-Host "   Создание виртуального окружения..." -ForegroundColor Yellow
    python -m venv $backendVenv
}

Write-Host "   Активация виртуального окружения..." -ForegroundColor Yellow
& "$backendVenv\Scripts\Activate.ps1"

Write-Host "   Проверка зависимостей..." -ForegroundColor Yellow
$pipList = & "$backendVenv\Scripts\pip.exe" list
if ($pipList -notmatch "fastapi") {
    Write-Host "   Установка зависимостей Backend..." -ForegroundColor Yellow
    & "$backendVenv\Scripts\pip.exe" install -r backend\requirements.txt --quiet
} else {
    Write-Host "✅ Зависимости Backend установлены" -ForegroundColor Green
}

# Проверка и установка зависимостей Frontend
Write-Host ""
Write-Host "📦 Проверка зависимостей Frontend..." -ForegroundColor Yellow
$frontendNodeModules = "frontend\node_modules"

if (-not (Test-Path $frontendNodeModules)) {
    Write-Host "   Установка зависимостей Frontend..." -ForegroundColor Yellow
    Set-Location frontend
    & $nodePath npm install
    Set-Location ..
    Write-Host "✅ Зависимости Frontend установлены" -ForegroundColor Green
} else {
    Write-Host "✅ Зависимости Frontend установлены" -ForegroundColor Green
}

# Запуск сервисов
Write-Host ""
Write-Host "🚀 Запуск сервисов..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Backend будет доступен на: http://localhost:8000" -ForegroundColor Green
Write-Host "📍 Frontend будет доступен на: http://localhost:3000" -ForegroundColor Green
Write-Host "📍 API документация: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Сервисы будут запущены в отдельных окнах PowerShell" -ForegroundColor Yellow
Write-Host ""


# Запуск Backend в отдельном окне
Write-Host "🔧 Запуск Backend (порт 8000)..." -ForegroundColor Yellow
$backendCommand = "cd `"$PWD`"; `"$backendVenv\Scripts\python.exe`" `"$PWD\backend\run.py`""
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand -WindowStyle Normal

Start-Sleep -Seconds 3

# Запуск Frontend в отдельном окне
Write-Host "🎨 Запуск Frontend (порт 3000)..." -ForegroundColor Yellow
$frontendCommand = "cd `"$PWD\frontend`"; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand -WindowStyle Normal

# Ожидание запуска
Write-Host ""
Write-Host "⏳ Ожидание запуска сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Проверка статуса
try {
    $backendHealth = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "✅ Backend запущен успешно!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend запускается... (может потребоваться еще несколько секунд)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✨ Платформа запущена!" -ForegroundColor Green
Write-Host ""
Write-Host "Откройте в браузере: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Для остановки закройте окна PowerShell с Backend и Frontend" -ForegroundColor Yellow
Write-Host ""
Write-Host "Нажмите любую клавишу для выхода (сервисы продолжат работать)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

