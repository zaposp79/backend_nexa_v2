# Inventario de Failures Preexistentes — Pre Paso B V2-8

## Contexto
Baseline de failures antes de aplicar VALUE_UPDATE a request.json (Paso B V2-8).
Fecha de captura: 2026-06-10.
Rama: refactor/modular-pure.
No se investigó RCA. No se modifica código.

## Comando ejecutado
```bash
cd /Users/darwin.minota.quinto/Projects/NEXA && \
  source backend_nexa/venv/bin/activate && \
  PYTHONPATH=$(pwd) python -m pytest backend_nexa/tests/refactor/ -q --tb=short \
  2>&1 | tee /tmp/refactor_failures_pre_paso_b.txt
```

## Resultado bruto
```text
11 failed, 84 passed, 3 deselected, 1 warning in 3.78s
```

## Failures en tests/refactor/ (11 únicos — reporte directo de pytest)

| Test | Archivo | Categoría | Toca Paso B | Prioridad | Nota |
|------|---------|-----------|-------------|-----------|------|
| test_snapshot_parity | test_baseline_formula_snapshot_v0.py | snapshot | SÍ | ALTA | Drift vs snapshot v0 — afecta Payroll/P&G |
| test_kpis_anchor_values | test_baseline_formula_snapshot_v0.py | snapshot | SÍ | ALTA | KPIs anchor drift |
| test_pyg_month1_anchor | test_baseline_formula_snapshot_v0.py | snapshot | SÍ | ALTA | P&G mes 1 drift |
| test_snapshot_parity | test_baseline_formula_snapshot_v1.py | snapshot | SÍ | ALTA | Drift vs snapshot v1 |
| test_kpis_anchor_values | test_baseline_formula_snapshot_v1.py | snapshot | SÍ | ALTA | KPIs anchor drift v1 |
| test_pyg_month1_anchor | test_baseline_formula_snapshot_v1.py | snapshot | SÍ | ALTA | P&G mes 1 drift v1 |
| test_snapshot_parity | test_baseline_formula_snapshot_cadena_c_v1.py | snapshot | SÍ | ALTA | Drift vs snapshot cadena_c_v1 — activo parametrización nueva |
| test_baselines_still_pass_v1 | test_formula_id_guardrails.py | integración | SÍ | ALTA | Guardrail falla porque v1 snapshot tiene drift |
| test_baselines_still_pass_cadena_c | test_formula_id_guardrails.py | integración | SÍ | ALTA | Guardrail falla porque cadena_c snapshot tiene drift |
| test_golden_tests_still_pass | test_formula_id_guardrails.py | integración | SÍ | MEDIA | Guardrail indirectamente falla — golden v27 CTS/Tarifas drift |
| test_request_json_after_fix | test_input_contract_fix_b1.py | integración | SÍ | ALTA | Falla en validación de request.json post-fix B1 |

## Failures indirectos detectados (en tests/golden/ vía guardrail)
Los siguientes fallan cuando se ejecuta test_golden_tests_still_pass (no son tests directos del scope tests/refactor/):

| Suite | Cant. | Categoría | Toca Paso B |
|-------|-------|-----------|-------------|
| test_cost_to_serve_golden_v27.py | ~20 | oracle/CTS | SÍ — Payroll/salario |
| test_vision_tarifas_golden_v27.py | ~20 | oracle/Tarifas | SÍ — ingreso_bruto, payroll |

Causa probable: nueva parametrización HR activa (6506b1fa — HR_productiva_2026-06-10.xlsx) contiene valores distintos a los golden v2-7 congelados. UNINVESTIGATED (no RCA).

## Resumen de prioridad
- Prioridad ALTA: 10 (todos snapshot-based o input-contract directamente vinculados a Paso B)
- Prioridad MEDIA: 1 (test_golden_tests_still_pass — indirecto)
- Prioridad BAJA: 0

## BLOCKED_BY_PREEXISTING_FAILURES
**SÍ** — 10 failures de prioridad alta tocan directamente snapshots P&G / Payroll / cadena_c y el contrato de request.json.

## Reglas
- No se investigó RCA.
- Si no fue obvio en 1 minuto, se marca UNINVESTIGATED.
- Prioridad alta = toca directamente Cadena C, P&G, Payroll, pólizas o consumers de request.json.
- No actualizar snapshots para hacer pasar tests — investigar drift antes de modificar.
