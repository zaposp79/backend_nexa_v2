# Formula Refactor Baseline 0

Línea base confiable del motor NEXA previa a la reorganización de fórmulas.
Branch: `refactor/modular-pure`. Fecha: 2026-06-06.

## 1. Input utilizado
- Archivo: `backend_nexa/request/request.json`
- Tipo: Bancamia — Cobranzas — "No Grupo Aval"
- Duración: 24 meses (fecha_inicio 2026-01-01)
- Pólizas: 10 (todas activas; incluye Comisión Admón 1.18% e impuestos)
- Cadena A: 3 perfiles (Inbound 10 / Inbound 15 / Inbound 20)
- Cadenas activas: A + B (C desactivada en el request)
- Ciudad: Bogotá (proporción 1.0), sede Toberín
- ICA 0.0097, GMF 0.004, costo de financiación = true

## 2. Parametrización utilizada
- HR activa: `v2-7` (storage/parametrization/hr/versions.json → is_active)
- GN activa: `v2-7`
- OP activa: `v2-7`
- Business rules activa: `v2-7`
- Fecha de activación: 2026-05-27T18:33:00Z (label "Excel V2-7 — WAVE 2 activation")
- Nota: el snapshot de versiones que expone el builder vino vacío en la corrida
  directa (PARAM_VERSIONS={}) porque `_br_repo` no fue inyectado vía container
  (warning `[PARAMETRIZATION] _br_repo not injected; falling back to
  get_parametrization_store()`). El fallback usa el store activo (v2-7),
  por lo que los valores son correctos; solo la traza de versión queda vacía.

## 3. Output backend actual
- Archivo: `backend_nexa/storage/simulation_results/baseline_formula_v0.json`
- Snapshot congelado: `backend_nexa/tests/refactor/baseline_formula_snapshot_v0.json`
- Estructura PricingResult válida (22 claves top-level):
  simulation_id, scenario, calculated_at, vision_por_servicio, vision_por_canal,
  detalle_por_canal, estructura_equipo, comparativo_escenarios, ficha_deal,
  kpis, pyg_por_mes (24 meses), waterfall_promedio, configuracion_comercial,
  reglas_negocio, evaluacion_riesgo, vision_pyg, cost_to_serve, vision_tarifas,
  panel, polizas, datasets_vision, audit_trace.
- Errores: none. Las 10 capas ejecutaron; `validate_visions_complete` OK.

### KPIs ancla (Bancamia Cobranzas)
| KPI | Valor |
|---|---|
| ingreso_mensual | 260.842.533,88 |
| costo_cadena_a_promedio | 185.297.653,44 |
| costo_total_contrato | 4.447.143.682,59 |
| utilidad_neta_total | 1.659.262.761,34 |
| pct_utilidad_neta_total | 0,27172 (27,17%) |
| margen_minimo_requerido | 0,21 (Cobranzas) |
| cumple_margen_minimo | false (margen objetivo 0.18 < mínimo 0.21) |

### P&G mes 1 ancla
| Concepto | Valor |
|---|---|
| rampup | 0,85 (Cobranzas, Excel Rot/Ausent/Rent B38) |
| payroll_a | 154.103.322,32 |
| no_payroll_a | 61.770.812,44 |
| ica_a | 2.728.240,45 |
| gmf_a | 863.496,54 |
| polizas | 3.591.736,99 |
| contribucion | 38.738.201,72 |
| pct_utilidad_neta | 0,15215 |

## 4. Comparación Excel/Backend
Ver matriz completa en `formula_refactor_baseline_0_comparison.md`.

Resumen: el Excel V2-7 está cacheado para OTRO deal (AMERICAS / Captura de
Datos / 12 meses / Cadena C dominante / canal Voz), por lo que la comparación
agregada deal-a-deal es **NO_COMPARABLE**. Lo que SÍ está en paridad exacta son
las constantes deal-independientes leídas de storage v2-7:

