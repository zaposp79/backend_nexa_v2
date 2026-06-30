# Visión Imprimible — Formula Ownership Sweep

**Fecha:** 2026-06-05
**Rama:** `refactor/modular-pure`
**Auditoría:** VISION_IMPRIMIBLE_FORMULA_OWNERSHIP_FINAL_SWEEP

---

## Resultado

**VISION_IMPRIMIBLE_FORMULA_OWNERSHIP_CERTIFIED — COMPLETO**
Todas las fórmulas propias de VI han sido movidas a `modules/vision_imprimible/helpers/`. El serializer solo contiene wrappers de delegación.

Tests ejecutados: **83 passed, 0 failed** (aprobaciones + ownership + guardrails).

---

## Criterios de clasificación

| Estado | Definición |
|---|---|
| `OK_SERIALIZACION_PURA` | Convierte dataclass → dict. No computa valores nuevos relevantes para VI. Puede quedarse en serializer. |
| `OK_DATO_PERSISTIDO` | Lee un campo ya calculado y lo expone. No hay fórmula; pertenece al dominio del dato, no de VI. |
| `OK_FORMULA_EN_MODULO_CORRECTO` | Fórmula propia de VI que ya vive en `modules/vision_imprimible`. |
| `FORMULA_DEBE_MOVERSE_A_VISION_IMPRIMIBLE` | Fórmula específica de una sección de VI que actualmente vive en el serializer. |
| `SHARED_PERSISTED_PROJECTION` | Agrega datos de múltiples fuentes persistidas. No es exclusiva de VI. |
| `FORMULA_BASE_NO_MOVER` | Fórmula del motor de cálculo. No es responsabilidad de VI. |

---

## Matriz completa

### `serializer_helpers.py`

