"""
Script para inicializar la base de datos PostgreSQL (local o en la nube como Neon.tech)
sin necesidad de Docker.
"""
import os
import sys
from pathlib import Path
import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "api"))

# Cargar variables de entorno desde .env
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    db_pass = os.environ.get("DB_PASSWORD", "billetera_local")
    DATABASE_URL = f"postgresql://billetera:{db_pass}@localhost:5432/billetera"

print(f"Conectando a base de datos...")

try:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Esquema
            esquema_sql = (BASE_DIR / "db" / "01-esquema.sql").read_text(encoding="utf-8")
            sentencias = esquema_sql.split(";")
            for s in sentencias:
                sentencia = s.strip()
                if not sentencia:
                    continue
                # En servicios cloud (como Neon) CREATE USER puede requerir superusuario
                if "CREATE USER" in sentencia.upper() or "GRANT" in sentencia.upper():
                    try:
                        cur.execute(sentencia)
                    except Exception as e:
                        pass
                else:
                    try:
                        cur.execute(sentencia)
                    except Exception as e:
                        if "already exists" in str(e).lower() or "ya existe" in str(e).lower():
                            pass
                        else:
                            raise e
            print("✅ Tablas y categorías creadas correctamente.")

            # 2. Datos demo (si la tabla movimientos está vacía)
            cur.execute("SELECT COUNT(*) FROM movimientos;")
            total_movs = cur.fetchone()[0]
            if total_movs == 0:
                demo_path = BASE_DIR / "db" / "02-datos-demo.sql"
                if demo_path.exists():
                    demo_sql = demo_path.read_text(encoding="utf-8")
                    for s in demo_sql.split(";"):
                        sentencia = s.strip()
                        if sentencia:
                            cur.execute(sentencia)
                    print("✅ Datos de prueba (6 meses) cargados correctamente.")
            else:
                print(f"ℹ️ La base de datos ya contiene {total_movs} movimientos. Se conservan los datos.")

    print("\n🎉 ¡Base de datos inicializada con éxito!")
except Exception as e:
    print(f"\n❌ Error conectando a la base de datos: {e}")
    print("\nPor favor verifica tu DATABASE_URL en el archivo .env.")
