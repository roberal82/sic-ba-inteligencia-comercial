-- SIC-BA Database v1.0
-- PostgreSQL schema for Sistema de Inteligencia Comercial Blanco & Asociados

CREATE SCHEMA IF NOT EXISTS sic_ba;
SET search_path TO sic_ba;

CREATE TABLE IF NOT EXISTS dim_clientes (
    id_cliente SERIAL PRIMARY KEY,
    codigo VARCHAR(30),
    cliente VARCHAR(200) NOT NULL,
    ruc VARCHAR(30),
    ciudad VARCHAR(100),
    telefono VARCHAR(100),
    email VARCHAR(150),
    vendedor VARCHAR(100),
    linea_credito NUMERIC(18,2) DEFAULT 0,
    fecha_alta DATE,
    estado VARCHAR(30) DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_proveedores (
    id_proveedor SERIAL PRIMARY KEY,
    proveedor VARCHAR(200) NOT NULL,
    ruc VARCHAR(30),
    telefono VARCHAR(100),
    email VARCHAR(150),
    linea_credito NUMERIC(18,2) DEFAULT 0,
    estado VARCHAR(30) DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_productos (
    id_producto SERIAL PRIMARY KEY,
    codigo VARCHAR(50),
    producto VARCHAR(300) NOT NULL,
    categoria VARCHAR(100),
    unidad VARCHAR(30),
    costo_referencia NUMERIC(18,2) DEFAULT 0,
    precio_referencia NUMERIC(18,2) DEFAULT 0,
    estado VARCHAR(30) DEFAULT 'ACTIVO'
);

CREATE TABLE IF NOT EXISTS fact_cobros (
    id_cobro SERIAL PRIMARY KEY,
    id_cliente INTEGER REFERENCES dim_clientes(id_cliente),
    cliente_texto VARCHAR(200),
    factura VARCHAR(60),
    fecha_factura DATE,
    vencimiento DATE,
    moneda VARCHAR(10) DEFAULT 'PYG',
    monto NUMERIC(18,2) DEFAULT 0,
    cobrado NUMERIC(18,2) DEFAULT 0,
    saldo NUMERIC(18,2) DEFAULT 0,
    estado VARCHAR(30),
    fuente VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_pagos (
    id_pago SERIAL PRIMARY KEY,
    id_proveedor INTEGER REFERENCES dim_proveedores(id_proveedor),
    proveedor_texto VARCHAR(200),
    factura VARCHAR(60),
    fecha DATE,
    vencimiento DATE,
    moneda VARCHAR(10) DEFAULT 'PYG',
    total_factura NUMERIC(18,2) DEFAULT 0,
    saldo NUMERIC(18,2) DEFAULT 0,
    estado VARCHAR(30),
    fuente VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_cheques (
    id_cheque SERIAL PRIMARY KEY,
    numero VARCHAR(50),
    banco VARCHAR(100),
    beneficiario VARCHAR(200),
    fecha_emision DATE,
    fecha_vencimiento DATE,
    monto NUMERIC(18,2) DEFAULT 0,
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    observacion TEXT,
    fuente VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_ventas (
    id_venta SERIAL PRIMARY KEY,
    fecha DATE,
    id_cliente INTEGER REFERENCES dim_clientes(id_cliente),
    cliente_texto VARCHAR(200),
    factura VARCHAR(60),
    id_producto INTEGER REFERENCES dim_productos(id_producto),
    producto_texto VARCHAR(300),
    cantidad NUMERIC(18,2) DEFAULT 0,
    costo NUMERIC(18,2) DEFAULT 0,
    venta NUMERIC(18,2) DEFAULT 0,
    utilidad NUMERIC(18,2) DEFAULT 0,
    margen NUMERIC(10,2) DEFAULT 0,
    fuente VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_cotizaciones (
    id_cotizacion SERIAL PRIMARY KEY,
    numero VARCHAR(60),
    fecha DATE,
    id_cliente INTEGER REFERENCES dim_clientes(id_cliente),
    cliente_texto VARCHAR(200),
    vendedor VARCHAR(100),
    estado VARCHAR(40),
    total NUMERIC(18,2) DEFAULT 0,
    costo NUMERIC(18,2) DEFAULT 0,
    utilidad NUMERIC(18,2) DEFAULT 0,
    margen NUMERIC(10,2) DEFAULT 0,
    fuente VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS score_clientes (
    id_score SERIAL PRIMARY KEY,
    id_cliente INTEGER REFERENCES dim_clientes(id_cliente),
    fecha_calculo DATE DEFAULT CURRENT_DATE,
    score_total NUMERIC(5,2),
    score_volumen NUMERIC(5,2),
    score_frecuencia NUMERIC(5,2),
    score_pago NUMERIC(5,2),
    score_antiguedad NUMERIC(5,2),
    score_margen NUMERIC(5,2),
    clasificacion VARCHAR(60),
    recomendacion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW vw_resumen_financiero AS
SELECT
    COALESCE((SELECT SUM(saldo) FROM fact_cobros), 0) AS total_cobrar,
    COALESCE((SELECT SUM(saldo) FROM fact_pagos), 0) AS total_pagar,
    COALESCE((SELECT SUM(monto) FROM fact_cheques WHERE estado = 'PENDIENTE'), 0) AS cheques_pendientes;

CREATE OR REPLACE VIEW vw_top_clientes_deudores AS
SELECT
    COALESCE(c.cliente, fc.cliente_texto) AS cliente,
    SUM(fc.saldo) AS saldo_total
FROM fact_cobros fc
LEFT JOIN dim_clientes c ON c.id_cliente = fc.id_cliente
GROUP BY COALESCE(c.cliente, fc.cliente_texto)
ORDER BY saldo_total DESC;
