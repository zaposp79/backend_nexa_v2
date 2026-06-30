# Baseline Regeneration — Variable Comp Load V2-8

**Commit trigger:** 5a72f81 (fix(v28): apply prestational load to variable compensation)
**Fecha:** 2026-06-11
**Decision:** VARIABLE_COMP_LOAD_DECISION = APPLY_PRESTATIONAL_LOAD_LIKE_EXCEL

## Contexto

`NominaCargadaService.calcular` (nomina_cargada.py:117): imponible base cambiado de
`salario_base × (1 + comision_pct × pct_cumplimiento_variable[0.7])` a
`salario_base × (1 + comision_pct)`.

El factor `pct_cumplimiento_variable` (0.70) se aplica aguas abajo en
`NominaCalculator._comisiones`, no antes de cargar. Esto alinea con Excel V2-8
`Inputs de Nomina!F62 = 2,350,905` (comisión COMPLETA sin reducción 0.7 en base).

## Snapshots actualizados

| Escenario | Campo | Valor anterior | Valor nuevo | Delta | Causa | Aprobado |
|-----------|-------|----------------|-------------|-------|-------|----------|
| bancamia_whatsapp_only | kpis.ingreso_mensual | 49,876,041.80 | 50,646,202.91 | +770,161.11 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_whatsapp_only | kpis.costo_total_contrato | 4,786,075,277.00 | 4,793,396,843.67 | +7,321,566.67 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_whatsapp_only | kpis.utilidad_neta_total | 2,415,014,835.97 | 2,416,769,037.70 | +1,754,201.73 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_whatsapp_only | kpis.pct_utilidad_neta_total | 0.33536795 | 0.33518910 | -0.00017885 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_whatsapp_only | pyg_por_mes[0].payroll_a | 28,283,260.07 | 28,893,390.62 | +610,130.55 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_excel_match | kpis.ingreso_mensual | 412,964,719.57 | 416,945,544.82 | +3,980,825.25 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_excel_match | kpis.costo_total_contrato | 8,143,741,146.37 | 8,181,585,017.08 | +37,843,870.71 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_excel_match | kpis.utilidad_neta_total | 3,191,826,730.94 | 3,200,893,886.40 | +9,067,155.46 | VARIABLE_COMP_LOAD | ✅ |
| bancamia_excel_match | pyg_por_mes[0].payroll_a | 104,406,043.83 | 107,559,699.72 | +3,153,655.89 | VARIABLE_COMP_LOAD | ✅ |

## Campos NO modificados (kill-switch control)

| Campo | Comportamiento |
|-------|---------------|
| no_payroll_a | Sin cambio — CAPEX/NoPayroll no afectado |
| costo_b | Sin cambio — Cadena B no afectada |
| costo_c | Sin cambio — Cadena C no afectada |
| storage/parametrization | Sin cambio — parametrización intacta |
| modules/ | Sin cambio — solo nomina_cargada.py en commit 5a72f81 |

## Anti-hardcode audit

Búsqueda de valores hardcoded en módulos productivos (600000, 1.5699, 0.7×comision):
- Resultado: 0 hardcodes nuevos encontrados
- `pct_cumplimiento_variable` leído desde storage parametrización, no hardcodeado

## Estado post-regeneración

- `make all`: PASS
- `make validate-excel-v28`: PASS (6/6, 1 skip)
- `test_cts_001_v28.py`: 2/2 PASS
- `test_nomina_variable_load_v28.py`: 2/2 PASS
- CTS-001 delta: -232.07 COP/tx (3.73%) — PARTIAL (Bug 1 residual + examenes/crucero)
- BASELINE_REGENERATED_FOR_VARIABLE_COMP_LOAD: DONE
- HR_PARAM_FACTOR_PRESTACIONAL: NEXT

## Causa residual 3.73%

| Componente | Delta COP/tx | Causa |
|------------|-------------|-------|
| salario_variable | +281.60 | Bug 1: variable line not multiplied by carga factor 1.5699 (CTS cosmético, no cambia TOTAL) |
| examenes | +12.23 | backend examenes ~0 vs Excel |
| crucero | +10.63 | backend crucero = 0 vs Excel |
| opex_fijo + inversiones | -71.95 + -16.72 | No-Payroll over-allocation offset |

Cerrar Bug 1 requiere `HR_PARAM_FACTOR_PRESTACIONAL` — siguiente fase.
