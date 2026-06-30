# Visión P&G — Ingeniería Inversa Excel V2-7

## Estructura Excel (hoja "Visión P&G", A1:CO80)

### Mapa de filas por sección

| Fila | Label Excel | Tipo | Backend key | Status |
|------|-------------|------|-------------|--------|
| 17 | Ingresos | sección | — | visual only |
| 18 | Ingreso Bruto | subtotal | `ingreso_bruto` | ✓ |
| 19 | Ingreso Cadena A | linea | `ingreso_bruto_a` | ✓ |
| 20 | Ingreso Cadena B | linea | `ingreso_bruto_b` | ✓ |
| 21 | Ingreso Cadena C | linea | `ingreso_bruto_c` | ✓ |
| 22 | Contingencia Operativa | linea | `contingencia_op` | ✓ |
| 23 | Contingencia Comercial | linea | `contingencia_com` | ✓ |
| 24 | Mark-Up | linea | `markup_ingreso` | ✓ |
| 25 | Descuento | linea (-) | `descuento_ingreso` | ✓ |
| 26 | Imprevistos | linea (-) | `imprevistos_ingreso` | ✓ |
| 27 | Ingreso Neto | **total** | `ingreso_neto` | ✓ |
| 29 | Costos | sección | — | visual only |
| 30 | Costo Total | total | `costo_total` | ✓ |
| 31 | Costos Cadena A | subtotal | `costo_a` | ✓ |
| 32 | Payroll | subtotal | `payroll_a` | ✓ (aggregate) |
| 33 | Nomina Loaded | subtotal | — | **GAP-PYG-HIER-1** |
| 34 | Salario Fijo | linea | — | **GAP-PYG-HIER-1** |
| 35 | Salario Variable (Comisiones) | linea | — | **GAP-PYG-HIER-1** |
| 36 | Capacitación Inicial | linea | — | **GAP-PYG-HIER-1** |
| 37 | Capacitación Rotación | linea | — | **GAP-PYG-HIER-1** |
| 38 | Exámenes Médicos | linea | — | **GAP-PYG-HIER-1** |
| 39 | Estudios de Seguridad | linea | — | **GAP-PYG-HIER-1** |
| 40 | Crucero | linea | — | **GAP-PYG-HIER-1** |
| 41 | No Payroll | subtotal | `no_payroll_a` | ✓ (aggregate) |
| 42 | OPEX Fijo | linea | — | **GAP-PYG-HIER-1** |
| 43 | Inversiones | linea | — | **GAP-PYG-HIER-1** |
| 44 | Costos Fijos | linea | — | **GAP-PYG-HIER-1** |
| 45 | Costos Cadena B | subtotal | `costo_b` | ✓ (aggregate) |
| 46 | Componente Fijo | subtotal | — | **GAP-PYG-HIER-2** |
| 47 | OPEX Fijo | linea | — | **GAP-PYG-HIER-2** |
| 48 | Inversiones | linea | — | **GAP-PYG-HIER-2** |
| 49 | S&M | linea | — | **GAP-PYG-HIER-2** |
| 50 | Componente Variable | subtotal | — | **GAP-PYG-HIER-2** |
| 51 | Tarifa Canal | linea | — | **GAP-PYG-HIER-2** |
| 52 | OPEX Variable | linea | — | **GAP-PYG-HIER-2** |
| 53 | Tasa de Escalamiento | linea | — | **GAP-PYG-HIER-2** |
| 54 | HITL | linea | — | **GAP-PYG-HIER-2** |
| 55 | Costos Cadena C | subtotal | `costo_c` | ✓ (aggregate) |
| 56 | Tarifa Proveedor | linea | — | **GAP-PYG-HIER-3** |
| 57 | Costo Integración | subtotal | — | **GAP-PYG-HIER-3** |
| 58-60 | OPEX Fijo / Inversiones / Equipo | linea | — | **GAP-PYG-HIER-3** |
| 61 | Costo Variable | subtotal | — | **GAP-PYG-HIER-3** |
| 62-64 | Tasa Escalamiento / OPEX Variable / HITL | linea | — | **GAP-PYG-HIER-3** |
| 65 | Componente Financiero | subtotal | `costos_financieros` | ✓ |
| 66 | ICA | linea | `ica` | ✓ |
| 67 | GMF | linea | `gmf` | ✓ |
| 68 | Comisión de Administración | linea | `comision_administracion` | ✓ |
| 69 | Pólizas adicionales | linea | `polizas` | ✓ |
| 70 | Costos Financieros | linea | `financiacion` | ✓ (label fix) |
| 73 | Utilidad | sección | — | visual only |
| 74 | Contribución | total | `contribucion` | ✓ |
| 75 | Contribución por Puesto | linea | — | **GAP-PYG-HIER-4** |
| 76 | % Contribución | porcentaje | `pct_contribucion` | ✓ |
| 78 | Costo Fijo | linea (= 0) | `costo_fijo` | ✓ (hardcoded 0) |
| 79 | Utilidad Neta | total | `utilidad_neta` | ✓ |
| 80 | % Utilidad Neta | porcentaje | `pct_utilidad_neta` | ✓ |