| Concepto | Excel | Backend | Estado |
|---|---|---|---|
| Rentabilidad mín. Cobranzas | 0.21 | 0.21 | MATCH |
| Margen objetivo Cobranzas | 0.18 | 0.18 | MATCH |
| Ramp-up Cobranzas (m1/m2/m3) | 0.85/0.92/1.0 | 0.85 (m1 verificado) | MATCH |
| Prestaciones (Ces/Pri/Int/Vac) | 0.0833/0.0833/0.12/0.0417 | idem | MATCH |
| Seg. social (Salud/Pensión/ARL/Caja/Sena) | 0.085/0.12/0.00522/0.04/0.04 | idem | MATCH |
| Salario mínimo / Aux. transporte | 1.750.905 / 249.095 | idem | MATCH |

Estado global de la comparación: ~50% MATCH (constantes), ~10%
MATCH_CON_TOLERANCIA (inputs deal ICA/GMF), ~40% NO_COMPARABLE (agregados,
por estado cacheado distinto del Excel). 1 DIVERGENCIA real (D-1, abajo).

## 5. Divergencias identificadas

### D-1 — Cadena B no fluye al resultado (REQUIERE_DECISION_NEGOCIO / BUG TÉCNICO)
- **Síntoma:** `costo_b = 0` en los 24 meses y `volumen_mensual = 0`, aunque
  `vision_por_servicio.cadenas_activas = ["A","B"]` y request.json trae
  `condiciones_cadena_b` con 16 ítems OPEX, CAPEX, HITL y tarifas.
- **Causa raíz:** request.json usa doble anidamiento
  `condiciones_cadena_b.condiciones_cadena_b.{opex,hitl,...}`. El detector
  `NewEntryDataAdapter._es_formato_entry_data_b` inspecciona el nivel externo
  (cuyas claves son solo `{condiciones_cadena_b}`), no encuentra ni claves
  entry_data ni internas → devuelve False → el adapter NO traduce → cadena_b
  se construye vacía (canales=0, opex=0). Mismo patrón en cadena_c.
- **Clasificación:** BUG TÉCNICO de contrato de entrada (nesting mismatch), NO
  decisión de negocio. Pre-existente; no introducido por este baseline.
- **Impacto:** subestima el costo del deal (omite costo Cadena B). KPIs y P&G
  reflejan solo Cadena A.
- **Recomendación:** decisión de negocio sobre el contrato — ¿request.json debe
  enviar `condiciones_cadena_b` plano (un solo nivel) o el adapter debe
  desenvolver el doble anidamiento? NO se corrige en este baseline (regla: no
  tocar código productivo). Escalar a backend-agent una vez tomada la decisión.

### D-2 — Traza de versión de parametrización vacía (NO bloqueante)
- Snapshot de versiones vacío en corrida directa por `_br_repo` no inyectado
  (sin container). Valores correctos (fallback a store activo v2-7); solo la
  trazabilidad de version_id queda sin poblar fuera del flujo HTTP/lifespan.

## 6. Formula IDs propuestos
50+ IDs en `formula_refactor_baseline_0_formula_ids.md`, formato
`LAYER.COMPONENT_CALCULATION`, mapeados a ubicación en código y tipo de cálculo,
cubriendo capas 2-10 + CTS + Tarifas + Imprimible + Riesgo. NO se implementó
tracing (fuera de scope de baseline 0).

## 7. Guardrails creados
Archivo: `backend_nexa/tests/refactor/test_baseline_formula_snapshot_v0.py`
- test_engine_runs_request — motor ejecuta request.json sin error
- test_pricing_result_is_valid — 5 visiones presentes, 24 meses
- test_snapshot_parity (`@baseline`) — output == snapshot (ignora timestamps)

## 8. Correcciones detectadas post-baseline

### D-1: Doble anidamiento Cadena B (FIJO en Baseline 1)
- **Detectado:** Sección 5 de este documento
- **Causa:** request.json usa `condiciones_cadena_b.condiciones_cadena_b.{opex,...}`.
  El loader pasaba el nivel externo al adapter que no detectaba el formato → cadena_b vacía.
