"""
Cliente y sincronizador de métricas para InfluxDB (Base de datos de series de tiempo).
Permite almacenar eventos financieros, saldos históricos y métricas de rendimiento en InfluxDB.
"""
import os
import logging
from pathlib import Path
from datetime import datetime, timezone, time
from decimal import Decimal
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import httpx

logger = logging.getLogger("billetera.influx")

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "billetera-super-secret-token-influxdb-2024")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "billetera_org")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "billetera_metricas")


def asegurar_setup_influx():
    """Si InfluxDB es nuevo y no tiene onboarding, lo inicializa automáticamente."""
    try:
        with httpx.Client(timeout=5) as http:
            r = http.get(f"{INFLUXDB_URL}/api/v2/setup")
            if r.status_code == 200 and r.json().get("allowed") is True:
                logger.info("Inicializando configuración inicial de InfluxDB...")
                http.post(
                    f"{INFLUXDB_URL}/api/v2/setup",
                    json={
                        "username": "admin",
                        "password": os.environ.get("INFLUX_PASSWORD", "adminpassword123"),
                        "org": INFLUXDB_ORG,
                        "bucket": INFLUXDB_BUCKET,
                        "token": INFLUXDB_TOKEN,
                    },
                )
    except Exception as e:
        logger.debug("Auto-setup no requerido o no disponible: %s", e)


def obtener_cliente() -> InfluxDBClient:
    return InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        timeout=10000,
    )


def verificar_conexion() -> Dict[str, Any]:
    try:
        with obtener_cliente() as client:
            ready = client.ready()
            ping = client.ping()
            return {
                "conectado": ping,
                "url": INFLUXDB_URL,
                "org": INFLUXDB_ORG,
                "bucket": INFLUXDB_BUCKET,
                "estado": ready.status if hasattr(ready, "status") else "activo",
            }
    except Exception as e:
        logger.warning("No se pudo conectar a InfluxDB: %s", e)
        return {
            "conectado": False,
            "url": INFLUXDB_URL,
            "org": INFLUXDB_ORG,
            "bucket": INFLUXDB_BUCKET,
            "error": str(e),
        }


def registrar_movimiento_influx(
    mov_id: int,
    cuenta_nombre: str,
    categoria_nombre: str,
    tipo: str,
    monto: float | Decimal,
    descripcion: str = "",
    fecha_dt: Optional[datetime] = None,
) -> bool:
    """Registra una transacción individual como punto de serie temporal en InfluxDB."""
    try:
        if fecha_dt is None:
            fecha_dt = datetime.now(timezone.utc)
        elif fecha_dt.tzinfo is None:
            fecha_dt = fecha_dt.replace(tzinfo=timezone.utc)

        punto = (
            Point("movimientos")
            .tag("tipo", tipo)
            .tag("cuenta", cuenta_nombre)
            .tag("categoria", categoria_nombre)
            .field("monto", float(monto))
            .field("id", int(mov_id))
            .field("descripcion", descripcion or "")
            .time(fecha_dt, WritePrecision.S)
        )

        with obtener_cliente() as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=punto)
        return True
    except Exception as e:
        logger.warning("Error al registrar movimiento en InfluxDB: %s", e)
        return False


def registrar_saldos_influx(cuentas: List[Dict[str, Any]]) -> bool:
    """Registra los saldos actuales por cuenta en InfluxDB."""
    try:
        ahora = datetime.now(timezone.utc)
        puntos = []
        for c in cuentas:
            p = (
                Point("cuentas")
                .tag("cuenta", c.get("nombre", "Desconocida"))
                .tag("tipo", c.get("tipo", "general"))
                .field("saldo", float(c.get("saldo", 0)))
                .field("cuenta_id", int(c.get("id", 0)))
                .time(ahora, WritePrecision.S)
            )
            puntos.append(p)

        if puntos:
            with obtener_cliente() as client:
                write_api = client.write_api(write_options=SYNCHRONOUS)
                write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=puntos)
        return True
    except Exception as e:
        logger.warning("Error al registrar saldos en InfluxDB: %s", e)
        return False


