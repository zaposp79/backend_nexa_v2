# BUSINESS_RULES_CANONICAL_MIGRATION

**Fecha:** 2026-06-09  
**Status:** ✅ COMPLETE  
**Branch:** refactor/modular-pure

---

## Objetivo

Mover las reglas de negocio runtime faltantes desde `storage/parametrization/business_rules/v2-7.json` a la ubicación canónica `modules/shared/config/business_rules/`, y eliminar todas las referencias runtime a la carpeta de storage.

---

## Cambios

| Archivo | Acción | Detalle |
|---|---|---|
| `modules/shared/config/business_rules/politicas_comerciales.yaml` | **CREADO** | 5 políticas comerciales + margen_objetivo cadenas |
| `modules/parametrizacion/mixins/provider_business_rules.py` | **REEMPLAZADO** | Lee de YAML canónico via `load_business_rules_cached`, sin `_br_repo` |
| `modules/parametrizacion/services/provider.py` | **MODIFICADO** | Removido parámetro `br_repo` de `build()` |
| `modules/panel/services/panel_service.py` | **MODIFICADO** | Removida inyección `br_service`; lee YAML directamente |
| `modules/parametrizacion/mixins/provider_fin_op.py` | **MODIFICADO** | Removido import y atributo `BUSINESS_RULES_DIR` no usado |
| `db/container.py` | **MODIFICADO** | Removidos `BusinessRulesRepository`, `BusinessRulesQueryService`, campos `business_rules_repository`/`business_rules_service` |
| `storage/parametrization/business_rules/` | **ELIMINADO** | `v2-7.json`, `2026-01.json`, `versions.json` |
| `tests/unit/test_business_rules_canonical_migration.py` | **CREADO** | 6 guardrails |

---

## Flujo anterior vs nuevo

**Antes:**
```
ParametrizationProvider.build(br_repo=BusinessRulesRepository(store))
  → _br_repo.get_active_data()
  → storage/parametrization/business_rules/versions.json
  → storage/parametrization/business_rules/v2-7.json
  → riesgo_config + reglas_negocio.politicas_comerciales
```

**Después:**
```
ParametrizationProvider.build()
  → get_politicas_comerciales(): load_business_rules_cached("politicas_comerciales")
  → get_riesgo_config():         load_business_rules_cached("riesgo")
  → modules/shared/config/business_rules/{politicas_comerciales,riesgo}.yaml
```

---

## YAML canónico creado

`modules/shared/config/business_rules/politicas_comerciales.yaml`:

```yaml
politicas_comerciales:
  - {nombre: contingencia_operativa, min: 0.025, max: 0.12}
  - {nombre: contingencia_comercial, min: 0.04,  max: 0.07}
  - {nombre: markup,                 min: 0.02,  max: 0.08}
  - {nombre: descuento,              min: 0.0,   max: 0.15}
  - {nombre: imprevistos,            min: 0.0,   max: 1.0}

margen_objetivo:
  cadena_a: 0.15
  cadena_b: 0.12
  cadena_c: 0.10
```

---

## Código muerto remanente (no eliminado)

`BusinessRulesRepository` y `BusinessRulesQueryService` permanecen en disco como código muerto — aún importados en tests de arquitectura. No eliminados para evitar romper esos tests sin auditoría.

---

## Tests

```
tests/golden/                                         58/58 PASS ✅
tests/refactor/test_baseline_formula_snapshot_v1.py   6/6  PASS ✅
tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py  4/4 PASS ✅
tests/unit/test_business_rules_canonical_migration.py 6/6  PASS ✅
────────────────────────────────────────────────────
Total: 74 PASS. Zero pricing drift.
```

---

## Riesgo

🟢 **ZERO** — Mismos valores, mismo output shape. Sin cambios de fórmulas ni cálculos.

---

## Siguiente paso

Ninguno requerido. Opcional: eliminar `BusinessRulesRepository` y `BusinessRulesQueryService` después de auditar y migrar los tests que los importan.
