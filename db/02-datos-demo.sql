-- =========================================================
--  Datos de ejemplo (últimos 6 meses) para ver los gráficos.
--  Si NO quieres datos de ejemplo, borra este archivo antes
--  de levantar el sistema por primera vez.
-- =========================================================

INSERT INTO cuentas (nombre, tipo, color, saldo_inicial) VALUES
    ('Efectivo',        'efectivo', '#00f5a0', 500),
    ('Banco',           'banco',    '#00d9f5', 3000),
    ('Ahorros',         'ahorro',   '#a855f7', 2000);

-- Sueldo cada mes (día 1) en el banco
INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
SELECT 2, (SELECT id FROM categorias WHERE nombre = 'Sueldo'), 'ingreso', 6500, 'Sueldo mensual', d::date
FROM generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '5 months',
                     date_trunc('month', CURRENT_DATE), INTERVAL '1 month') AS d;

-- Alquiler cada mes (día 5)
INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
SELECT 2, (SELECT id FROM categorias WHERE nombre = 'Vivienda'), 'gasto', 1800, 'Alquiler', (d + INTERVAL '4 days')::date
FROM generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '5 months',
                     date_trunc('month', CURRENT_DATE), INTERVAL '1 month') AS d
WHERE (d + INTERVAL '4 days')::date <= CURRENT_DATE;

-- Servicios cada mes (día 10)
INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
SELECT 2, (SELECT id FROM categorias WHERE nombre = 'Servicios'), 'gasto', round((250 + random() * 120)::numeric, 2),
       'Luz, agua e internet', (d + INTERVAL '9 days')::date
FROM generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '5 months',
                     date_trunc('month', CURRENT_DATE), INTERVAL '1 month') AS d
WHERE (d + INTERVAL '9 days')::date <= CURRENT_DATE;

-- Gastos variables: cada categoría tiene una probabilidad diaria,
-- un monto mínimo, un rango y descripciones posibles.
INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
SELECT
    CASE WHEN random() < 0.3 THEN 1 ELSE 2 END,   -- 30% en efectivo, 70% banco
    c.id,
    'gasto',
    round((r.minimo + random() * r.rango)::numeric, 2),
    r.textos[1 + floor(random() * array_length(r.textos, 1))::int],
    d::date
FROM (
  -- OFFSET 0 obliga a sortear un número aleatorio por cada día y categoría
  SELECT d, r.*, random() AS azar
  FROM generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '5 months', CURRENT_DATE, INTERVAL '1 day') AS d
  CROSS JOIN (VALUES
    ('Comida',          0.90, 20,  60,  ARRAY['Almuerzo', 'Supermercado', 'Cena', 'Salteñas', 'Café']),
    ('Comida',          0.35, 40,  120, ARRAY['Supermercado', 'Mercado', 'Pedido a domicilio']),
    ('Transporte',      0.75, 3,   22,  ARRAY['Micro', 'Taxi', 'Gasolina', 'Trufi']),
    ('Entretenimiento', 0.10, 30,  120, ARRAY['Cine', 'Salida con amigos', 'Streaming', 'Videojuego']),
    ('Ropa',            0.03, 80,  250, ARRAY['Compra de ropa', 'Zapatos']),
    ('Salud',           0.04, 40,  150, ARRAY['Farmacia', 'Consulta médica']),
    ('Educación',       0.05, 30,  200, ARRAY['Libros', 'Curso online', 'Fotocopias']),
    ('Otros gastos',    0.05, 10,  80,  ARRAY['Varios', 'Regalo', 'Ferretería'])
  ) AS r(nombre, prob, minimo, rango, textos)
  OFFSET 0
) r
JOIN categorias c ON c.nombre = r.nombre AND c.tipo = 'gasto'
WHERE r.azar < r.prob;

-- Ingresos extra ocasionales (freelance)
INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
SELECT 1, (SELECT id FROM categorias WHERE nombre = 'Freelance'), 'ingreso',
       round((400 + random() * 900)::numeric, 2), 'Proyecto freelance', d::date
FROM generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '5 months', CURRENT_DATE, INTERVAL '1 day') AS d
WHERE random() < 0.03;

-- Ventas mensuales en efectivo
INSERT INTO movimientos (cuenta_id, categoria_id, tipo, monto, descripcion, fecha)
SELECT 1, (SELECT id FROM categorias WHERE nombre = 'Ventas'), 'ingreso',
       round((600 + random() * 500)::numeric, 2), 'Venta de productos', (d + INTERVAL '14 days')::date
FROM generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '5 months',
                     date_trunc('month', CURRENT_DATE), INTERVAL '1 month') AS d
WHERE (d + INTERVAL '14 days')::date <= CURRENT_DATE;

-- Presupuestos mensuales
INSERT INTO presupuestos (categoria_id, monto)
SELECT id, CASE nombre
    WHEN 'Comida'          THEN 1500
    WHEN 'Transporte'      THEN 400
    WHEN 'Vivienda'        THEN 1800
    WHEN 'Servicios'       THEN 400
    WHEN 'Entretenimiento' THEN 500
    WHEN 'Ropa'            THEN 300
END
FROM categorias
WHERE nombre IN ('Comida', 'Transporte', 'Vivienda', 'Servicios', 'Entretenimiento', 'Ropa');
