// =========================================================
//  Mi Billetera - lógica de la app móvil
// =========================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const estado = {
  grafana: "http://localhost:3000",
  categorias: [],
  cuentas: [],
  tipoMov: "gasto",
  categoriaSel: null,
  filtroTipo: "",
  rango: "now-2M/M",
  colorCuenta: "#00d9f5",
};

const ICONOS_CUENTA = { efectivo: "💵", banco: "🏦", tarjeta: "💳", ahorro: "🐷" };
const COLORES = ["#00f5a0", "#00d9f5", "#a855f7", "#ff5ea8", "#f59e0b", "#6366f1", "#14b8a6", "#ef4444"];

// ---------------------------------------------------------------- Utilidades
const formato = new Intl.NumberFormat("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const bs = (n) => `Bs ${formato.format(Number(n))}`;

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

function hoyISO() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

function fechaBonita(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  const fecha = new Date(a, m - 1, d);
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  const dias = Math.round((hoy - fecha) / 86400000);
  if (dias === 0) return "Hoy";
  if (dias === 1) return "Ayer";
  return fecha.toLocaleDateString("es-BO", { weekday: "long", day: "numeric", month: "long" });
}

async function api(ruta, opciones = {}) {
  const res = await fetch(`/api${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (!res.ok) {
    let msg = "Ocurrió un error";
    try {
      const err = await res.json();
      msg = typeof err.detail === "string" ? err.detail : "Revisa los datos ingresados";
    } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

let toastTimer;
function toast(texto) {
  const t = $("#toast");
  t.textContent = texto;
  t.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("visible"), 2200);
}

// Anima un número desde 0 hasta su valor final
function contar(el, valor) {
  const inicio = performance.now();
  const dur = 700;
  const paso = (t) => {
    const p = Math.min(1, (t - inicio) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = bs(valor * eased);
    if (p < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// ---------------------------------------------------------------- Navegación
function ir(vista) {
  $$(".vista").forEach((v) => v.classList.toggle("activa", v.id === `vista-${vista}`));
  $$(".barra-nav [data-ir]").forEach((b) => b.classList.toggle("activo", b.dataset.ir === vista));
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (vista === "inicio") cargarInicio();
  if (vista === "movimientos") cargarMovimientos();
  if (vista === "graficos") cargarPaneles("#vista-graficos");
  if (vista === "presupuesto") cargarPresupuestos();
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-ir]");
  if (b) ir(b.dataset.ir);
});

// ---------------------------------------------------------------- Grafana
// Grafana dibuja cada gráfico como imagen PNG en el servidor.
// Así el celular solo descarga imágenes livianas (no toda la app de Grafana).
const ZONA = Intl.DateTimeFormat().resolvedOptions().timeZone || "America/La_Paz";

function urlPanel(id, desde, tipo = "d-solo", extra = {}) {
  const p = new URLSearchParams({
    orgId: 1, panelId: id, from: desde, to: "now", theme: "dark", tz: ZONA, ...extra,
  });
  return `${estado.grafana}/${tipo}/billetera/billetera?${p}`;
}

function cargarPaneles(contenedor) {
  $$(`${contenedor} .panel-grafana`).forEach((div) => {
    const desde = div.dataset.rango || estado.rango;
    const ancho = Math.round(div.clientWidth) || 340;
    const alto = Math.round(div.clientHeight) || 260;
    div.innerHTML = `<div class="cargando">Cargando gráfico…</div>`;

    const img = document.createElement("img");
    img.alt = "Gráfico de Grafana";
    img.src = urlPanel(div.dataset.panel, desde, "render/d-solo", {
      width: ancho, height: alto, scale: Math.min(3, Math.ceil(window.devicePixelRatio || 1)), _: Date.now(),
    });
    img.onload = () => div.querySelector(".cargando")?.remove();
    img.onerror = () => {
      div.querySelector(".cargando").textContent = "No se pudo cargar el gráfico. Toca para reintentar.";
      div.onclick = () => { div.onclick = null; cargarPaneles(`#${div.closest(".vista").id}`); };
    };
    // Al tocar el gráfico se abre la versión interactiva de Grafana
    img.addEventListener("click", () => window.open(urlPanel(div.dataset.panel, desde), "_blank"));
    div.appendChild(img);
  });
}

$("#filtro-rango").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  $$("#filtro-rango .chip").forEach((c) => c.classList.toggle("activo", c === chip));
  estado.rango = chip.dataset.rango;
  cargarPaneles("#vista-graficos");
});