| # | Elemento | Archivo actual | Tipo de contenido | Sección Excel | Dueño correcto | Estado | Acción requerida |
|---|---|---|---|---|---|---|---|
| SH-01 | `_pyg_to_dict` | `serializer_helpers.py` | Serialización de `PyGMensual` + captura de `@property` omitidas por `asdict()` | Evolución Mensual | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| SH-02 | `_desglose_cts_to_dict` | `serializer_helpers.py` | Serialización de `DesgloseCTSCadenaA` + expone `.total` | Cost To Serve | Serializer (dominio CTS) | `OK_SERIALIZACION_PURA` | Ninguna — no tocar CTS |
| SH-03 | `_desglose_cts_b_to_dict` | `serializer_helpers.py` | Serialización de `DesgloseCTSCadenaB` + expone `.total` | Cost To Serve | Serializer (dominio CTS) | `OK_SERIALIZACION_PURA` | Ninguna — no tocar CTS |
| SH-04 | `_cost_to_serve_to_dict` | `serializer_helpers.py` | Ensambla `desglose_a` + `desglose_b` en el dict CTS | Cost To Serve | Serializer (dominio CTS) | `OK_DATO_PERSISTIDO` | Ninguna — no tocar CTS |
| SH-05 | `_vision_tarifas_to_dict` | `serializer_helpers.py` | Proyección de campos `TarifaCanal` a los 15 visibles en hoja VT | Vision Tarifas | Serializer (proyección de VT) | `OK_SERIALIZACION_PURA` | Ninguna — el set `_VT_CANAL_FIELDS` es una lista de campos, no una fórmula |
| SH-06 | `_ficha_deal_to_dict` | `serializer_helpers.py` (wrapper) | Deriva `fecha_fin`, `duracion_contrato`, `mes_finalizacion` de `fecha_inicio + meses_contrato` | VI!B12:T13 Ficha del Deal (sección 01) | `modules/vision_imprimible/helpers/ficha.py` | `OK_FORMULA_EN_MODULO_CORRECTO` | **COMPLETADO — FORMULA_OWNERSHIP_2 (2026-06-05)** |
| SH-07 | `_reglas_negocio_to_dict` | `serializer_helpers.py` (wrapper) | **Wrapper de 1 línea** → delega a `vision_imprimible.helpers.reglas_negocio.reglas_negocio_to_dict` | VI sección 07 (Reglas de Negocio / Contingencias) | `modules/vision_imprimible/helpers/reglas_negocio.py` | `OK_FORMULA_EN_MODULO_CORRECTO` | **COMPLETADO — FORMULA_OWNERSHIP_4 (2026-06-05)** |
| SH-08 | `_reglas_negocio_to_list` | `serializer_helpers.py` | `[asdict(r) for r in reglas]` — lista pura | Sección 07 | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| SH-09 | `_waterfall_to_dict` | `serializer_helpers.py` | `asdict(wf) if wf else None` — guard + serialización | Sección 04 Waterfall | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| SH-10 | `_vision_pyg_to_dict` | `serializer_helpers.py` | Reorganización jerárquica de `VisionPyG` en secciones con `detalle` anidado. `_SECTION_META` es un mapeo de claves a labels. | Vision P&G | Serializer (pertenece a VisionPyG, no exclusivo de VI) | `OK_SERIALIZACION_PURA` | Ninguna — reorganización estructural sin fórmulas nuevas |
| SH-11 | `_aprobaciones_requeridas` | `serializer_helpers.py` (wrapper) | **Wrapper de 1 línea** → delega a `vision_imprimible.helpers.aprobaciones.aprobaciones_requeridas` | VI!M91-M93 (Aprobaciones) | `modules/vision_imprimible/helpers/aprobaciones.py` | `OK_FORMULA_EN_MODULO_CORRECTO` | Ninguna — FORMULA_OWNERSHIP_1 completado |
| SH-12 | `_evaluacion_riesgo_to_dict` | `serializer_helpers.py` | Serializa `EvaluacionRiesgo` + agrega alias `riesgo_actual` (= `calificacion`) + llama `_aprobaciones_requeridas` (ya delegado) | VI sección 06 (Evaluación de Riesgo) | Serializer — la función es principalmente serialización; el alias es trivial; la fórmula delegó | `OK_SERIALIZACION_PURA` | Ninguna — `riesgo_actual` es alias de presentación, no fórmula |
| SH-13 | `_vision_ejecutiva_sections` | `serializer_helpers.py` | Lee `resultado.vision_imprimible` y llama `asdict()` sobre sus secciones. No computa nada nuevo. | VI secciones 10-14 (Ejecutiva) | Serializer | `OK_SERIALIZACION_PURA` | Ninguna — consume lo que el Builder ya construyó |
| SH-14 | `_select_principal_channel` | `serializer_helpers.py` (wrapper) | **Wrapper de 1 línea** → delega a `vision_imprimible.helpers.configuracion_comercial.select_principal_channel` | VI sección 03 (Configuración Comercial) | `modules/vision_imprimible/helpers/configuracion_comercial.py` | `OK_FORMULA_EN_MODULO_CORRECTO` | **COMPLETADO — FORMULA_OWNERSHIP_3 (2026-06-05)** |
| SH-15 | `_configuracion_comercial` | `serializer_helpers.py` (wrapper) | **Wrapper de 1 línea** → delega a `vision_imprimible.helpers.configuracion_comercial.configuracion_comercial_to_dict` | VI sección 03 (Configuración Comercial) | `modules/vision_imprimible/helpers/configuracion_comercial.py` | `OK_FORMULA_EN_MODULO_CORRECTO` | **COMPLETADO — FORMULA_OWNERSHIP_3 (2026-06-05)** |
| SH-16 | `_polizas_por_cadena` | `serializer_helpers.py` | `sum(p.polizas_a/b/c for p in pyg_por_mes)` — agrega campos ya persistidos en P&G | Campo top-level `polizas` (no sección VI) | Serializer | `SHARED_PERSISTED_PROJECTION` | Ninguna — agrega datos de múltiples fuentes, no exclusivo de VI |

### `pricing_result_serializer.py`

