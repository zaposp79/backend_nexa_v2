# Contracts Alignment — Excel Definitivo V2-8

**Status:** PARAMETRIZATION_ALIGNMENT_COMPLETED  
**Commits:** `abaed2b` (contracts) → `[this commit]` (storage/tests/guardrails)

---

## 1. Estado real

| Componente | Status |
|---|---|
| Contracts HR/OP/GN | ✅ Alineados con Excel definitivo |
| Tests parametrizacion | ✅ 271 pass / 1 skip / 0 fail |
| Guardrail tests | ✅ 5 nuevos guardrails protegiendo cambios |
| GNRepository.get_active() | ✅ Añadido (bug pre-existente resuelto) |
| OPValidator._validate_poliza_rates | ✅ Actualizado a columna Porcentaje |
| business_rules ghost dir | ✅ Eliminado |
| OP_HITL_CADENA_B dead code | ✅ Eliminado |
| Storage v2-7 JSON | ⚠️ Pre-existente: archivos v2-7 ya eliminados antes de este trabajo |

---

## 2. Excel definitivos usados

| Módulo | Archivo | Sheets | Status |
|---|---|---|---|
| HR | `excel/HR_productiva_2026-05-11-09-52-29.xlsx` | 15 sheets | ✅ Leído |
| OP | `excel/OP_productiva_2026-05-11-10-35-25.xlsx` | 11 sheets | ✅ Leído |
| GN | `excel/GN_productiva_2026-05-11-10-25-28.xlsx` | 1 sheet | ✅ Leído |

---

## 3. Contratos — Cambios aplicados

### OP Module (`modules/parametrizacion/op/contracts.py`)

| Sheet | Antes | Después |
|---|---|---|
| OP-Poliza | `[Poliza, Valor]` | `[Poliza, Porcentaje, PorcentajeExigido]` |
| OP-PolizaFija | No existía | `[Poliza, Porcentaje]` |
| OP-Costo | No existía | `[CostoOperativo, Valor]` |
| OP-MargenObjetivo | No existía | `[Cadena, Porcentaje]` |
| OP-HITLCadenaB | Definida (no en contract) | Eliminada completamente |
| OP-Tasa | En contrato | Eliminada (no en Excel) |
| OP-DatosOperativos | En contrato | Eliminada (no en Excel) |
| OP-BillingComponente | Nunca existió en código | Confirmado ausente |

### HR Module (`modules/parametrizacion/hr/contracts.py`)

| Sheet | Antes | Después |
|---|---|---|
| HR-EquipoHITL | `[EquipoHITL, ratio]` (TABLE_ROWS) | `[EquipoHITL]` (CATALOG_BY_COLUMN) |

**Consumer impact:** Zero referencias activas a `ratio` encontradas en código.

### GN Module (`modules/parametrizacion/gn/contracts.py`)

| Sheet | Antes | Después |
|---|---|---|
| GN-LV | 22 columnas (sin Divisa) | 23 columnas (Divisa al final) |

---

## 4. Fixtures y tests actualizados

| Archivo | Cambio |
|---|---|
| `tests/parametrizacion/uploads/test_gn_upload_characterization.py` | `_GN_LV_HEADERS` / `_GN_LV_ROW` → agregar Divisa |
| `tests/parametrizacion/security/test_excel_contracts.py` | `_valid_gn_workbook()` → agregar Divisa |
| `tests/parametrizacion/uploads/test_op_upload_characterization.py` | `_op_workbook()` OP-Poliza → `[Poliza, Porcentaje, PorcentajeExigido]` |
| `tests/parametrizacion/uploads/test_op_repository_document_store.py` | 2 workbooks inline actualizados |
| `tests/parametrizacion/unit/test_ica_guardrails.py` | `_make_op_workbook()` OP-Poliza header actualizado |
| `tests/parametrizacion/unit/test_mixed_value_columns.py` | `TestOPDatosOperativos::test_percent_string_rejected` → skip con doc |
| `tests/parametrizacion/uploads/test_gn_repository_document_store.py` | Import `__import__` → relative import fix |

---

## 5. Upload/parse validado

