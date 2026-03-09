@echo off
title Domain IQ Server
cd /d "%~dp0"

:: 1. Cek Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python 3.11+ dari https://www.python.org/downloads/
    echo Pastikan centang "Add Python to PATH" saat install.
    pause
    exit /b 1
)

:: 2. Cek .env
if not exist ".env" (
    echo [SETUP] File .env belum ada, membuat dari template...
    copy .env.example .env >nul
    echo.
    echo ============================================================
    echo   File .env sudah dibuat dari .env.example
    echo   PENTING: Edit file .env dan isi DATABASE_URL + AUTH_PASSWORD
    echo   sebelum menjalankan server lagi.
    echo ============================================================
    echo.
    notepad .env
    pause
    exit /b 0
)

:: 3. Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt --quiet
echo.

:: 4. Start server + buka browser
echo [2/2] Starting server at http://localhost:8000 ...
echo.
start "" http://localhost:8000
python -m uvicorn app.main:app --port 8000
pause