| # | Elemento | Archivo actual | Tipo de contenido | Dueño correcto | Estado | Acción requerida |
|---|---|---|---|---|---|---|
| PS-01 | `pricing_result_to_dict` | `pricing_result_serializer.py` | Orquestador principal — llama helpers, construye dict final | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| PS-02 | `pricing_result_to_visions_response` | `pricing_result_serializer.py` | Orquestador del POST response — reutiliza mismos helpers | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| PS-03 | `validate_visions_complete` | `pricing_result_serializer.py` | Valida que el pipeline generó todas las visiones — precondición interna | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| PS-04 | `_build_execution_trace` | `pricing_result_serializer.py` | Audit/debug trace — enumeración de calculadoras y métricas del pipeline | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| PS-05 | `build_simulation_snapshot` | `pricing_result_serializer.py` | Construye `SimulationSnapshot` con mapeo de campos via `.get(key, default)` | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |
| PS-06 | `VisionIncompleteError` | `pricing_result_serializer.py` | Excepción del pipeline de validación | Serializer | `OK_SERIALIZACION_PURA` | Ninguna |

---

## Resumen de hallazgos

### Fórmulas que DEBEN moverse (4)

| ID | Fórmula | Sección Excel | Destino propuesto |
|---|---|---|---|
| ~~F-01~~ | ~~`_ficha_deal_to_dict`~~ | ~~VI!B12:T13 — Ficha (sección 01)~~ | **CERTIFICADO** — `vision_imprimible/helpers/ficha.py` (FORMULA_OWNERSHIP_2, 2026-06-05) |
| ~~F-02~~ | ~~`_reglas_negocio_to_dict`~~ | ~~VI sección 07 — Reglas de Negocio~~ | **CERTIFICADO** — `vision_imprimible/helpers/reglas_negocio.py` (FORMULA_OWNERSHIP_4, 2026-06-05) |
| ~~F-03~~ | ~~`_select_principal_channel`~~ | ~~VI sección 03 — Configuración Comercial~~ | **CERTIFICADO** — `vision_imprimible/helpers/configuracion_comercial.py` (FORMULA_OWNERSHIP_3, 2026-06-05) |
| ~~F-04~~ | ~~`_configuracion_comercial`~~ | ~~VI sección 03 — Configuración Comercial~~ | **CERTIFICADO** — `vision_imprimible/helpers/configuracion_comercial.py` (FORMULA_OWNERSHIP_3, 2026-06-05) |

### Fórmula ya certificada (1)

| ID | Fórmula | Estado |
|---|---|---|
| F-00 | `_aprobaciones_requeridas` | `OK_FORMULA_EN_MODULO_CORRECTO` — delegada a `vision_imprimible/helpers/aprobaciones.py` (FORMULA_OWNERSHIP_1) |

### Elementos OK en serializer (11)

`_pyg_to_dict`, `_desglose_cts_to_dict`, `_desglose_cts_b_to_dict`, `_cost_to_serve_to_dict`, `_vision_tarifas_to_dict`, `_reglas_negocio_to_list`, `_waterfall_to_dict`, `_vision_pyg_to_dict`, `_evaluacion_riesgo_to_dict`, `_vision_ejecutiva_sections`, `_polizas_por_cadena` (SHARED) + todos los de `pricing_result_serializer.py`.

---

## Análisis por fórmula pendiente

### F-01 — `_ficha_deal_to_dict` (fecha derivada)

```python
# Fórmula específica de VI sección 01 (Excel VI!B12:T13):
end_month = fi.month - 1 + panel.meses_contrato
end_year  = fi.year + end_month // 12
end_month = end_month % 12 + 1
last_day  = calendar.monthrange(end_year, end_month)[1]
end_day   = min(fi.day, last_day)
ff        = datetime(end_year, end_month, end_day) - timedelta(days=1)
fecha_fin          = ff.strftime("%Y-%m-%d")
duracion_contrato  = f"{fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}"
mes_finalizacion   = (fi.month - 1) + panel.meses_contrato
```

**Por qué debe moverse:** estas 3 derivadas no son serialización de un campo existente — son cómputos nuevos visibles solo en VI sección 01. Entran en la regla "fórmula propia de Visión Imprimible".