def registrar_resumen_global_influx(
    saldo_total: float | Decimal,
    ingresos_mes: float | Decimal,
    gastos_mes: float | Decimal,
) -> bool:
    """Registra las métricas agregadas globales en InfluxDB."""
    try:
        ahora = datetime.now(timezone.utc)
        s_total = float(saldo_total)
        ing_mes = float(ingresos_mes)
        gas_mes = float(gastos_mes)
        flujo_neto = ing_mes - gas_mes

        punto = (
            Point("resumen")
            .field("saldo_total", s_total)
            .field("ingresos_mes", ing_mes)
            .field("gastos_mes", gas_mes)
            .field("flujo_neto", flujo_neto)
            .time(ahora, WritePrecision.S)
        )

        with obtener_cliente() as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=punto)
        return True
    except Exception as e:
        logger.warning("Error al registrar resumen en InfluxDB: %s", e)
        return False


def sincronizar_todo_desde_postgres(consultar_fn) -> Dict[str, Any]:
    """
    Lee toda la información histórica de PostgreSQL y la sincroniza por lotes a InfluxDB.
    Esto garantiza que los dashboards de Grafana muestren datos de inmediato.
    """
    try:
        # 1. Obtener movimientos
        movimientos = consultar_fn("""
            SELECT m.id, m.tipo, m.monto, m.descripcion, m.fecha,
                   c.nombre AS categoria, cu.nombre AS cuenta, cu.tipo AS cuenta_tipo
            FROM movimientos m
            JOIN categorias c ON c.id = m.categoria_id
            JOIN cuentas cu   ON cu.id = m.cuenta_id
            ORDER BY m.fecha ASC, m.id ASC
        """)

        puntos: List[Point] = []
        for m in movimientos:
            # Convertir fecha a datetime con hora fija (12:00:00 UTC) para consistencia
            fecha = m["fecha"]
            if isinstance(fecha, str):
                dt = datetime.fromisoformat(fecha).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.combine(fecha, time(12, 0, 0, tzinfo=timezone.utc))

            punto = (
                Point("movimientos")
                .tag("tipo", m["tipo"])
                .tag("cuenta", m["cuenta"])
                .tag("categoria", m["categoria"])
                .field("monto", float(m["monto"]))
                .field("id", int(m["id"]))
                .field("descripcion", m["descripcion"] or "")
                .time(dt, WritePrecision.S)
            )
            puntos.append(punto)

        # 2. Obtener saldos de cuentas
        cuentas = consultar_fn("""
            SELECT c.id, c.nombre, c.tipo,
                   c.saldo_inicial + COALESCE(SUM(CASE WHEN m.tipo = 'ingreso' THEN m.monto ELSE -m.monto END), 0) AS saldo
            FROM cuentas c
            LEFT JOIN movimientos m ON m.cuenta_id = c.id
            GROUP BY c.id
            ORDER BY c.id
        """)
        ahora = datetime.now(timezone.utc)
        for c in cuentas:
            punto_cuenta = (
                Point("cuentas")
                .tag("cuenta", c["nombre"])
                .tag("tipo", c["tipo"])
                .field("saldo", float(c["saldo"]))
                .field("cuenta_id", int(c["id"]))
                .time(ahora, WritePrecision.S)
            )
            puntos.append(punto_cuenta)

        # 3. Resumen global
        mes = consultar_fn("""
            SELECT COALESCE(SUM(monto) FILTER (WHERE tipo = 'ingreso'), 0) AS ingresos,
                   COALESCE(SUM(monto) FILTER (WHERE tipo = 'gasto'), 0)   AS gastos
            FROM movimientos
            WHERE fecha >= date_trunc('month', CURRENT_DATE)
        """)[0]
        saldo_total = sum((c["saldo"] for c in cuentas), Decimal(0))
        punto_resumen = (
            Point("resumen")
            .field("saldo_total", float(saldo_total))
            .field("ingresos_mes", float(mes["ingresos"]))
            .field("gastos_mes", float(mes["gastos"]))
            .field("flujo_neto", float(mes["ingresos"] - mes["gastos"]))
            .time(ahora, WritePrecision.S)
        )
        puntos.append(punto_resumen)

        # Enviar por lotes a InfluxDB
        if puntos:
            with obtener_cliente() as client:
                write_api = client.write_api(write_options=SYNCHRONOUS)
                # Influx soporta listas de Point directamente
                write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=puntos)

        return {
            "estado": "exito",
            "puntos_sincronizados": len(puntos),
            "movimientos": len(movimientos),
            "cuentas": len(cuentas),
        }
    except Exception as e:
        logger.error("Error durante la sincronización a InfluxDB: %s", e)
        return {
            "estado": "error",
            "detalle": str(e),
        }

