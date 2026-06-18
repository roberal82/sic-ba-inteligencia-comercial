-- SIC-BA PostgreSQL schema

CREATE TABLE dim_clientes (
  id SERIAL PRIMARY KEY,
  cliente TEXT UNIQUE,
  ruc TEXT,
  ciudad TEXT,
  estado TEXT
);

CREATE TABLE dim_proveedores (
  id SERIAL PRIMARY KEY,
  proveedor TEXT UNIQUE,
  ruc TEXT,
  estado TEXT
);

CREATE TABLE fact_ventas (
  id SERIAL PRIMARY KEY,
  fuente TEXT,
  factura TEXT,
  fecha DATE,
  cliente TEXT,
  total_gs NUMERIC,
  total_usd NUMERIC
);

CREATE TABLE fact_cobros (
  id SERIAL PRIMARY KEY,
  fuente TEXT,
  cliente TEXT,
  comprobante TEXT,
  fecha DATE,
  vencimiento DATE,
  moneda TEXT,
  total NUMERIC,
  saldo NUMERIC
);

CREATE TABLE fact_pagos (
  id SERIAL PRIMARY KEY,
  fuente TEXT,
  proveedor TEXT,
  numero TEXT,
  fecha DATE,
  vencimiento DATE,
  moneda TEXT,
  total_factura NUMERIC,
  saldo NUMERIC
);

CREATE TABLE fact_compras (
  id SERIAL PRIMARY KEY,
  fuente TEXT,
  proveedor TEXT,
  fecha DATE,
  factura TEXT,
  moneda TEXT,
  producto TEXT,
  cantidad NUMERIC,
  total NUMERIC
);
