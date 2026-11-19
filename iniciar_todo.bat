@echo off
title Lanzador General - Mi Billetera (Sin Docker)
cd /d "%~dp0"

echo ==========================================================
echo   Iniciando Mi Billetera (Modo Nativo Windows Sin Docker)
echo ==========================================================

REM 1. Verificar herramientas
if not exist "herramientas\influxdb\influxd.exe" (
    echo [INFO] Descargando InfluxDB y Grafana portables para Windows...
    powershell -ExecutionPolicy Bypass -File "%~dp0descargar_herramientas.ps1"
)

REM 2. Iniciar InfluxDB en nueva ventana
echo [1/3] Levantando InfluxDB...
start "InfluxDB (TSDB)" cmd /k "%~dp0iniciar_influxdb.bat"

REM 3. Iniciar Grafana en nueva ventana
echo [2/3] Levantando Grafana...
start "Grafana (Dashboards)" cmd /k "%~dp0iniciar_grafana.bat"

REM 4. Iniciar API FastAPI en nueva ventana
echo [3/3] Levantando API y App Web...
start "API FastAPI" cmd /k "%~dp0iniciar_api.bat"

echo.
echo ==========================================================
echo   Todos los servicios estan iniciando en ventanas separadas.
echo   Abriendo la aplicacion en el navegador...
echo ==========================================================
timeout /t 3 >nul
start http://localhost:8000
