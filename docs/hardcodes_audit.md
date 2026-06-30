# Hardcodes Audit — NEXA Pricing Engine

> Generated: 2026-05-21
> Scope: All Python source files in `backend_nexa/` (excluding venv, __pycache__, worktrees)
> Method: Line-by-line forensic scan of calculators, engine, domain, adapters, shared, repositories

---

## Executive Summary

The NEXA engine has **strong parametrization architecture** — most financial data flows through
`IParametrizationProvider` from `storage/parametrization/{hr,gn,op}/`. However, **two modules**
contain significant hardcoded business rules that should be externalized:

1. **`engine.py` → `_calcular_reglas_negocio()`** — Policy min/max ranges (POLITICAS)
2. **`calculators/riesgo.py` → `RiesgoCalculator`** — 20+ risk thresholds, weights, and SMMLV

Additionally, there are a few minor items in `vision_tarifas.py`, `domain/models.py`,
and `context_builder.py` that warrant attention.

---

## Phase 1: Forensic Inventory

### CRITICAL — Business Policy Hardcodes

| Archivo | Linea | Valor | Tipo | Riesgo | Origen Excel | Accion Recomendada |
|---------|-------|-------|------|--------|--------------|-------------------|
| `engine.py` | 271 | `0.05` | contingencia_operativa min | **ALTO** | Panel Control General B67 | Migrar a `config/business_rules/` |
| `engine.py` | 271 | `0.08` | contingencia_operativa max | **ALTO** | Panel Control General E67 | Migrar a `config/business_rules/` |
| `engine.py` | 272 | `0.04` | contingencia_comercial min | **ALTO** | Panel Control General B68 | Migrar a `config/business_rules/` |
| `engine.py` | 272 | `0.07` | contingencia_comercial max | **ALTO** | Panel Control General E68 | Migrar a `config/business_rules/` |
| `engine.py` | 273 | `0.02` | markup min | **ALTO** | Panel Control General B69 | Migrar a `config/business_rules/` |
| `engine.py` | 273 | `0.08` | markup max | **ALTO** | Panel Control General E69 | Migrar a `config/business_rules/` |
| `engine.py` | 274 | `0.0` | descuento min | **ALTO** | Panel Control General B70 | Migrar a `config/business_rules/` |
| `engine.py` | 274 | `0.08` | descuento max | **ALTO** | Panel Control General E70 | Migrar a `config/business_rules/` |
| `engine.py` | 269 | `None, None` | margen_objetivo sin limites | MEDIO | Panel Control General B66 | Definir limites si existen en Excel |

### CRITICAL — Risk Model Hardcodes (riesgo.py)

| Archivo | Linea | Valor | Tipo | Riesgo | Origen Excel | Accion Recomendada |
|---------|-------|-------|------|--------|--------------|-------------------|
| `riesgo.py` | 90 | `1000.0` | UMBRAL_APROBACION_SMMLV | **ALTO** | Riesgo col Q | Migrar a `config/business_rules/riesgo.json` |
| `riesgo.py` | 91 | `1_423_500.0` | SMMLV_2026 | **ALTO** | Regulatorio anual | Migrar a `storage/parametrization/gn/` — cambia cada anio |
| `riesgo.py` | 98 | `60` | PERIODO_PAGO_LIMITE_ALTO | **ALTO** | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 99 | `30` | PERIODO_PAGO_LIMITE_BAJO | **ALTO** | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 106 | `0.05` | MIN_CONTINGENCIA_OPERATIVA | **ALTO** | Panel C67 | Migrar (duplica engine.py POLITICAS min) |
| `riesgo.py` | 107 | `0.04` | MIN_CONTINGENCIA_COMERCIAL | **ALTO** | Panel C68 | Migrar (duplica engine.py POLITICAS min) |
| `riesgo.py` | 108 | `3` | ALERTAS_LIMITE_ALTO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 109 | `1` | ALERTAS_LIMITE_MEDIO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 112 | `6` | COMPLEJIDAD_LIMITE_ALTO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 113 | `3` | COMPLEJIDAD_LIMITE_MEDIO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 116 | `8` | CAPACITACION_LIMITE_BAJO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 117 | `4` | CAPACITACION_LIMITE_MEDIO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 120 | `0.10` | ROTACION_LIMITE_ALTO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 121 | `0.05` | ROTACION_LIMITE_MEDIO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 124 | `2.5` | SCORE_LIMITE_ALTO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 125 | `1.5` | SCORE_LIMITE_MEDIO | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 128 | `0.4` | PESO_CLIENTE | MEDIO | Riesgo B1:Y282 | Migrar a config |
| `riesgo.py` | 129 | `0.6` | PESO_OPERATIVO | MEDIO | Riesgo B1:Y282 | Migrar a config |
| `riesgo.py` | 132-143 | criterios meta (pesos) | Pesos por criterio | MEDIO | Riesgo hoja Excel | Migrar a config |
| `riesgo.py` | 95 | `{"No Grupo Aval"}` | TIPOS_CLIENTE_ALTO | MEDIO | Riesgo col Q | Migrar a config |
| `riesgo.py` | 102 | `{"Cliente Nuevo"}` | ANTIGUEDAD_ALTO | MEDIO | Riesgo col Q | Migrar a config |
| `riesgo.py` | 358 | `3` | dependencia terceros limite alto | BAJO | Riesgo hoja Excel | Migrar a config |

