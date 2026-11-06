"""
Billetera personal - API REST (FastAPI + PostgreSQL)

También sirve la app móvil (carpeta /static) en la raíz "/".
"""
import os
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

import httpx
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

DATABASE_URL = os.environ["DATABASE_URL"]
# Dirección interna de Grafana (dentro de Docker). La app la publica en /grafana/
GRAFANA_INTERNO = os.environ.get("GRAFANA_INTERNAL_URL", "http://grafana:3000")

app = FastAPI(title="Billetera personal")
cliente_grafana = httpx.AsyncClient(base_url=GRAFANA_INTERNO, timeout=60)


def db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def consultar(sql: str, params: tuple = ()) -> list[dict]:
    with db() as con:
        return con.execute(sql, params).fetchall()


def ejecutar(sql: str, params: tuple = ()) -> Optional[dict]:
    with db() as con:
        cur = con.execute(sql, params)
        return cur.fetchone() if cur.description else None


# ---------------------------------------------------------------- Modelos
class CuentaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    tipo: Literal["efectivo", "banco", "tarjeta", "ahorro"] = "efectivo"
    color: str = Field(default="#00d9f5", pattern=r"^#[0-9a-fA-F]{6}$")
    saldo_inicial: Decimal = Decimal(0)


class MovimientoIn(BaseModel):
    cuenta_id: int
    categoria_id: int
    tipo: Literal["ingreso", "gasto"]
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    descripcion: str = Field(default="", max_length=120)
    fecha: date = Field(default_factory=date.today)


class PresupuestoIn(BaseModel):
    monto: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


# ---------------------------------------------------------------- Config
@app.get("/api/config")
def config():
    # Ruta relativa: funciona igual en localhost, en la IP de la red o en un dominio
    return {"grafana_url": "/grafana", "moneda": "Bs"}


# ---------------------------------------------------------------- Proxy de Grafana
# Los gráficos se sirven desde el MISMO origen que la app (puerto 8000).
# Así el celular solo necesita una dirección y no hay problemas de puertos.
CABECERAS_OMITIR = {
    "host", "content-length", "transfer-encoding", "connection", "keep-alive",
    "upgrade", "te", "trailer", "proxy-authorization", "proxy-authenticate",
}


@app.api_route("/grafana/{ruta:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy_grafana(ruta: str, request: Request):
    url = httpx.URL(path=f"/grafana/{ruta}", query=request.url.query.encode())
    cabeceras = {k: v for k, v in request.headers.items() if k.lower() not in CABECERAS_OMITIR}
    peticion = cliente_grafana.build_request(
        request.method, url, headers=cabeceras, content=await request.body()
    )
    try:
        r = await cliente_grafana.send(peticion, stream=True)
    except httpx.HTTPError:
        raise HTTPException(502, "Grafana no está disponible")
    respuesta = StreamingResponse(r.aiter_raw(), status_code=r.status_code, background=BackgroundTask(r.aclose))
    respuesta.raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in r.headers.multi_items()
        if k.lower() not in CABECERAS_OMITIR
    ]
    return respuesta


# ---------------------------------------------------------------- Resumen
@app.get("/api/resumen")
def resumen():
    cuentas = consultar("""
        SELECT c.id, c.nombre, c.tipo, c.color,
               c.saldo_inicial + COALESCE(SUM(CASE WHEN m.tipo = 'ingreso' THEN m.monto ELSE -m.monto END), 0) AS saldo
        FROM cuentas c
        LEFT JOIN movimientos m ON m.cuenta_id = c.id
        GROUP BY c.id
        ORDER BY c.id
    """)
    mes = consultar("""
        SELECT COALESCE(SUM(monto) FILTER (WHERE tipo = 'ingreso'), 0) AS ingresos,
               COALESCE(SUM(monto) FILTER (WHERE tipo = 'gasto'), 0)   AS gastos
        FROM movimientos
        WHERE fecha >= date_trunc('month', CURRENT_DATE)
    """)[0]
    return {
        "saldo_total": sum((c["saldo"] for c in cuentas), Decimal(0)),
        "ingresos_mes": mes["ingresos"],
        "gastos_mes": mes["gastos"],
        "cuentas": cuentas,
    }


# ---------------------------------------------------------------- Cuentas
@app.get("/api/cuentas")
def listar_cuentas():
    return consultar("SELECT * FROM cuentas ORDER BY id")


