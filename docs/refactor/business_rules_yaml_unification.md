# BUSINESS_RULES_YAML_UNIFICATION

**Fecha:** 2026-06-07  
**Status:** ✅ COMPLETE  
**Branch:** refactor/modular-pure

---

## Objetivo

Unificar la configuración YAML de business rules en una sola ubicación canónica, eliminando la duplicidad entre `config/business_rules/` (raíz) y `modules/shared/config/business_rules/`.

---

## Estructura anterior

```
backend_nexa/
  config/
    business_rules/
      riesgo.yaml                    ← ORPHANED (no importado en runtime)
  modules/
    shared/
      config/
        business_rules/
          loader.py                  ← CANONICAL (vision_tarifas)
          operaciones.yaml           ← CANONICAL
          margenes.yaml              ← CANONICAL
      infrastructure/
        business_rules_loader.py     ← LEGACY loader → config/business_rules/
```

**Problemas detectados:**
- `config/business_rules/riesgo.yaml` no era importado desde ningún módulo de runtime — solo desde 3 archivos de tests via `infrastructure/business_rules_loader.py`
- `infrastructure/business_rules_loader.py` apuntaba a `config/business_rules/` (raíz) en lugar del directorio canónico
- `modules/shared/config/business_rules/loader.py` no exponía API genérica (`load_business_rules`) — solo `get_business_rules()` / `BusinessRulesConfig`
- La función `load_business_rules_cached` mencionada en `CLAUDE.md` solo existía en la ubicación legacy

---

## Estructura nueva

```
backend_nexa/
  modules/
    shared/
      config/
        business_rules/             ← ÚNICA UBICACIÓN CANÓNICA
          loader.py                 ← API completa: get_business_rules() + load_business_rules()
          riesgo.yaml               ← MOVIDO desde config/business_rules/
          operaciones.yaml          ← sin cambios
          margenes.yaml             ← sin cambios
      infrastructure/
        business_rules_loader.py    ← SHIM (re-export DEPRECATED)
```

---

## Archivos modificados / creados / eliminados

| Archivo | Acción | Detalle |
|---|---|---|
| `config/business_rules/riesgo.yaml` | **ELIMINADO** | Movido a ubicación canónica |
| `config/business_rules/` | **ELIMINADO** | Directorio eliminado (quedó vacío) |
| `modules/shared/config/business_rules/riesgo.yaml` | **CREADO** | Movido desde config/ |
| `modules/shared/config/business_rules/loader.py` | **MODIFICADO** | Añadidas `load_business_rules()` + `load_business_rules_cached()` |
| `modules/shared/infrastructure/business_rules_loader.py` | **CONVERTIDO A SHIM** | Re-export DEPRECATED desde canonical |
| `tests/unit/test_business_rules_yaml_unification.py` | **CREADO** | 12 guardrail tests |

---

## API canónica (módulo canonical)

```python
from nexa_engine.modules.shared.config.business_rules.loader import (
    get_business_rules,           # → BusinessRulesConfig (operaciones + margenes)
    load_business_rules,          # → dict desde cualquier YAML del dir
    load_business_rules_cached,   # → dict cacheado
)
```

---

## Shim de compatibilidad (no usar en código nuevo)

```python
# Todavía funciona (3 test files no migrados):
from nexa_engine.modules.shared.infrastructure.business_rules_loader import load_business_rules
```

El shim es un re-export puro. Los tests existentes no necesitan cambios.

---

## Consumidores de runtime sin cambios

| Módulo | Import | Estado |
|---|---|---|
| `vision_tarifas/reglas.py` | `...config.business_rules.loader.get_business_rules` | Sin cambios |
| `vision_tarifas/mixins/reglas_methods_1.py` | idem | Sin cambios |
| `vision_tarifas/mixins/reglas_methods_2.py` | idem | Sin cambios |

---

## Tests ejecutados

```
tests/unit/test_business_rules_yaml_unification.py    12/12 PASS ✅
tests/unit/test_business_rules_guardrails.py          25/25 PASS ✅
tests/golden/                                         58/58 PASS ✅
tests/refactor/test_baseline_formula_snapshot_v1.py    6/6 PASS ✅
tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py  4/4 PASS ✅
─────────────────────────────────────────────────────────────
Total verificado: 105 tests  Zero pricing drift
```

**Pre-existing failures (no relacionados):** 8 tests en `test_business_rules_config.py` y `test_business_rules_fix2.py` fallan por `AttributeError: 'RiesgoCalculator' object has no attribute '_smmlv'` — anterior a esta tarea.

---

## Riesgo

🟢 **ZERO** — Sin cambios a fórmulas, cálculos, runtime, contratos públicos ni storage/parametrization.

---

## Decisión de diseño

`operaciones.yaml` y `margenes.yaml` permanecen bajo `modules/shared/config/business_rules/` como configuración estática (no versionada). Estos valores son constantes BPO Colombia vinculadas a Excel V2-5 y no requieren el ciclo de versionado de parametrización (HR/GN/OP). Si en el futuro se requiere versionado de constantes operativas, ese es un scope separado.

`riesgo.yaml` es ahora un YAML de referencia co-ubicado. Los datos de riesgo en runtime provienen de `storage/parametrization/business_rules/v2-7.json` (Layer 2 activo). El YAML sirve como referencia documentada de la estructura del modelo.

---

## Siguiente paso

Ninguno requerido para este scope. Si se desea eliminar el shim:
1. Migrar los 3 test files a importar desde `...config.business_rules.loader`
2. Eliminar `modules/shared/infrastructure/business_rules_loader.py`
3. Actualizar `CLAUDE.md` para remover referencia a `infrastructure.business_rules_loader`