- **Impacto:** Cadena B no fluía (costo_b=0 en los 24 meses, ~964M COP omitidos).
- **Fix:** `user_input_loader.py` `_normalizar_entry_data_format` — unwrap guard análogo
  al que ya existía para `condiciones_cadena_a` (línea 346).
- **Artefactos:** `docs/refactor/formula_refactor_baseline_1.md`,
  `tests/refactor/test_input_contract_fix_b1.py` (7/7 PASSED)
- **Snapshot y anchors:** actualizados en `test_baseline_formula_snapshot_v0.py`
  y `baseline_formula_snapshot_v0.json` para reflejar Baseline 1 (con cadena_b).
- **Contratos públicos:** sin cambios.
- test_kpis_anchor_values (`@baseline`) — 6 KPIs ancla exactos
- test_pyg_month1_anchor (`@baseline`) — ramp 0.85 + payroll/no_payroll/ICA/GMF

Snapshot congelado: `tests/refactor/baseline_formula_snapshot_v0.json`.

Comandos para validar antes/después del refactor:
```bash
PYTHONPATH=$(pwd) backend_nexa/venv/bin/python -m pytest \
  backend_nexa/tests/refactor/test_baseline_formula_snapshot_v0.py -q
PYTHONPATH=$(pwd) backend_nexa/venv/bin/python -m pytest backend_nexa/tests/golden/ -q
```
Resultado actual: refactor 5/5 PASSED; golden 58/58 PASSED.

## 8. Primera fase recomendada
**Comenzar con `no_payroll` (Capa 3 — NoPayrollCalculator).**

Justificación:
1. **Aislamiento:** es la capa con menos dependencias entrantes; solo consume
   `solicitud.parametros_no_payroll`. No depende de otras capas de cálculo.
2. **Riesgo bajo:** su salida alimenta CostosTotales de forma aditiva; no entra
   en bucles de indexación/ramp como Nómina. Un error es fácil de aislar.
3. **Valor de clarificación:** mezcla OPEX fijo, infraestructura, TI/licencias y
   CAPEX amortizado — buenos candidatos a extraer/parametrizar con formula_ids
   (NO_PAYROLL.OPEX_FIJO, .INFRAESTRUCTURA, .TI_LICENCIAS, .INVERSIONES_CAPEX).
4. **Cobertura de guardrail:** el snapshot ya ancla `no_payroll_a = 61.770.812,44`
   en mes 1, así que cualquier drift se detecta de inmediato.
5. **No bloqueado por D-1:** la divergencia de Cadena B no afecta a no_payroll
   (Cadena A), por lo que se puede avanzar sin esperar la decisión de negocio.

Nómina (fundamental, muchas dependencias: ramp, indexación, prestaciones,
roles) y Costos Financieros (intermedio: ICA/GMF/pólizas/financiación) quedan
para fases posteriores, una vez validado el patrón con no_payroll.

## 9. Criterio para permitir refactor
- Baseline snapshot generado — OK (`baseline_formula_snapshot_v0.json`)
- Guardrails en place y pasando — OK (5/5)
- Golden/parity suite pasando — OK (58/58)
- Formula IDs documentados — OK (50+)
- Matriz Excel/Backend cerrada — OK (constantes en paridad; agregados
  NO_COMPARABLE por estado cacheado; D-1 documentado)
- Pendiente: decisión de negocio sobre D-1 (no bloquea fase no_payroll).

## 10. Qué NO se tocó
- Código productivo intacto (motor, calculadores, serializers, adapters).
- Contratos públicos (DTOs, ApiResponse) intactos.
- Ningún archivo movido.
- Excel sin tocar en runtime (solo lectura data_only).
- NO se creó `modules/calculator/formulas/`.
- NO se hizo commit ni refactor.

## 11. Próximo paso
Proceder con la Fase 1 del refactor sobre `no_payroll` (Capa 3), corriendo los
guardrails antes y después de cada cambio. En paralelo, escalar la decisión de
negocio sobre D-1 (doble anidamiento de condiciones_cadena_b/c) al
backend-agent, ya que afecta paridad de deals con Cadena B/C activa pero NO
bloquea la fase no_payroll.
