-- =========================================================
--  Billetera personal - Esquema de base de datos
-- =========================================================

CREATE TABLE cuentas (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(60)    NOT NULL,
    tipo          VARCHAR(20)    NOT NULL DEFAULT 'efectivo',   -- efectivo | banco | tarjeta | ahorro
    color         VARCHAR(9)     NOT NULL DEFAULT '#00d9f5',
    saldo_inicial NUMERIC(14, 2) NOT NULL DEFAULT 0,
    creado        TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE TABLE categorias (
    id      SERIAL PRIMARY KEY,
    nombre  VARCHAR(40) NOT NULL,
    tipo    VARCHAR(10) NOT NULL CHECK (tipo IN ('ingreso', 'gasto')),
    icono   VARCHAR(8)  NOT NULL DEFAULT '💸',
    color   VARCHAR(9)  NOT NULL DEFAULT '#a855f7',
    UNIQUE (nombre, tipo)
);

CREATE TABLE movimientos (
    id           SERIAL PRIMARY KEY,
    cuenta_id    INT            NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
    categoria_id INT            NOT NULL REFERENCES categorias(id),
    tipo         VARCHAR(10)    NOT NULL CHECK (tipo IN ('ingreso', 'gasto')),
    monto        NUMERIC(14, 2) NOT NULL CHECK (monto > 0),
    descripcion  VARCHAR(120)   NOT NULL DEFAULT '',
    fecha        DATE           NOT NULL DEFAULT CURRENT_DATE,
    creado       TIMESTAMPTZ    NOT NULL DEFAULT now()
);
CREATE INDEX idx_movimientos_fecha ON movimientos (fecha);

-- Presupuesto mensual por categoría de gasto
CREATE TABLE presupuestos (
    categoria_id INT PRIMARY KEY REFERENCES categorias(id) ON DELETE CASCADE,
    monto        NUMERIC(14, 2) NOT NULL CHECK (monto > 0)
);

-- Categorías por defecto
INSERT INTO categorias (nombre, tipo, icono, color) VALUES
    ('Sueldo',          'ingreso', '💼', '#00f5a0'),
    ('Ventas',          'ingreso', '🛒', '#00d9f5'),
    ('Freelance',       'ingreso', '💻', '#38bdf8'),
    ('Otros ingresos',  'ingreso', '✨', '#a3e635'),
    ('Comida',          'gasto',   '🍔', '#ff5ea8'),
    ('Transporte',      'gasto',   '🚌', '#f59e0b'),
    ('Vivienda',        'gasto',   '🏠', '#a855f7'),
    ('Servicios',       'gasto',   '💡', '#facc15'),
    ('Salud',           'gasto',   '💊', '#ef4444'),
    ('Educación',       'gasto',   '📚', '#6366f1'),
    ('Entretenimiento', 'gasto',   '🎮', '#ec4899'),
    ('Ropa',            'gasto',   '👕', '#14b8a6'),
    ('Otros gastos',    'gasto',   '📦', '#94a3b8');

-- Usuario de solo lectura para Grafana (no puede modificar datos)
CREATE USER grafana_lector WITH PASSWORD 'grafana_lector';
GRANT CONNECT ON DATABASE billetera TO grafana_lector;
GRANT USAGE ON SCHEMA public TO grafana_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_lector;
