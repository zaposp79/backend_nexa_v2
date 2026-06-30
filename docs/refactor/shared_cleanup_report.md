# Shared Models Cleanup Report

**Fase:** 2D (CTS + PyG legacy DTO removal)
**Fecha:** 2026-06-10
**Branch:** refactor/modular-pure

---

## Resumen

Eliminación de archivos DTO legacy de `modules/shared/models/` cuyas clases ya habían sido migradas a sus bounded contexts canónicos en sesiones anteriores (Fase 2B).

---

## Archivos eliminados

| Archivo legacy | Motivo | Canonical location |
|---|---|---|
| `modules/shared/models/visions_cts.py` | Duplicado post-migración; 0 consumers directos | `modules/vision_cost_to_serve/dto/models.py` |
| `modules/shared/models/visions_pyg.py` | Duplicado post-migración; 0 consumers directos | `modules/pyg/dto/models.py` |

---

## Compatibilidad preservada

`modules/shared/models/visions.py` — adapter de re-export backward-compat — sigue exponiendo:
- `ResultadoCostToServe` ← `vision_cost_to_serve.dto.models`
- `VisionPyGRow`, `VisionPyGRowDetalle`, `ResumenEjecutivoPyG`, `VisionPyG` ← `pyg.dto.models`

No se cambia ningún contrato público. Consumers de `visions.py` no requieren cambios de imports.

---

## Guardrails activos (test_shared_guardrails.py)

| Test | Protege |
|---|---|
| `test_visions_cts_duplicate_removed` | `visions_cts.py` no re-emerge |
| `test_visions_pyg_duplicate_removed` | `visions_pyg.py` no re-emerge |
| `test_cts_canonical_location_exists` | canonical CTS location intacta |
| `test_pyg_dto_canonical_location_exists` | canonical PyG location intacta |
| `test_visions_adapter_re_exports_cts_symbol` | adapter exporta `ResultadoCostToServe` |
| `test_visions_adapter_re_exports_pyg_symbol` | adapter exporta `VisionPyG` |
| `TestSharedInvariantNoBusinessDomainImports` | `shared/` no importa desde módulos de dominio |

---

## Validación

```
32 passed (guardrails)
158 passed (refactor + golden)
0 regresiones
```

---

## Estado diferido

Los siguientes archivos quedan en `shared/models/` pendientes de sesiones dedicadas:

| Archivo | Estado | Motivo diferido |
|---|---|---|
| `panel.py` | DEFER | API-facing, PricingRequest cross-consumed |
| `results.py` | DEFER | PricingResult serializado, 31 consumidores |
| `visions_tarifas.py` | DEFER | 5 clases cross-cutting con stability contracts (Fase 2C) |
| `visions_imprimible.py` | DEFER | VisionImprimible aggregate raíz, API-facing |
| `visions.py` | KEEP_TEMPORARY_ADAPTER | Re-exporter; target Fase 2E/2F |
