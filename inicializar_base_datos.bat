@echo off
title Inicializar Base de Datos PostgreSQL
cd /d "%~dp0"
echo ===================================================
echo   Creando Tablas y Cargando Datos en PostgreSQL
echo ===================================================
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro .venv. Creando entorno virtual...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r api\requirements.txt
)
.venv\Scripts\python.exe db\inicializar_db.py
echo.
pause
