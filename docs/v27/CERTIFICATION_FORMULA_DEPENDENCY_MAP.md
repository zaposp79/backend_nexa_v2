# Formula Dependency Map — Workbook V2-7

## Economic calculation chain

```
INPUTS (user config)
  Panel de Control General
    ├── Servicio (C5), Márgenes (C63/D63/E63)
    ├── ICA (C34=0.01), GMF (C35=0.004)
    ├── Pólizas config (C38:C55)
    ├── Escenarios comerciales (A81:D113)
    └── Ramp-up by service (→ Rot, Ausent y Rentabilidad!B38:B43)

LAYER 1 — Cost computation
  Nomina Loaded
    ├── salario_fijo, comisiones, cap_inicial, crucero (per profile per month)
    └── aggregated by canal (rows 93-113)
  No payroll
    ├── opex_ti, capex, costos_fijos (per profile per month)
    └── aggregated by canal (rows 107-124)
  Costo Variable
    └── tarifa_canal, escalamiento, HITL (Cadena B/C)
  Costo Cadena C
    └── tarifa_proveedor, integración, equipo_integ
  Costos Totales
    └── aggregation of all cost layers
  Pólizas - Costo Financiacion
    ├── ICA (rows 12-83): gross-up on costs
    ├── GMF (rows 86-163): direct on cash flows
    ├── Pólizas per_canal (rows 173-185)
    └── Financiación (row 310+)

LAYER 2 — Vision computation
  Visión P&G
    ├── Ingresos: (costo / (1-margen)) × rampup
    ├── Costos: Nomina + NoPayroll + CadenaB + CadenaC
    ├── Comp. Financiero: ICA + GMF + Pólizas + Financiación + ComAdm
    └── Contribución: Ingreso Neto - Costo Total
    [does NOT reference Vision Tarifas — 0 references confirmed]
  Vision Tarifas_Modelo_Cobro
    ├── Costs (C40/C50/C60): same sources as P&G
    ├── Ingresos (C47/C57/C67): costo/factor
    ├── C72 (Facturación Total): C47+C57+C67
    └── Rows 75-85 (billing schedule): DISPLAY_ONLY
  Vision Cost To Serve
    ├── K50/L50/M50 denominators (from Panel + perfiles)
    ├── CTS_A = (payroll+nopayroll)/K50
    ├── CTS_B = costo_b/L50
    ├── CTS_C = costo_c/M50
    ├── B19 = VT!C72 (ingreso display) ← certified
    └── H19 = VT!C40+C50+C60 (costo display) ← certified

LAYER 3 — KPI
  KPIs (from P&G + CTS)
    ├── ingreso_mensual (from engine.py via VT!C72)
    ├── costo_mensual_promedio
    └── facturacion_mensual_proyectada
```

## Isolation proof for DISPLAY_ONLY elements

```
Panel!C182 → VT!C77 → [dead end: 0 consumers]
                        ↗
VT!C72 = C47+C57+C67   (does NOT use C77)
P&G    = Nomina+NoPayroll+CostoVariable+CadenaC (does NOT reference VT)
```

Verified by exhaustive scan of all formula strings across all 23 workbook sheets.
