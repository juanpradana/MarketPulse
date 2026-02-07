@echo off
REM Quick Start Script for MarketPulse (Windows)
REM This script helps you start the backend and frontend servers

echo ========================================
echo   MarketPulse - Quick Start
echo   Investment Intelligence Platform
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Python and Node.js detected
echo.

REM Check if backend virtual environment exists
if not exist "backend\venv\" (
    echo [SETUP] Creating Python virtual environment...
    cd backend
    python -m venv venv
    call venv\Scripts\activate
    echo [SETUP] Installing Python dependencies...
    @REM pip install --upgrade pip
    python.exe -m pip install --upgrade pip
    pip install -r requirements.txt
    echo [SETUP] Installing Playwright browsers...
    playwright install chromium
    cd ..
    echo [OK] Backend setup complete
    echo.
) else (
    echo [OK] Backend virtual environment exists
    echo.
)

REM Create data directory if not exists
if not exist "backend\data\" (
    echo [SETUP] Creating data directory...
    mkdir backend\data
    echo [OK] Data directory created
    echo.
)

REM Check if backend .env exists
if not exist "backend\.env" (
    echo [WARNING] backend\.env not found
    echo [SETUP] Copying .env.example to .env...
    copy backend\.env.example backend\.env
    echo.
    echo [ACTION REQUIRED] Please edit backend\.env with your credentials:
    echo   - NEOBDM_EMAIL
    echo   - NEOBDM_PASSWORD
    echo.
    echo Press any key to open .env file in notepad...
    pause >nul
    notepad backend\.env
    echo.
)

REM Check if frontend node_modules exists
if not exist "frontend\node_modules\" (
    echo [SETUP] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo [OK] Frontend setup complete
    echo.
) else (
    echo [OK] Frontend dependencies installed
    echo.
)

REM Check if frontend .env.local exists
if not exist "frontend\.env.local" (
    echo [SETUP] Creating frontend\.env.local...
    echo NEXT_PUBLIC_API_URL=http://localhost:8000 > frontend\.env.local
    echo [OK] Frontend environment configured
    echo.
)

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama is not running
    echo [INFO] Please start Ollama in a separate terminal:
    echo   ollama serve
    echo.
    echo Press any key to continue anyway...
    pause >nul
) else (
    echo [OK] Ollama is running
    echo.
)

echo ========================================
echo   Starting Servers
echo ========================================
echo.
echo [INFO] Backend will start on: http://localhost:8000
echo [INFO] Frontend will start on: http://localhost:3000
echo.
echo Press any key to start servers...
pause >nul

REM Start backend in new window
echo [START] Starting Backend Server...
start "MarketPulse Backend" cmd /k "cd backend && venv\Scripts\activate && python server.py"

REM Wait a bit for backend to start
timeout /t 5 /nobreak >nul

REM Start frontend in new window
echo [START] Starting Frontend Server...
start "MarketPulse Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo   Servers Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo [INFO] Two new windows have been opened
echo [INFO] Close this window or press Ctrl+C to exit
echo.
pause
