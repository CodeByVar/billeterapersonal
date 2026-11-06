# Conectar la billetera a Grafana Cloud

Tu base de datos vive en tu PC (Docker) y Grafana Cloud vive en internet, así que
Grafana Cloud **no puede verla directamente**. Para unirlos se usa **Private Data
Source Connect (PDC)**: un agente que corre en tu PC y abre un túnel seguro **de
salida** hacia tu Grafana Cloud.

- ✅ No abres puertos ni publicas tu base de datos en internet.
- ✅ Funciona incluso en la red de la universidad.
- ⚠️ Tu PC tiene que estar encendida con Docker abierto para ver los datos.

---

## Paso 1: Crear la conexión privada en Grafana Cloud

1. Entra a tu Grafana Cloud (`https://TU-USUARIO.grafana.net`).
2. Menú izquierdo → **Connections** → **Private data source connections**.
3. Botón **Add new network**, con el nombre `billetera`.
4. Elige la pestaña **Docker** y pulsa **Create a new token**.
5. Grafana te muestra un comando parecido a este:
   ```
   docker run --name pdc-agent grafana/pdc-agent:latest -token glc_xxxxx -cluster prod-us-east-0 -gcloud-hosted-grafana-id 123456
   ```
   **No lo ejecutes.** Solo copia los 3 valores.

## Paso 2: Pegar los valores en tu `.env`

Abre `billetera/.env` y completa:

```
PDC_TOKEN=glc_xxxxx            (el valor después de -token)
PDC_CLUSTER=prod-us-east-0     (el valor después de -cluster)
PDC_GRAFANA_ID=123456          (el valor después de -gcloud-hosted-grafana-id)
```

> 🔒 El token es como una contraseña: no lo compartas ni lo subas a GitHub
> (`.env` ya está en `.gitignore`).

## Paso 3: Encender el agente

En la carpeta `billetera`:

```bash
docker compose --profile cloud up -d
```

Comprueba que se conectó:

```bash
docker compose logs pdc
```

Deberías ver mensajes de conexión exitosa. En Grafana Cloud, la red `billetera`
aparecerá como **connected**.

## Paso 4: Crear la fuente de datos PostgreSQL

1. **Connections** → **Add new connection** → busca **PostgreSQL** → **Add new data source**.
2. Completa:

   | Campo | Valor |
   |---|---|
   | Name | `Billetera` |
   | Host URL | `db:5432` |
   | Database name | `billetera` |
   | Username | `grafana_lector` |
   | Password | `grafana_lector` |
   | TLS/SSL Mode | `disable` |
   | **Private data source connect** | elige la red `billetera` |

3. Pulsa **Save & test**. Debe salir ✅ *Database Connection OK*.

> El usuario `grafana_lector` solo puede **leer**: Grafana Cloud no puede
> modificar ni borrar tus datos.

## Paso 5: Importar el dashboard

1. **Dashboards** → **New** → **Import**.
2. **Upload dashboard JSON file** → elige `billetera/grafana-cloud/dashboard-billetera.json`.
3. En *Base de datos Billetera*, selecciona la fuente `Billetera` del paso 4.
4. Pulsa **Import**. 🎉

Ya tienes los 8 gráficos en tu Grafana Cloud, y puedes verlos desde cualquier
lugar (también desde la app de Grafana en el celular).

---

## Problemas comunes

| Problema | Solución |
|---|---|
| "Save & test" falla | Revisa `docker compose logs pdc` y que hayas elegido la red PDC en la fuente de datos |
| Los paneles dicen *No data* | Tu PC está apagada o Docker cerrado |
| El dashboard ya existe | Al importar, cambia el nombre o el UID |

## ¿Y si quiero que funcione con la PC apagada?

Necesitas mover la base de datos a la nube (por ejemplo **Neon** o **Supabase**,
ambos con plan gratis). Así Grafana Cloud y la app leen la misma base las 24 horas.
Para eso la app **necesita login** antes de publicarse en internet.
