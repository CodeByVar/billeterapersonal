@echo off
title API Mi Billetera (FastAPI)
cd /d "%~dp0"
echo ===================================================
echo   Iniciando API y Servidor Web (Puerto 8000)
echo ===================================================
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno .venv. Ejecuta: python -m venv .venv
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
pause