### MODERATE — Fallbacks and Defaults

| Archivo | Linea | Valor | Tipo | Riesgo | Origen Excel | Accion Recomendada |
|---------|-------|-------|------|--------|--------------|-------------------|
| `vision_tarifas.py` | 296-297 | `0.5` / `0.5` | Rough payroll/no-payroll split | MEDIO | N/A — fallback | Documentar como fallback; OK si calculators siempre presentes |
| `domain/models.py` | 260 | `0.7` | pct_cumplimiento_variable default | BAJO | HR-SalarioBasico | OK — overridden by context_builder from parametrizacion |
| `context_builder.py` | 178 | `0` | horas_formacion_mensual | BAJO | N/A | Informativo — no afecta calculo |
| `context_builder.py` | 182 | `"Anual"` | frecuencia indexacion | BAJO | Convencion Excel V2-4 | OK — es una constante de diseno, no financiera |
| `context_builder.py` | 464 | `1.0` | factor_base indexacion | BAJO | Convencion Excel V2-4 | OK — es la definicion del modelo (anio inicio = base 1.0) |
| `context_builder.py` | 474 | `0.0` | costo_estudio_seg | BAJO | No implementado aun | Conectar a parametrizacion cuando haya dato en HR |
| `adapters/unified_input_adapter.py` | 244 | `0.0` | tmo_segundos default | BAJO | N/A — informativo | OK — campo informativo |
| `adapters/unified_input_adapter.py` | 383 | `0.0` | inversion_anual default | BAJO | N/A | OK — default sensato |

### SAFE — Technical Constants (NO action needed)

| Archivo | Linea | Valor | Tipo | Justificacion |
|---------|-------|-------|------|---------------|
| `nomina_cargada.py` | 118 | `2 * smmlv` | Umbral auxilio transporte | Regulatorio — formula legal (2 SMMLV) fija en el CST |
| `nomina_cargada.py` | 162 | `2 * smmlv` | Umbral dotaciones | Regulatorio — formula legal fija |
| `no_payroll.py` | 136 | `mes == 1` | CAPEX inicial solo mes 1 | Logica de negocio correcta — setup es mes 1 |
| `cadena_c.py` | 112 | `12` | Division inversion_anual/12 | Matematica pura — anual a mensual |
| `nomina.py` | 253 | `12` | pct_examen_anual / 12 | Matematica pura — anual a mensual |
| `calculators/utils.py` | 81 | `12` | ciclo anual en factor_aumento | Matematica pura — 12 meses/anio |
| `domain/models.py` | `= 0.0` defaults | Muchos | Dataclass defaults | Tecnico — backward compat, todos overridden |
| `shared/validator_utils.py` | 12 | `0.8` | Fuzzy-match cutoff | Tecnico — UX, no financiero |
| `input_validator.py` | regex patterns | Varios | Excel reference detection | Tecnico — seguridad de inputs |
| `vision_pyg.py` | 37-72 | Row definitions | Labels, secciones, signos | Tecnico — definicion de la tabla de presentacion |

---

## Phase 2: Traceability

### Flow 1: POLITICAS (engine.py:264-275)

```
Excel "Panel de Control General" B66:E70 (min/max ranges)
  → NO en parametrizacion (gap)
  → hardcoded in engine._calcular_reglas_negocio()
  → ReglaNegocios model
  → pricing_serializer → reglas_negocio list
  → Frontend seccion 07 (Contingencias)
```

