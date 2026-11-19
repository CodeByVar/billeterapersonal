# 💰 Mi Billetera - Finanzas Personales con PostgreSQL, InfluxDB y Grafana

Billetera móvil personal (PWA) para administrar finanzas en tiempo real, con almacenamiento transaccional en **PostgreSQL**, métricas de series temporales en **InfluxDB** y dashboards dinámicos interactivos con reportes en **Grafana**.

![Stack](https://img.shields.io/badge/FastAPI-PostgreSQL-blue) ![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-purple) ![Grafana](https://img.shields.io/badge/Grafana-11-orange)

---

## 🌟 Arquitectura del Sistema (Dual Database)

El proyecto utiliza una **arquitectura híbrida de bases de datos** recomendada para analítica moderna:

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────────────────────┐
│  App Móvil   │────▶│   API (FastAPI)   │────▶│ PostgreSQL 16 (Relacional)       │
│  HTML/CSS/JS │     │   puerto 8000     │     │ • Cuentas, categorías,           │
│    (PWA)     │     └────────┬──────────┘     │   presupuestos, movimientos      │
│              │              │                └──────────────────────────────────┘
│              │              │                ┌──────────────────────────────────┐
│  Estadísticas│              └───────────────▶│ InfluxDB 2.7 (Series de Tiempo)  │
│  en la App   │                               │ • Eventos de movimientos         │
│  (PNG / Web) │                               │ • Telemetría histórica de saldos │
│      ▲       │                               │ • Flujos netos y resumen         │
│      │       │     ┌───────────────────┐     └────────────────┬─────────────────┘
│      └───────┼────▶│ Grafana 11        │                      │
│   /grafana/  │     │ (Dashboards       │◀─────────────────────┘
└──────────────┘     │  Dinámicos)       │ (Consultas con lenguaje Flux)
                     └───────────────────┘
```

### ¿Por qué dos bases de datos?
1. **PostgreSQL (Base Relacional / Transaccional)**:
   - Garantiza consistencia **ACID**.
   - Almacena el modelo relacional estructurado: catálogo de cuentas, categorías, montos tope de presupuestos mensuales y los registros maestros de transacciones.
2. **InfluxDB (Base de Datos de Series de Tiempo - TSDB)**:
   - Especializada en almacenamiento cronológico de alta velocidad y compresión temporal.
   - Modela cada gasto/ingreso como un **evento temporal** con marcas de tiempo precisas (*timestamp*), indexado por etiquetas (*tags*) para consultas analíticas multidimensionales instantáneas.
   - Permite agregaciones estadísticas continuas (promedios, tendencias, ventanas temporales con `aggregateWindow`) en Grafana.

---

## 🗄️ Variables y Parámetros Almacenados

### 1. Variables en PostgreSQL
| Tabla | Columnas / Variables | Tipo | Descripción |
|---|---|---|---|
| `cuentas` | `id`, `nombre`, `tipo`, `color`, `saldo_inicial`, `creado` | Relacional | Tipos: `efectivo`, `banco`, `tarjeta`, `ahorro` |
| `categorias`| `id`, `nombre`, `tipo`, `icono`, `color` | Relacional | Tipos: `ingreso` o `gasto` |
| `movimientos`| `id`, `cuenta_id`, `categoria_id`, `tipo`, `monto`, `descripcion`, `fecha`, `creado` | Relacional | Registro transaccional diario |
| `presupuestos`| `categoria_id`, `monto` | Relacional | Límite mensual presupuestado |

### 2. Variables y Estructura en InfluxDB
- **Organización:** `billetera_org` | **Bucket:** `billetera_metricas`

| Measurement | Tags (Dimensiones de búsqueda) | Fields (Métricas numéricas y datos) | Timestamp |
|---|---|---|---|
| `movimientos` | `tipo` (`ingreso`/`gasto`), `cuenta`, `categoria` | `monto` (float), `id` (int), `descripcion` (string) | Fecha del movimiento (`_time`) |
| `cuentas` | `cuenta`, `tipo` | `saldo` (float), `cuenta_id` (int) | Momento de registro (`_time`) |
| `resumen` | *(Agrupación global)* | `saldo_total` (float), `ingresos_mes` (float), `gastos_mes` (float), `flujo_neto` (float) | Momento de registro (`_time`) |

---

## 📊 Dashboards y Variables Dinámicas en Grafana

Grafana incluye 2 dashboards listos:
1. **Mi Billetera (PostgreSQL):** Vistas analíticas relacionales (Ingresos vs Gastos por mes, distribución por donut, barras de presupuesto usado).
2. **Reportes y Telemetría Financiera (InfluxDB):** Dashboard dinámico impulsado por el lenguaje **Flux**:
   - **Variables dinámicas (Filtros en el encabezado):**
     - `$tipo`: Permite filtrar al instante entre *Todos*, *Ingresos* o *Gastos*.
     - `$cuenta`: Permite segmentar el análisis por cuenta (*Efectivo*, *Banco BNB*, *Tarjeta Visa*, *Ahorro* o *Todas*).
   - **Métricas y reportes:**
     - **KPI Stat:** Total de movimientos registrados en la serie temporal.
     - **KPI Stat:** Volumen transaccional total (Suma de montos).
     - **KPI Stat:** Monto promedio por transacción (Ticket promedio).
     - **KPI Stat:** Flujo neto mensual (Superávit/Déficit).
     - **Time Series:** Serie temporal de transacciones agrupadas diariamente con `aggregateWindow(every: 1d, fn: sum)`.
     - **Pie/Donut:** Distribución porcentual por cuenta.
     - **Bar Chart:** Gastos totales clasificados por categoría.
     - **Time Series:** Evolución cronológica de saldos por cuenta.
     - **Tabla:** Auditoría y registro detallado de eventos de telemetría financiera.

---

## 🚀 Cómo Ejecutar el Proyecto

Tienes dos formas de ejecutarlo: **Sin Docker (Nativo en Windows)** o **Con Docker**.

---

### 🔹 Opción A: Sin Docker (Nativo en Windows - Recomendado)

No necesitas instalar Docker. Todo corre directamente en tu PC con scripts automáticos que ya dejé listos:

1. **Base de Datos PostgreSQL (Elige una de las dos):**
   * **Recomendada (0 instalaciones en tu PC):** Crea una cuenta gratis en [Neon.tech](https://neon.tech), crea un proyecto "billetera", copia la URL de conexión y colócala en tu archivo `.env`:
     ```env
     DATABASE_URL=postgresql://usuario:contraseña@ep-xyz.aws.neon.tech/neondb?sslmode=require
     ```
   * *O bien*, si tienes PostgreSQL instalado localmente en Windows, pon tu contraseña en `.env` (`DB_PASSWORD=tu_contraseña`).

2. **Inicializar las tablas y datos demo:**
   * Haz doble clic en el archivo:
     ```text
     inicializar_base_datos.bat
     ```
     *(Crea automáticamente las tablas en PostgreSQL y carga los 6 meses de datos de prueba).*

3. **Iniciar Todo el Sistema:**
   * Haz doble clic en el archivo:
     ```text
     iniciar_todo.bat
     ```
     *(La primera vez descargará InfluxDB y Grafana portables automáticamente y luego levantará la API, InfluxDB y Grafana en ventanas separadas, abriendo la app en tu navegador).*

---

### 🔹 Opción B: Con Docker Desktop

Si tienes Docker instalado y abierto:

```bash
docker compose up -d --build
```

---

### URLs de Acceso:
- 📱 **App Web / Móvil:** [http://localhost:8000](http://localhost:8000)
- 📊 **Grafana (Dashboards):** [http://localhost:8000/grafana/](http://localhost:8000/grafana/) o [http://localhost:3000](http://localhost:3000)
- 📈 **InfluxDB Web UI:** [http://localhost:8086](http://localhost:8086) (Usuario: `admin`, Contraseña: `adminpassword123`)

Para sincronizar todos los datos iniciales de PostgreSQL a InfluxDB manualmente en cualquier momento:
- En la app móvil ve a la pestaña **Gráficos** y pulsa el botón **`⚡ Sync Influx`**, o haz un POST a:
  ```bash
  curl -X POST http://localhost:8000/api/influx/sincronizar
  ```

Para apagar el sistema:
```bash
docker compose down
```

Para reiniciar y borrar datos:
```bash
docker compose down -v
```
