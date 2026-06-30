# SHARED_PROFITABILITY_SHIM_AUDIT

**Status:** COMPLETADO — Shim eliminado
**Veredicto:** `SHIM_REMOVE_READY` → ejecutado
**Fecha:** 2026-06-10

## 1. Resumen ejecutivo

El shim `modules/shared/profitability/` fue eliminado. No tenía consumidores — todos
los imports apuntaban a `modules/calculator_motor/formulas/profitability/`. El guardrail
que protegía la vieja ubicación fue invertido para proteger la canónica.

## 2. Ubicación canónica confirmada

`modules/calculator_motor/formulas/profitability/calculators.py` — 18 consumidores, todos apuntan aquí.

## 3. Consumidores del shim

**0** — ningún archivo fuera del propio shim importaba desde `shared.profitability`.

## 4. Exposición pública

Ninguna. El proyecto es una aplicación interna, sin distribución pública. Sin docs
ni `__all__` que prometiera estabilidad pública del path `shared.profitability`.

## 5. Decisión

`SHIM_REMOVE_READY` → ejecutado.

- 0 consumidores internos del shim
- Sin exposición pública
- Guardrail pre-existente roto (confirmaba que el shim era stale)

## 6. Cambios ejecutados

**Eliminados:**
- `modules/shared/profitability/__init__.py`
- `modules/shared/profitability/calculators.py`

**Actualizado:** `tests/unit/test_shared_guardrails.py`
- `test_profitability_calculators_still_in_shared` → `test_profitability_calculators_in_canonical_location`
- `test_profitability_calculators_exports_class` → apunta a ruta canónica (antes leía shim sin clase → FAIL)
- Añadido: `test_shared_profitability_shim_removed` (confirma que shared/profitability/ está eliminado)

## 7. Validaciones

```
Pre-eliminación:  2125 passed, 94 failed, 17 errors
Post-eliminación: 2127 passed, 93 failed, 17 errors  (+2 pass, -1 fail — guardrails corregidos)
```

Sin regresiones.