**Why it must be parametrized**: These ranges change per client segment, regulatory updates,
or commercial strategy. Currently, changing them requires a code deploy.

### Flow 2: RiesgoCalculator thresholds (riesgo.py:87-143)

```
Excel "Riesgo" B1:Y282 (thresholds, weights, SMMLV)
  → NO en parametrizacion (gap)
  → hardcoded as class attributes in RiesgoCalculator
  → EvaluacionRiesgo model
  → pricing_serializer → evaluacion_riesgo dict
  → Frontend seccion 06 (Control de Riesgo)
```

**Why it must be parametrized**: SMMLV changes annually (regulatory). Weights and thresholds
are calibration parameters that will need tuning as the business evolves.

### Flow 3: MIN_CONTINGENCIA duplicates

```
engine.py:271  → contingencia_operativa min = 0.05
riesgo.py:106  → MIN_CONTINGENCIA_OPERATIVA = 0.05
engine.py:272  → contingencia_comercial min = 0.04
riesgo.py:107  → MIN_CONTINGENCIA_COMERCIAL = 0.04
```

**Risk**: These are the same business rule duplicated in two files. A change in one
without the other creates an inconsistency.

### Flow 4: pct_cumplimiento_variable = 0.7 (models.py:260)

```
storage/parametrization/hr/*.json → pct_cumplimiento_variable
  → ParametrizationProvider.get_nomina_laboral_params()
  → context_builder._construir_parametros_calculo() (line 699)
  → ParametrosCalculo.pct_cumplimiento_variable (overrides the 0.7 default)
  → NominaCalculator._comisiones()
```

**Status**: SAFE — the 0.7 is a dataclass default that is always overridden at runtime.
Removing it would break backward compat for any code that constructs `ParametrosCalculo`
without explicit `pct_cumplimiento_variable`. Keep as-is with documentation.

### Flow 5: factor_base = 1.0 (context_builder.py:464)

```
Convention: year-of-contract-start is always base 1.0
  → factor_indexacion_base = 1.0 (hardcoded)
  → ParametrosNomina.factor_indexacion_base
  → NominaCalculator._factor_indexacion()
```

**Status**: SAFE — this is NOT a calibration parameter. It's the mathematical definition
of the indexation model: "the starting year has factor 1.0, subsequent years grow by
pct_aumento". Changing this would change the model itself, not a parameter.

### Flow 6: vision_tarifas 0.5 split (vision_tarifas.py:296-297)

```
Only reached when calc_nomina AND calc_no_payroll are both None
  → total * 0.5 for payroll, total * 0.5 for no_payroll
  → TarifaCanal.payroll_ch / no_payroll_ch
```

**Status**: LOW RISK — this is a defensive fallback for degraded operation. In production,
both calculators are always injected by the engine. Should be documented but not prioritized.

---

## Phase 3: Parametrization Design

### Proposed Structure

```
storage/parametrization/gn/
  reglas_negocio.json          ← NEW: policy ranges (POLITICAS)
  riesgo_config.json           ← NEW: risk model thresholds & weights
  constantes_regulatorias.json ← NEW: SMMLV, umbral aprobacion
```

### reglas_negocio.json

```json
{
  "version": "2026-01",
  "politicas_comerciales": {
    "margen_objetivo": {
      "min": null,
      "max": null,
      "label": "Margen objetivo"
    },
    "contingencia_operativa": {
      "min": 0.05,
      "max": 0.08,
      "label": "Contingencia Operativa"
    },
    "contingencia_comercial": {
      "min": 0.04,
      "max": 0.07,
      "label": "Contingencia Comercial"
    },
    "markup": {
      "min": 0.02,
      "max": 0.08,
      "label": "Markup"
    },
    "descuento": {
      "min": 0.0,
      "max": 0.08,
      "label": "Descuento volumen"
    }
  }
}
```

### riesgo_config.json

```json
{
  "version": "2026-01",
  "pesos_categorias": {
    "Cliente": 0.4,
    "Operativo": 0.6
  },
  "clasificacion_score": {
    "alto": 2.5,
    "medio": 1.5
  },
  "criterios": [
    {
      "id": 1,
      "factor": "Clasificacion de oportunidad",
      "categoria": "Cliente",
      "peso": 0.30
    },
    {
      "id": 2,
      "factor": "Tipo de cliente",
      "categoria": "Cliente",
      "peso": 0.25
    }
  ],
  "umbrales": {
    "periodo_pago_alto": 60,
    "periodo_pago_bajo": 30,
    "alertas_alto": 3,
    "alertas_medio": 1,
    "complejidad_alto": 6,
    "complejidad_medio": 3,
    "capacitacion_bajo": 8,
    "capacitacion_medio": 4,
    "rotacion_alto": 0.10,
    "rotacion_medio": 0.05,
    "dependencia_terceros_alto": 3,
    "min_contingencia_operativa": 0.05,
    "min_contingencia_comercial": 0.04
  },
  "tipos_cliente_alto": ["No Grupo Aval"],
  "antiguedad_alto": ["Cliente Nuevo"]
}
```