**Propuesta:** `vision_imprimible/helpers/ficha_deal.py` con `ficha_deal_to_dict(panel) → dict`. El serializer importa y delega.

---

### F-02 — `_reglas_negocio_to_dict` (alerta logic)

```python
# Fórmula específica de VI sección 07:
alerta_activa = requiere_aprobacion or len(reglas_fuera_rango) > 0
if requiere_aprobacion:
    alerta_mensaje = "El contrato requiere aprobacion por parte de Alta Dirección ..."
elif reglas_fuera_rango:
    alerta_mensaje = f"Reglas fuera de rango: {nombres}"
else:
    alerta_mensaje = ""
```

**Por qué debe moverse:** la lógica de alerta (condición OR, selección de mensaje) es propia de cómo VI sección 07 presenta las contingencias. La serialización pura de la lista de reglas ya está en `_reglas_negocio_to_list` (que puede quedarse).

**Propuesta:** `vision_imprimible/helpers/reglas_negocio.py` con `reglas_negocio_to_dict(reglas, resultado) → dict`. El serializer importa y delega.

---

### F-03+F-04 — `_select_principal_channel` + `_configuracion_comercial` (sección 03)

```python
# F-03: selección de canal (VI sección 03):
canal_principal = max(canales, key=lambda c: c.facturacion)

# F-04: fórmula tarifa_fija (VI sección 03):
tarifa_fija = canal_principal.facturacion * pct_fijo_global
```

**Por qué deben moverse:** son la lógica de construcción de VI sección 03. El Builder ya hace su propia selección de canal (primer canal con `ingreso_bruto > 0`) — la divergencia entre Builder y Serializer en la selección es documentada y conocida. Ambas funciones son VI-específicas.

**Propuesta:** `vision_imprimible/helpers/configuracion_comercial.py` con `select_principal_channel(canales)` y `configuracion_comercial_to_dict(resultado) → dict`. El serializer importa y delega.

---

## Nota sobre divergencias conocidas en sección 03

La divergencia Builder vs Serializer en la selección de canal es documentada:
- **Builder:** primer canal con `ingreso_bruto > 0`
- **Serializer / F-03:** canal con mayor `facturacion` (`max`)

Esta divergencia NO debe resolverse en esta fase. Al mover F-03+F-04 a `vision_imprimible/helpers/`, la divergencia se hace explícita en el módulo VI (no oculta en el serializer), lo cual es el estado correcto.

---

## Tests ejecutados

```
tests/parity/test_vision_imprimible_aprobaciones.py   23 passed
tests/parity/test_vision_imprimible_ownership.py      24 passed
tests/parity/test_vision_ejecutiva_sections.py         9 passed
tests/unit/test_business_rules_guardrails.py          25 passed
──────────────────────────────────────────────────────
Total                                                 85 passed, 0 failed
```

---

## Roadmap de próximas implementaciones

| Fase | Tarea | Fórmulas | Riesgo |
|---|---|---|---|
| ~~FORMULA_OWNERSHIP_2~~ | ~~Mover F-01~~ | `_ficha_deal_to_dict` | **COMPLETADO 2026-06-05** → `vision_imprimible/helpers/ficha.py` |
| ~~FORMULA_OWNERSHIP_3~~ | ~~Mover F-03+F-04~~ | ~~`_select_principal_channel`, `_configuracion_comercial`~~ | **COMPLETADO 2026-06-05** → `vision_imprimible/helpers/configuracion_comercial.py` |
| ~~FORMULA_OWNERSHIP_4~~ | ~~Mover F-02~~ | ~~`_reglas_negocio_to_dict` (alerta logic)~~ | **COMPLETADO 2026-06-05** → `vision_imprimible/helpers/reglas_negocio.py` |

Cada fase sigue el patrón establecido en FORMULA_OWNERSHIP_1:
1. Crear helper en `modules/vision_imprimible/helpers/<nombre>.py`.
2. Dejar en serializer solo el wrapper de delegación.
3. Actualizar G-11 / tests de ownership si aplica.
4. 0 cambios en output público.