// ---------------------------------------------------------------- Inicio
function htmlMovimiento(m, conBorrar = false) {
  const signo = m.tipo === "ingreso" ? "+" : "−";
  return `
    <li class="mov" style="--color:${m.color}">
      <div class="ico">${m.icono}</div>
      <div class="info">
        <strong>${escapar(m.descripcion || m.categoria)}</strong>
        <small>${escapar(m.categoria)} · ${escapar(m.cuenta)}</small>
      </div>
      <span class="valor ${m.tipo} monto">${signo} ${bs(m.monto)}</span>
      ${conBorrar ? `<button class="borrar" data-borrar-mov="${m.id}" title="Eliminar" aria-label="Eliminar">🗑️</button>` : ""}
    </li>`;
}

async function cargarInicio() {
  try {
    const [r, movs] = await Promise.all([api("/resumen"), api("/movimientos?limite=5")]);
    estado.cuentas = r.cuentas;
    contar($("#saldo-total"), Number(r.saldo_total));
    contar($("#ingresos-mes"), Number(r.ingresos_mes));
    contar($("#gastos-mes"), Number(r.gastos_mes));

    $("#lista-cuentas").innerHTML = r.cuentas.length
      ? r.cuentas.map((c) => `
          <div class="cuenta" style="--color:${c.color}">
            <button class="borrar" data-borrar-cuenta="${c.id}" data-nombre="${escapar(c.nombre)}" title="Eliminar cuenta">✕</button>
            <div class="ico">${ICONOS_CUENTA[c.tipo] || "💰"}</div>
            <p>${escapar(c.nombre)}</p>
            <strong class="monto">${bs(c.saldo)}</strong>
          </div>`).join("")
      : `<p class="vacio">Crea tu primera cuenta con “+ Nueva”</p>`;

    $("#ultimos-movs").innerHTML = movs.length
      ? movs.map((m) => htmlMovimiento(m)).join("")
      : `<li class="vacio">Aún no tienes movimientos.<br>Toca ＋ para registrar el primero.</li>`;

    cargarPaneles("#vista-inicio");
  } catch (e) {
    toast("⚠️ " + e.message);
  }
}

// ---------------------------------------------------------------- Movimientos
let busquedaTimer;
$("#buscador").addEventListener("input", () => {
  clearTimeout(busquedaTimer);
  busquedaTimer = setTimeout(cargarMovimientos, 300);
});
$("#filtro-tipo").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  $$("#filtro-tipo .chip").forEach((c) => c.classList.toggle("activo", c === chip));
  estado.filtroTipo = chip.dataset.tipo;
  cargarMovimientos();
});

async function cargarMovimientos() {
  const p = new URLSearchParams({ limite: 200, buscar: $("#buscador").value.trim() });
  if (estado.filtroTipo) p.set("tipo", estado.filtroTipo);
  try {
    const movs = await api(`/movimientos?${p}`);
    if (!movs.length) {
      $("#movs-agrupados").innerHTML = `<p class="vacio">No se encontraron movimientos 🔍</p>`;
      return;
    }
    const grupos = {};
    movs.forEach((m) => (grupos[m.fecha] ??= []).push(m));
    $("#movs-agrupados").innerHTML = Object.entries(grupos).map(([fecha, lista]) => `
      <p class="fecha-grupo">${fechaBonita(fecha)}</p>
      <ul class="lista-movs">${lista.map((m) => htmlMovimiento(m, true)).join("")}</ul>
    `).join("");
  } catch (e) {
    toast("⚠️ " + e.message);
  }
}

// ---------------------------------------------------------------- Presupuestos
async function cargarPresupuestos() {
  $("#mes-actual").textContent = new Date().toLocaleDateString("es-BO", { month: "long", year: "numeric" });
  try {
    const lista = await api("/presupuestos");
    $("#lista-presu").innerHTML = lista.map((p) => {
      const gastado = Number(p.gastado);
      if (!p.presupuesto) {
        return `
          <li class="presu sin-presu" data-presu="${p.categoria_id}" data-nombre="${escapar(p.nombre)}">
            <div class="cabeza"><span>${p.icono}</span><strong>${escapar(p.nombre)}</strong><small>Sin presupuesto</small></div>
            <div class="pie"><span>Gastado: <b class="monto">${bs(gastado)}</b></span><span>Toca para definir</span></div>
          </li>`;
      }
      const tope = Number(p.presupuesto);
      const pct = (gastado / tope) * 100;
      const clase = pct >= 100 ? "excedido" : pct >= 80 ? "alerta" : "";
      const resto = tope - gastado;
      return `
        <li class="presu" data-presu="${p.categoria_id}" data-nombre="${escapar(p.nombre)}" data-monto="${tope}">
          <div class="cabeza"><span>${p.icono}</span><strong>${escapar(p.nombre)}</strong><small>${Math.round(pct)}%</small></div>
          <div class="barra"><div class="${clase}" style="width:0" data-ancho="${Math.min(100, pct)}%"></div></div>
          <div class="pie">
            <span class="monto">${bs(gastado)} de ${bs(tope)}</span>
            <span class="monto">${resto >= 0 ? `Quedan ${bs(resto)}` : `⚠️ Excedido ${bs(-resto)}`}</span>
          </div>
        </li>`;
    }).join("");
    // animar las barras
    requestAnimationFrame(() => $$(".barra div").forEach((b) => (b.style.width = b.dataset.ancho)));
  } catch (e) {
    toast("⚠️ " + e.message);
  }
}