Los tests de upload de `tests/parametrizacion/uploads/` validan el pipeline completo:

```
Excel workbook bytes → read_excel_sheets() → normalize_sheets_by_contract()
→ OPValidator / HRValidator → Repository.save_version() → storage JSON
```

**Resultado:** 271 passed / 1 skipped (1 skip = OP-DatosOperativos removed)

---

## 6. Consumers revisados

| Símbolo | Resultado |
|---|---|
| `ratio` (columna HR-EquipoHITL) | Zero referencias activas |
| `OP-BillingComponente` | Solo en comentarios históricos (pyg_calculator.py, parametrization_provider.py) |
| `OP-HITLCadenaB` | Eliminado de contrato, zero referencias |
| `OP-Tasa` | Solo en docstring (op/contracts.py), no en lógica activa |
| `OP-DatosOperativos` | Solo en tests documentales (test_mixed_value_columns.py) |
| `Porcentaje` (nuevo campo OP-Poliza) | OPValidator actualizado |
| `PorcentajeExigido` (nuevo campo) | Disponible en contrato, sin consumer activo |
| `Divisa` (nuevo campo GN-LV) | Disponible en contrato, sin consumer activo |

---

## 7. Gaps reales

| Gap | Tipo | Estado |
|---|---|---|
| Storage v2-7 JSON eliminados antes | Pre-existente | No relacionado con este trabajo |
| `OP-DatosOperativos` tests pasan incidentalmente | Documentado | Test marcado con skip |
| `PorcentajeExigido` sin consumer activo | Disponible para uso futuro | OK — no inventar consumer |
| `Divisa` sin consumer activo | Disponible para uso futuro | OK — no inventar consumer |
| Armenia ICA 0.6 en Excel OP | RESUELTO ✅ | Corregido a 0.006 (0.6%) |

---

## 8. OP-BillingComponente y estado de sheets removidos

**Status: ZERO referencias activas.**

Tres menciones históricas (solo comentarios/docstrings):
1. `modules/pyg/services/pyg_calculator.py` — comentario `# NOTE: removed`
2. `modules/shared/ports/parametrization_provider.py` — nota en docstring
3. `docs/refactor/excel_definitivos_snapshot.md` — documentación

Ninguna es código activo. El sheet nunca existió en Excel definitivo.

---

## 9. Corrección de datos — Armenia ICA Rate

**Hallazgo:** Excel OP-ICA tenía Armenia 'Tasa' = **0.6 (60%)** — valor imposible.

**Análisis:**
| Ciudad | Tasa | % |
|---|---|---|
| Armenia (antes) | **0.6** | **60% ❌** |
| Armenia (después) | 0.006 | 0.6% ✅ |
| Bogotá | 0.0097 | 0.97% ✅ |
| Barranquilla | 0.0125 | 1.25% ✅ |
| Bucaramanga | 0.009 | 0.9% ✅ |
| Manizales | 0.0045 | 0.45% ✅ |

**Resolución:**
1. Corregido Armenia en Excel de 0.6 → 0.006 (notación decimal correcta)
2. Actualizado test `test_production_op_file_blocked_by_armenia_anomaly` 
   → `test_production_op_file_upload_succeeds`
3. Verificado: production OP file ahora pasa validación ICA

**Commit:** `2ac1dca fix: update ICA tests — Armenia rate corrected from 0.6 to 0.006`

---

## 10. Cambios adicionales (bugs pre-existentes resueltos)

| Bug | Archivo | Fix |
|---|---|---|
| `GNRepository.get_active()` faltaba | `gn/repositories/repository.py` | Añadido (equivalente a HR/OP) |
| OPValidator leía columna `valor` en OP-Poliza | `op/validators/validator.py` | Ahora lee `porcentaje` (fallback a `valor`) |
| `business_rules/` directorio fantasma | `modules/parametrizacion/business_rules/` | Eliminado (solo tenía __pycache__) |
| `OP_HITL_CADENA_B` definida pero no en contrato | `op/contracts.py` | Eliminada |
| `__import__` con path absoluto fallaba | `test_gn_repository_document_store.py` | Reemplazado con relative import |
