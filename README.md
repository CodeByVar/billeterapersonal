# 💰 Mi Billetera

Billetera móvil personal para administrar tus finanzas, con gráficos de **Grafana**.

![Stack](https://img.shields.io/badge/FastAPI-PostgreSQL-blue) ![Grafana](https://img.shields.io/badge/Grafana-11-orange)

## Funciones

- **Inicio:** saldo total animado, ingresos y gastos del mes, cuentas (efectivo, banco, tarjeta, ahorro) y últimos movimientos.
- **Registrar ingresos y gastos** con el botón ＋: monto, categoría con íconos, cuenta, fecha y descripción.
- **Movimientos:** historial agrupado por día, buscador, filtros y opción de eliminar.
- **Gráficos (Grafana):** ingresos vs gastos por mes, gastos por categoría, gasto diario, evolución del saldo y presupuesto usado.
- **Presupuesto:** define un tope mensual por categoría. La barra se pone amarilla al 80 % y roja al pasarte.
- **Ocultar montos** (👁️) para cuando alguien mira tu pantalla.
- **Diseño móvil (PWA):** se puede "instalar" en el celular como una app.

## Arquitectura

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│ App móvil    │────▶│ API (FastAPI)     │────▶│ PostgreSQL   │
│ HTML/CSS/JS  │     │ puerto 8000       │     │              │
│              │     └───────────────────┘     │              │
│  <iframe> ───┼──▶ /grafana/ ──▶ Grafana ───▶│ (solo lectura)│
└──────────────┘   (la API reenvía)            └──────────────┘
```

| Carpeta | Contenido |
|---|---|
| `api/main.py` | API REST (cuentas, categorías, movimientos, presupuestos) |
| `api/static/` | App móvil (`index.html`, `estilos.css`, `app.js`) |
| `db/01-esquema.sql` | Tablas, categorías por defecto y usuario de solo lectura para Grafana |
| `db/02-datos-demo.sql` | Datos de ejemplo de 6 meses (**bórralo si quieres empezar en blanco**) |
| `grafana/` | Fuente de datos y dashboard que se configuran solos |
| `renderer` (Docker) | Convierte los gráficos de Grafana en imágenes PNG para el celular |

## Cómo ejecutarlo

Requisitos: **Docker Desktop** abierto.

```bash
docker compose up -d --build
```

- 📱 App: http://localhost:8000
- 📊 Grafana: http://localhost:8000/grafana/ (usuario `admin`, contraseña `admin`)

Para apagarlo:

```bash
docker compose down
```

Para **borrar todos los datos** y empezar de cero (vuelve a cargar los scripts de `db/`):

```bash
docker compose down -v
```

## Usarlo desde tu celular

1. El celular y la PC deben estar en la **misma red Wi-Fi**.
2. Averigua la IP de tu PC con `ipconfig` (por ejemplo `192.168.1.50`).
3. En el celular abre `http://192.168.1.50:8000`
4. En Chrome: ⋮ → **Agregar a pantalla principal** para tenerla como app.

Los gráficos de Grafana se sirven desde la misma app (ruta `/grafana/`), así que el celular solo necesita el puerto 8000.
Además, Grafana los dibuja **como imágenes en la PC** (contenedor `renderer`), así que el celular solo descarga imágenes livianas. Si tocas un gráfico, se abre la versión interactiva.

> Si Windows pregunta por el firewall, permite el acceso en redes privadas.
> Las redes de universidades o empresas suelen bloquear la conexión entre dispositivos; en ese caso prueba en tu casa o con el hotspot del celular.

## Seguridad ⚠️

Este sistema está pensado para **uso personal en tu PC o red local**:
- La app **no tiene login**.
- Grafana permite **ver** los gráficos sin iniciar sesión (solo lectura). Grafana usa un usuario de base de datos que **no puede modificar datos**.
- **No lo publiques en internet** sin antes agregar autenticación, HTTPS y cambiar las contraseñas del archivo `.env`.

## Ideas para seguir mejorándolo

- Login de usuarios (JWT)
- Transferencias entre cuentas
- Movimientos recurrentes (sueldo, alquiler)
- Exportar a Excel o PDF
- Alertas de Grafana cuando superas un presupuesto
