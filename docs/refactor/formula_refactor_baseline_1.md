# Formula Refactor Baseline 1 (Post-D1-Fix)

Branch: `refactor/modular-pure`. Fecha: 2026-06-06.
Precede a: Baseline 0 (formula_refactor_baseline_0.md, con costo_b=0 por bug D-1).

## 1. Cambio respecto a Baseline 0

Bug D-1 corregido: Cadena B ahora fluye correctamente al resultado.

- **Fix**: `user_input_loader.py` `_normalizar_entry_data_format` — agregado unwrap guard
  para `condiciones_cadena_b` (análogo al guard ya existente para `condiciones_cadena_a`).
- **Causa original**: request.json enviaba `condiciones_cadena_b.condiciones_cadena_b.{opex,...}`
  (doble anidamiento). El loader pasaba el nivel externo `{"condiciones_cadena_b":{...}}` al
  adapter, que no encontraba claves entry_data → no transformaba → cadena_b vacía.

## 2. Comparación: Baseline 0 vs Baseline 1

| Métrica | Baseline 0 (buggy) | Baseline 1 (fixed) | Delta |
|---------|-------------------|--------------------|-------|
| costo_b mes1 | 0 | 39.503.127,41 | +39.503.127 |
| costo_b mes24 | 0 | 40.869.971,41 | +40.869.971 |
| total costo_b contrato | 0 | 964.477.185,84 | +964.477.186 |
| ingreso_mensual (KPI) | 260.842.533,88 | 260.842.533,88 | 0 (cadena A unchanged) |
| costo_cadena_a_promedio | 185.297.653,44 | 185.297.653,44 | 0 |
| costo_total_contrato | 4.447.143.682,59 | 5.411.620.868,43 | +964.477.186 |
| utilidad_neta_total | 1.659.262.761,34 | 2.247.734.158,93 | +588.471.398 |
| pct_utilidad_neta_total | 27,17% | 29,35% | +2,18 pp |
| payroll_a mes1 | 154.103.322,32 | 154.103.322,32 | 0 |
| no_payroll_a mes1 | 61.770.812,44 | 61.770.812,44 | 0 |
| rampup mes1 | 0,85 | 0,85 | 0 |

KPIs de Cadena A: **sin cambio**. Solo los agregados que incluyen B cambiaron.

## 3. Artefactos

- Output completo: `storage/simulation_results/baseline_formula_v1.json`
- Snapshot congelado (actualizado): `tests/refactor/baseline_formula_snapshot_v0.json`
  (renominalización pendiente; mismo archivo, valores actualizados a B1)
- Tests guardrails: `tests/refactor/test_baseline_formula_snapshot_v0.py` (5 tests)
- Tests nuevos: `tests/refactor/test_input_contract_fix_b1.py` (7 tests, 7/7 PASSED)

## 4. Input Contract Impact

- Cambio en contrato de entrada: **NINGUNO** (mismo formato soportado, se añade tolerancia)
- Adapter `NewEntryDataAdapter`: **sin cambios**
- DTOs públicos: **sin cambios**
- Calculadores: **sin cambios**
- Solo `user_input_loader.py` — método privado `_normalizar_entry_data_format`

## 5. Próximo paso

Baseline 1 es el punto de partida para el refactor de no_payroll.
Cadena B fluye; baseline numérico es confiable y completo.
