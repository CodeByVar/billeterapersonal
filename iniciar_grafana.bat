@echo off
title Grafana 11 (Dashboards - Puerto 3000)
cd /d "%~dp0"
echo ===================================================
echo   Iniciando Grafana 11 (Puerto 3000)
echo ===================================================
if not exist "herramientas\grafana\bin\grafana-server.exe" (
    echo [INFO] Descargando Grafana por primera vez...
    powershell -ExecutionPolicy Bypass -File "%~dp0descargar_herramientas.ps1"
)
cd herramientas\grafana
bin\grafana-server.exe --homepath . --config conf\custom.ini
pause