// ---------------------------------------------------------------- Modales
function abrir(id) { $(id).hidden = false; }
function cerrar(modal) { modal.hidden = true; }
$$(".modal").forEach((m) => {
  m.addEventListener("click", (e) => {
    if (e.target === m || e.target.closest("[data-cerrar]")) cerrar(m);
  });
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") $$(".modal").forEach(cerrar);
});

let confirmarAccion = null;
function confirmar(titulo, texto, accion) {
  $("#conf-titulo").textContent = titulo;
  $("#conf-texto").textContent = texto;
  confirmarAccion = accion;
  abrir("#modal-confirmar");
}
$("#conf-ok").addEventListener("click", async () => {
  cerrar($("#modal-confirmar"));
  if (confirmarAccion) await confirmarAccion();
});

// ----- Nuevo movimiento
function pintarCategorias() {
  const lista = estado.categorias.filter((c) => c.tipo === estado.tipoMov);
  if (!lista.some((c) => c.id === estado.categoriaSel)) estado.categoriaSel = lista[0]?.id ?? null;
  $("#grid-cat").innerHTML = lista.map((c) => `
    <button type="button" class="cat ${c.id === estado.categoriaSel ? "activo" : ""}" style="--color:${c.color}" data-cat="${c.id}">
      <span>${c.icono}</span>${escapar(c.nombre)}
    </button>`).join("");
}

$("#grid-cat").addEventListener("click", (e) => {
  const b = e.target.closest("[data-cat]");
  if (!b) return;
  estado.categoriaSel = Number(b.dataset.cat);
  pintarCategorias();
});

$(".selector-tipo").addEventListener("click", (e) => {
  const b = e.target.closest("[data-tipo]");
  if (!b) return;
  estado.tipoMov = b.dataset.tipo;
  $$(".selector-tipo button").forEach((x) => x.classList.toggle("activo", x === b));
  pintarCategorias();
});

$("#btn-agregar").addEventListener("click", async () => {
  if (!estado.cuentas.length) {
    estado.cuentas = (await api("/resumen")).cuentas;
  }
  if (!estado.cuentas.length) {
    toast("Primero crea una cuenta 👛");
    abrirNuevaCuenta();
    return;
  }
  $("#form-mov").reset();
  $("#mov-error").textContent = "";
  $("#mov-fecha").value = hoyISO();
  $("#mov-cuenta").innerHTML = estado.cuentas
    .map((c) => `<option value="${c.id}">${ICONOS_CUENTA[c.tipo] || "💰"} ${escapar(c.nombre)}</option>`)
    .join("");
  pintarCategorias();
  abrir("#modal-mov");
  setTimeout(() => $("#mov-monto").focus(), 300);
});

$("#form-mov").addEventListener("submit", async (e) => {
  e.preventDefault();
  const boton = e.target.querySelector('[type="submit"]');
  if (!estado.categoriaSel) {
    $("#mov-error").textContent = "Elige una categoría";
    return;
  }
  boton.disabled = true;
  try {
    await api("/movimientos", {
      method: "POST",
      body: JSON.stringify({
        tipo: estado.tipoMov,
        monto: $("#mov-monto").value,
        categoria_id: estado.categoriaSel,
        cuenta_id: Number($("#mov-cuenta").value),
        fecha: $("#mov-fecha").value,
        descripcion: $("#mov-desc").value,
      }),
    });
    cerrar($("#modal-mov"));
    toast(estado.tipoMov === "ingreso" ? "💰 Ingreso registrado" : "💸 Gasto registrado");
    refrescarVistaActual();
  } catch (err) {
    $("#mov-error").textContent = err.message;
  } finally {
    boton.disabled = false;
  }
});

