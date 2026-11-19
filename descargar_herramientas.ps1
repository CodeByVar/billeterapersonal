# ==============================================================================
# Script de Descarga y Preparación de Herramientas Portables (Windows Sin Docker)
# Descarga InfluxDB 2 y Grafana 11 oficiales portables para Windows.
# ==============================================================================

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$HerramientasDir = Join-Path $Raiz "herramientas"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Preparando herramientas locales (InfluxDB + Grafana)   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $HerramientasDir)) {
    New-Item -ItemType Directory -Path $HerramientasDir | Out-Null
}

# ---------------- 1. InfluxDB 2 ----------------
$InfluxDir = Join-Path $HerramientasDir "influxdb"
$InfluxExe = Join-Path $InfluxDir "influxd.exe"

if (-not (Test-Path $InfluxExe)) {
    $InfluxZip = Join-Path $HerramientasDir "influxdb.zip"
    $InfluxUrl = "https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.11-windows.zip"
    Write-Host "`n[1/2] Descargando InfluxDB 2.7.11 portable para Windows..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $InfluxUrl -OutFile $InfluxZip -UseBasicParsing

    Write-Host "Extrayendo InfluxDB..." -ForegroundColor Yellow
    Expand-Archive -Path $InfluxZip -DestinationPath $HerramientasDir -Force
    Remove-Item -Path $InfluxZip -Force

    # Mover contenido a carpeta fija "influxdb" si vino con subcarpeta de versión
    $Extraido = Get-ChildItem -Path $HerramientasDir -Directory -Filter "*influxdb2*" | Select-Object -First 1
    if ($Extraido -and ($Extraido.FullName -ne $InfluxDir)) {
        if (Test-Path $InfluxDir) { Remove-Item -Recurse -Force $InfluxDir }
        Rename-Item -Path $Extraido.FullName -NewName "influxdb"
    }
    Write-Host "✅ InfluxDB listo en: $InfluxDir" -ForegroundColor Green
} else {
    Write-Host "`n[1/2] InfluxDB ya está descargado en: $InfluxDir" -ForegroundColor Green
}

# ---------------- 2. Grafana 11 ----------------
$GrafanaDir = Join-Path $HerramientasDir "grafana"
$GrafanaExe = Join-Path $GrafanaDir "bin\grafana-server.exe"

if (-not (Test-Path $GrafanaExe)) {
    $GrafanaZip = Join-Path $HerramientasDir "grafana.zip"
    $GrafanaUrl = "https://dl.grafana.com/oss/release/grafana-11.4.0.windows-amd64.zip"
    Write-Host "`n[2/2] Descargando Grafana 11.4.0 portable para Windows..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $GrafanaUrl -OutFile $GrafanaZip -UseBasicParsing

    Write-Host "Extrayendo Grafana..." -ForegroundColor Yellow
    Expand-Archive -Path $GrafanaZip -DestinationPath $HerramientasDir -Force
    Remove-Item -Path $GrafanaZip -Force

    $ExtraidoGraf = Get-ChildItem -Path $HerramientasDir -Directory -Filter "*grafana-v11*" | Select-Object -First 1
    if (-not $ExtraidoGraf) {
        $ExtraidoGraf = Get-ChildItem -Path $HerramientasDir -Directory -Filter "*grafana-11*" | Select-Object -First 1
    }
    if ($ExtraidoGraf -and ($ExtraidoGraf.FullName -ne $GrafanaDir)) {
        if (Test-Path $GrafanaDir) { Remove-Item -Recurse -Force $GrafanaDir }
        Rename-Item -Path $ExtraidoGraf.FullName -NewName "grafana"
    }
    Write-Host "✅ Grafana listo en: $GrafanaDir" -ForegroundColor Green
} else {
    Write-Host "`n[2/2] Grafana ya está descargado en: $GrafanaDir" -ForegroundColor Green
}

# ---------------- 3. Aprovisionar Dashboards y Datasources en Grafana ----------------
Write-Host "`nConfigurando provisioning y dashboards en Grafana..." -ForegroundColor Yellow
$GrafanaProv = Join-Path $GrafanaDir "conf\provisioning"
if (-not (Test-Path $GrafanaProv)) { New-Item -ItemType Directory -Path $GrafanaProv | Out-Null }

# Copiar provisioning
Copy-Item -Path (Join-Path $Raiz "grafana\provisioning\*") -Destination $GrafanaProv -Recurse -Force

# Asegurar carpeta dashboards y copiar
$DashDir = "C:\var\lib\grafana\dashboards"
if (-not (Test-Path $DashDir)) { New-Item -ItemType Directory -Path $DashDir -Force | Out-Null }
Copy-Item -Path (Join-Path $Raiz "grafana\dashboards\*") -Destination $DashDir -Recurse -Force

# Configurar custom.ini para permitir embedding y autenticación anónima
$CustomIni = Join-Path $GrafanaDir "conf\custom.ini"
@"
[server]
http_port = 3000

[security]
allow_embedding = true

[auth.anonymous]
enabled = true
org_role = Viewer

[dashboards]
default_home_dashboard_path = C:/var/lib/grafana/dashboards/billetera.json
"@ | Set-Content -Path $CustomIni -Encoding utf8

Write-Host "✅ Grafana configurado con dashboards automáticos." -ForegroundColor Green
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " ¡Herramientas listas! Ahora puedes usar 'iniciar_todo.bat'" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