### constantes_regulatorias.json

```json
{
  "version": "2026-01",
  "smmlv": 1423500.0,
  "anio_vigencia": 2026,
  "umbral_aprobacion_smmlv": 1000.0
}
```

### Provider Interface Extension

Add to `IParametrizationProvider`:

```python
def get_politicas_comerciales(self) -> Dict[str, Any]:
    """Policy min/max ranges for contingencies, markup, descuento."""
    ...

def get_riesgo_config(self) -> Dict[str, Any]:
    """Risk model thresholds, weights, criteria, and classification limits."""
    ...

def get_constantes_regulatorias(self) -> Dict[str, Any]:
    """SMMLV, approval thresholds, and other regulatory constants."""
    ...
```

---

## Phase 4: Refactor Plan (Ordered by Risk)

### Step 1: Create JSON config files (zero code impact)
- Create `storage/parametrization/gn/reglas_negocio.json`
- Create `storage/parametrization/gn/riesgo_config.json`
- Create `storage/parametrization/gn/constantes_regulatorias.json`
- Populate with exact current hardcoded values

### Step 2: Extend provider interface + implementation
- Add 3 methods to `IParametrizationProvider`
- Implement in `ParametrizationProvider` (load from JSON)
- Add to mock provider for tests

### Step 3: Migrate engine.py POLITICAS
- `_calcular_reglas_negocio()` reads from provider instead of hardcoded list
- Contract: same `ReglaNegocios` output, same serialized JSON

### Step 4: Migrate riesgo.py thresholds
- `RiesgoCalculator.__init__()` receives config from provider
- All class-level constants become instance attributes loaded from config
- Contract: same `EvaluacionRiesgo` output

### Step 5: Eliminate duplicate (MIN_CONTINGENCIA in riesgo.py)
- Both `engine.py` and `riesgo.py` read from same source
- Single source of truth for min contingencies

---

## Phase 5: Testing Strategy

### Required Tests per Migration Step

1. **Loading tests**: Verify JSON files parse correctly and all required fields exist
2. **Contract tests**: Before/after golden output comparison for every migrated module
3. **Fallback tests**: If JSON is missing/corrupt, system should fail fast with clear error
4. **Regression tests**: Full pipeline `test_baseline_regression.py` must pass identically
5. **Snapshot tests**: Serialize full `PricingResult` before and after, diff must be empty

### Existing Test Coverage (must remain green)

- `tests/contract/test_vision_cost_to_serve_phase_a.py` — 330 tests
- `tests/contract/test_vision_pyg_contract.py`
- `tests/contract/test_vision_tarifas_contract.py`
- `tests/integration/test_baseline_regression.py`
- `tests/unit/test_riesgo_calculator.py`

---

## Phase 6: Priority Matrix

| Item | Severity | Effort | Priority |
|------|----------|--------|----------|
| SMMLV_2026 in riesgo.py | CRITICAL (breaks annually) | Low | **P0** |
| POLITICAS in engine.py | HIGH (business rule) | Medium | **P1** |
| Risk thresholds in riesgo.py | HIGH (20+ values) | Medium | **P1** |
| Duplicate MIN_CONTINGENCIA | MEDIUM (consistency) | Low | **P2** |
| vision_tarifas 0.5 fallback | LOW (never reached) | Low | **P3** |
| pct_cumplimiento_variable default | LOW (always overridden) | None | **Skip** |
| factor_base = 1.0 | NONE (model definition) | None | **Skip** |
| horas_formacion_mensual = 0 | NONE (informativo) | None | **Skip** |

---

## Restrictions Checklist

- [x] No financial logic modified without forensic evidence
- [x] No new hardcodes introduced
- [x] All existing tests baseline documented
- [x] Traceability from Excel cell to serializer output
- [x] Backward compatibility plan for every change
- [x] Clean architecture (provider interface, not direct file reads)