// ----- Nueva cuenta
function abrirNuevaCuenta() {
  $("#form-cuenta").reset();
  $("#cta-error").textContent = "";
  estado.colorCuenta = COLORES[estado.cuentas.length % COLORES.length];
  pintarColores();
  abrir("#modal-cuenta");
}
function pintarColores() {
  $("#cta-colores").innerHTML = COLORES.map((c) =>
    `<button type="button" style="background:${c}" class="${c === estado.colorCuenta ? "activo" : ""}" data-color="${c}" aria-label="Color ${c}"></button>`
  ).join("");
}
$("#cta-colores").addEventListener("click", (e) => {
  const b = e.target.closest("[data-color]");
  if (!b) return;
  estado.colorCuenta = b.dataset.color;
  pintarColores();
});
$("#btn-nueva-cuenta").addEventListener("click", abrirNuevaCuenta);

$("#form-cuenta").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/cuentas", {
      method: "POST",
      body: JSON.stringify({
        nombre: $("#cta-nombre").value.trim(),
        tipo: $("#cta-tipo").value,
        color: estado.colorCuenta,
        saldo_inicial: $("#cta-saldo").value || 0,
      }),
    });
    cerrar($("#modal-cuenta"));
    toast("👛 Cuenta creada");
    cargarInicio();
  } catch (err) {
    $("#cta-error").textContent = err.message;
  }
});

// ----- Presupuesto
let presuCategoria = null;
$("#lista-presu").addEventListener("click", (e) => {
  const li = e.target.closest("[data-presu]");
  if (!li) return;
  presuCategoria = li.dataset.presu;
  $("#presu-titulo").textContent = `Presupuesto: ${li.dataset.nombre}`;
  $("#presu-monto").value = li.dataset.monto || "";
  abrir("#modal-presu");
  setTimeout(() => $("#presu-monto").focus(), 300);
});
$("#form-presu").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api(`/presupuestos/${presuCategoria}`, {
      method: "PUT",
      body: JSON.stringify({ monto: $("#presu-monto").value || 0 }),
    });
    cerrar($("#modal-presu"));
    toast("🎯 Presupuesto guardado");
    cargarPresupuestos();
  } catch (err) {
    toast("⚠️ " + err.message);
  }
});

// ----- Borrar movimiento / cuenta
document.addEventListener("click", (e) => {
  const bm = e.target.closest("[data-borrar-mov]");
  if (bm) {
    confirmar("¿Eliminar movimiento?", "Esta acción no se puede deshacer.", async () => {
      try {
        await api(`/movimientos/${bm.dataset.borrarMov}`, { method: "DELETE" });
        toast("🗑️ Movimiento eliminado");
        refrescarVistaActual();
      } catch (err) { toast("⚠️ " + err.message); }
    });
  }
  const bc = e.target.closest("[data-borrar-cuenta]");
  if (bc) {
    confirmar(`¿Eliminar “${bc.dataset.nombre}”?`, "Se borrarán también todos los movimientos de esta cuenta.", async () => {
      try {
        await api(`/cuentas/${bc.dataset.borrarCuenta}`, { method: "DELETE" });
        toast("🗑️ Cuenta eliminada");
        cargarInicio();
      } catch (err) { toast("⚠️ " + err.message); }
    });
  }
});

function refrescarVistaActual() {
  const activa = $(".vista.activa").id.replace("vista-", "");
  ir(activa);
}

// ---------------------------------------------------------------- Ocultar montos
function aplicarOculto(oculto) {
  document.body.classList.toggle("oculto", oculto);
  $("#btn-ocultar").textContent = oculto ? "🙈" : "👁️";
}
$("#btn-ocultar").addEventListener("click", () => {
  const oculto = !document.body.classList.contains("oculto");
  aplicarOculto(oculto);
  try { localStorage.setItem("billetera-oculto", oculto ? "1" : ""); } catch {}
});

// ---------------------------------------------------------------- Inicio de la app
(async function iniciar() {
  const hora = new Date().getHours();
  $("#saludo").textContent = hora < 12 ? "Buenos días ☀️" : hora < 19 ? "Buenas tardes 🌤️" : "Buenas noches 🌙";
  $("#etiqueta-mes").textContent = new Date().toLocaleDateString("es-BO", { month: "long", year: "numeric" });
  try { aplicarOculto(localStorage.getItem("billetera-oculto") === "1"); } catch {}

  try {
    const cfg = await api("/config");
    estado.grafana = cfg.grafana_url;
    $("#link-grafana").href = `${estado.grafana}/d/billetera/billetera`;
    estado.categorias = await api("/categorias");
  } catch (e) {
    toast("⚠️ No se pudo conectar con el servidor");
  }
  cargarInicio();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
})();