@app.post("/api/cuentas", status_code=201)
def crear_cuenta(c: CuentaIn):
    return ejecutar(
        "INSERT INTO cuentas (nombre, tipo, color, saldo_inicial) VALUES (%s, %s, %s, %s) RETURNING *",
        (c.nombre, c.tipo, c.color, c.saldo_inicial),
    )


@app.delete("/api/cuentas/{cuenta_id}", status_code=204)
def borrar_cuenta(cuenta_id: int):
    if not ejecutar("DELETE FROM cuentas WHERE id = %s RETURNING id", (cuenta_id,)):
        raise HTTPException(404, "Cuenta no encontrada")


# ---------------------------------------------------------------- Categorías
@app.get("/api/categorias")
def listar_categorias():
    return consultar("SELECT * FROM categorias ORDER BY tipo, nombre")


# ---------------------------------------------------------------- Movimientos
@app.get("/api/movimientos")
def listar_movimientos(
    limite: int = Query(50, ge=1, le=500),
    tipo: Optional[Literal["ingreso", "gasto"]] = None,
    buscar: str = "",
):
    return consultar(
        """
        SELECT m.*, c.nombre AS categoria, c.icono, c.color, cu.nombre AS cuenta
        FROM movimientos m
        JOIN categorias c ON c.id = m.categoria_id
        JOIN cuentas cu   ON cu.id = m.cuenta_id
        WHERE (%(tipo)s::text IS NULL OR m.tipo = %(tipo)s)
          AND (%(buscar)s = '' OR m.descripcion ILIKE %(patron)s OR c.nombre ILIKE %(patron)s)
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT %(limite)s
        """,
        {"tipo": tipo, "buscar": buscar, "patron": f"%{buscar}%", "limite": limite},
    )


@app.post("/api/movimientos", status_code=201)
def crear_movimiento(m: MovimientoIn):
    cat = consultar("SELECT tipo FROM categorias WHERE id = %s", (m.categoria_id,))
    if not cat:
        raise HTTPException(400, "La categoría no existe")
    if cat[0]["tipo"] != m.tipo:
        raise HTTPException(400, "La categoría no corresponde al tipo de movimiento")
    if not consultar("SELECT 1 FROM cuentas WHERE id = %s", (m.cuenta_id,)):
        raise HTTPException(400, "La cuenta no existe")
    return ejecutar(
        """INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
        (m.cuenta_id, m.categoria_id, m.tipo, m.monto, m.descripcion.strip(), m.fecha),
    )


@app.delete("/api/movimientos/{mov_id}", status_code=204)
def borrar_movimiento(mov_id: int):
    if not ejecutar("DELETE FROM movimientos WHERE id = %s RETURNING id", (mov_id,)):
        raise HTTPException(404, "Movimiento no encontrado")


# ---------------------------------------------------------------- Presupuestos
@app.get("/api/presupuestos")
def listar_presupuestos():
    """Presupuesto del mes actual por categoría de gasto, con lo gastado."""
    return consultar("""
        SELECT c.id AS categoria_id, c.nombre, c.icono, c.color,
               p.monto AS presupuesto,
               COALESCE(SUM(m.monto), 0) AS gastado
        FROM categorias c
        LEFT JOIN presupuestos p ON p.categoria_id = c.id
        LEFT JOIN movimientos m  ON m.categoria_id = c.id
                                AND m.fecha >= date_trunc('month', CURRENT_DATE)
        WHERE c.tipo = 'gasto'
        GROUP BY c.id, p.monto
        ORDER BY (p.monto IS NULL), c.nombre
    """)


@app.put("/api/presupuestos/{categoria_id}")
def guardar_presupuesto(categoria_id: int, p: PresupuestoIn):
    if not consultar("SELECT 1 FROM categorias WHERE id = %s AND tipo = 'gasto'", (categoria_id,)):
        raise HTTPException(400, "Solo se puede presupuestar una categoría de gasto")
    if p.monto == 0:
        ejecutar("DELETE FROM presupuestos WHERE categoria_id = %s", (categoria_id,))
        return {"categoria_id": categoria_id, "monto": None}
    return ejecutar(
        """INSERT INTO presupuestos (categoria_id, monto) VALUES (%s, %s)
           ON CONFLICT (categoria_id) DO UPDATE SET monto = EXCLUDED.monto RETURNING *""",
        (categoria_id, p.monto),
    )


# ---------------------------------------------------------------- App móvil
app.mount("/", StaticFiles(directory="static", html=True), name="static")