## Jerarquía funcional

```
Ingresos
 ├── Ingreso Bruto (subtotal)
 │    ├── Ingreso Cadena A
 │    ├── Ingreso Cadena B
 │    └── Ingreso Cadena C
 ├── Ajustes (Contingencias + Markup - Descuento - Imprevistos)
 └── Ingreso Neto (total)

Costos
 ├── Costo Total (total = A+B+C)
 │    ├── Costos Cadena A (subtotal)
 │    │    ├── Payroll (subtotal) → aggregate en backend; sub-componentes: GAP-PYG-HIER-1
 │    │    └── No Payroll (subtotal) → aggregate en backend; sub-componentes: GAP-PYG-HIER-1
 │    ├── Costos Cadena B (subtotal) → aggregate; sub-componentes: GAP-PYG-HIER-2
 │    └── Costos Cadena C (subtotal) → aggregate; sub-componentes: GAP-PYG-HIER-3
 └── Componente Financiero (subtotal)
      ├── ICA
      ├── GMF
      ├── Comisión de Administración
      ├── Pólizas adicionales
      └── Costos Financieros (= Financiación)

Utilidad
 ├── Contribución (= Ingreso Neto - Costo Total - Comp.Financiero)
 ├── Contribución por Puesto → GAP-PYG-HIER-4
 ├── % Contribución
 ├── Costo Fijo (= 0, hardcoded)
 ├── Utilidad Neta
 └── % Utilidad Neta
```

## Fórmulas clave

| Celda | Fórmula |
|-------|---------|
| C18 (Ingreso Bruto) | `=C19+C20+C21` |
| C19 (Ingreso A) | `=IFERROR((C31/(1-Panel!C63))*C15, 0)` |
| C27 (Ingreso Neto) | `=C18+SUM(C22:C24)-C25-C26` |
| C30 (Costo Total) | `=C31+C45+C55` |
| C65 (Comp. Financiero) | `=SUM(C66:C70)` |
| C74 (Contribución) | `=C27-C30` |
| C79 (Utilidad Neta) | `=C27-C30-C78` (C78=0) |

## Reglas de activación

- **IFERROR en ingresos**: Si margen=1.0 (cadena inactiva) → muestra 0, no error.
- **Ramp-up (C15)**: Multiplica todos los ingresos. Si rampup=0 → ingresos=0 ese mes.
- **Imprevistos (C26)**: `Panel!C73 × ingreso_bruto`. Solo resta si Panel!C73 > 0.
- **Costo Fijo (C78)**: Siempre 0 en V2-7 (hardcoded en Excel).

## Gaps identificados (Fase 2 — estado de cierre)

| ID | Descripción | Estado | Resolución |
|----|-------------|--------|-----------|
| GAP-PYG-HIER-1 | Sub-componentes Payroll/No Payroll (Cadena A), Excel filas 34-44 | **CERRADO** | `VisionPyGBuilder` recibe `calc_nomina`/`calc_no_payroll`; emite `filas_detalle` por mes (parent=`payroll_a`/`no_payroll_a`). Suma exacta al parent verificada. |
| GAP-PYG-HIER-2 | Sub-componentes Cadena B, Excel filas 46-54 | **PARCIAL** | 6 sub-componentes cerrados (OPEX Fijo, Inversiones, S&M, Tarifa Canal, Tasa Escalamiento, HITL). **"OPEX Variable" (fila 52) = UNDETERMINED**: `ResultadoCadenaB` no modela ese campo; no se fabrica fila. |
| GAP-PYG-HIER-3 | Sub-componentes Cadena C, Excel filas 56-64 | **CERRADO** | `calc_cadena_c` añadido al dict de calculadores; 7 sub-componentes desde `ResultadoCadenaC`. Caveat: el summary `costo_c` usa `total_pyg` (excluye hitl/equipo/opex_var → van a `costo_c_fin`); en el fixture real esos son 0 y suma == parent. |
| GAP-PYG-HIER-4 | "Contribución por Puesto" (fila 75 = C74/C14) | **CERRADO** | `estaciones = Σ(fte × pct_presencia)` (no-soporte). Validado: backend=24.0 == workbook C14=24. Calculado en builder, NO se añade campo a PyGMensual (preserva contrato certificado). |
| LABEL-FIN-01 | `financiacion` → "Costos Financieros" (fila 70) | CERRADO (Fase 1) | Corregido en _ROW_DEFINITIONS |
| LABEL-TOTAL-01 | `costo_total` → "Costo Total" | CERRADO (Fase 1) | Corregido |
| EXTRA-ROW-01 | `polizas_a/b/c` sin equivalente Excel | CERRADO (Fase 1) | Eliminadas de _ROW_DEFINITIONS |
