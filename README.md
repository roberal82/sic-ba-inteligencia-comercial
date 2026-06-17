# SIC-BA - Sistema de Inteligencia Comercial

Proyecto de Inteligencia Comercial para Blanco & Asociados.

## Objetivo

Transformar los reportes PDF generados por el ERP Valurq en información estratégica para la toma de decisiones.

El ERP seguirá siendo el sistema transaccional y contable.
El SIC-BA será el centro de comando gerencial.

## Arquitectura

```text
ERP Valurq
    ↓
Reportes PDF
    ↓
Google Drive
    ↓
Extractor Python
    ↓
Base Maestra SIC-BA
    ↓
Dashboard Ejecutivo
    ↓
IA Gerencial
```

## Módulos

### Financiero
- Cuentas por cobrar
- Cuentas por pagar
- Cheques diferidos
- Flujo de caja

### Comercial
- Ventas
- Clientes
- Cotizaciones
- Booking

### Operaciones
- Vehículos
- Combustible
- Gastos

### Inteligencia Artificial
- Alertas automáticas
- Score de clientes
- Riesgo financiero
- Predicción de flujo de caja

## Estructura del repositorio

```text
sic-ba-inteligencia-comercial/
├── src/
├── docs/
├── data_raw/
├── data_clean/
├── dashboard/
└── ia/
```

## Estado del Proyecto

Fase actual:
- Arquitectura definida
- Base maestra en construcción
- Extractor PDF Valurq v1.0 implementado
- Dashboard Presidencia en diseño

## Roadmap

### Sprint 1
- Base Maestra
- Extractor PDF
- Dashboard Financiero

### Sprint 2
- Dashboard Comercial
- Score de Clientes
- Flujo de Caja 30/60/90 días

### Sprint 3
- IA Gerencial
- Automatización completa
- Reporte Ejecutivo Diario

## Autor

Robert Benítez
Blanco & Asociados - Soluciones Integrales