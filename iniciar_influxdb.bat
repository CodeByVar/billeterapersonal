@echo off
title InfluxDB 2 (Series de Tiempo - Puerto 8086)
cd /d "%~dp0"
echo ===================================================
echo   Iniciando InfluxDB 2 (Puerto 8086)
echo ===================================================
if not exist "herramientas\influxdb\influxd.exe" (
    echo [INFO] Descargando InfluxDB por primera vez...
    powershell -ExecutionPolicy Bypass -File "%~dp0descargar_herramientas.ps1"
)
herramientas\influxdb\influxd.exe
pause
