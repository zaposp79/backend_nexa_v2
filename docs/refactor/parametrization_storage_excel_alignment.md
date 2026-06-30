# Parametrization Storage ↔ Excel Alignment Report

**Branch:** `refactor/modular-pure`  
**Date:** 2026-06-10  
**Scope:** OP parametrization alignment audit — removal of fictitious `OP-BillingComponente`

---

## Veredicto: `OP_PARAMETRIZATION_ALIGNED`

---

## 1. Problema detectado

El commit `006d559` (Stage 2 Target 1 — P&G billing indexation) introdujo un artefacto
ficticio `OP-BillingComponente` en 6 archivos del motor. La hoja **no existe** en ningún
archivo Excel OP real.

**Hoja ficticia:** `OP-BillingComponente`  
**Hoja real en Excel:** `OP-Componente`

---

## 2. Auditoría de Excel real

**Archivo auditado:** `excel/OP_productiva_2026-05-11-10-35-25.xlsx`

| Hoja Excel real | Columnas | Notas |
|---|---|---|
| `OP-Componente` | Componente, Año, Valor | IPC=0.0527, SMLV variable por año |
| `OP-ComponenteAcumulado` | Componente, Año, Valor | Factor acumulado multi-año |
| `OP-Poliza` | Poliza, Valor, ... | GMF + pólizas de seguros |
| `OP-ICA` | Ciudad, ICA, Valor | 100 filas (ciudades) |
| `OP-Config` | Clave, Valor | `tasa_financiacion_mensual` |
| `OP-HardSoft` | HardwareSoftware, Valor, CantidadMes, Tipo | 7 filas |
| `OP-OpexFijo` | OpexItem, Valor | 6 filas |

**`OP-BillingComponente`:** `SIN_FUENTE_PRIMARIA` — no existe en ningún archivo Excel OP.

---

## 3. Valores reales en `storage/parametrization/v2-7/op.json` (hoja `componente`)

Fuente: `OP-Componente` del Excel V2-7

| Componente | Año | Valor |
|---|---|---|
| IPC | 2025–2030 | 0.0527 (constante) |
| SMLV | 2025 | 0.12 |
| SMLV | 2026 | 0.2378 |
| SMLV | 2027–2030 | 0.12 |

Estos valores son la **fuente canónica** para indexación salarial en el motor NEXA.

---

## 4. Archivos modificados (commit `b8587e5`)

| Archivo | Cambio |
|---|---|
| `modules/parametrizacion/op/contracts.py` | Eliminado `OP_BILLING_COMPONENTE` SheetContract y su entrada en `OP_CONTRACT.sheets[]` |
| `modules/parametrizacion/repositories/financial_parametrization_repository.py` | Eliminado método `get_billing_component_rate()` |
| `modules/shared/ports/parametrization_provider.py` | Eliminado `get_billing_indexacion_rate()` del Protocol `IParametrizationProvider` |
| `modules/parametrizacion/mixins/provider_fin_op.py` | Eliminada implementación `get_billing_indexacion_rate()` del mixin |
| `modules/parametrizacion/shared/repositories/frozen_parametrization_adapter.py` | Eliminada delegación `get_billing_indexacion_rate()` |
| `modules/pyg/services/pyg_calculator.py` | Eliminado bloque de billing indexation en `calcular_mes()` (17 líneas) que aplicaba `(1 + billing_rate)` a `ingreso_bruto` |

---

## 5. Artefactos corregidos

| Artefacto | Estado |
|---|---|
| `storage/parametrization/v2-7/op.json` | Restaurado desde git — contiene `componente`, `componenteacumulado`, `poliza`, `ica`, `config` |
| `storage/parametrization/{hr,gn,op}/versions.json` | Corrección: añadido `"path": "../v2-7/{hr,gn,op}.json"` para que `VersionSummary.path` resuelva el fallback correcto |
| `tests/refactor/baseline_formula_snapshot_cadena_c_v1.json` | Regenerado con v2-7 activo (M1 ingreso_bruto: 405,232,440.96) |

---

## 6. Impacto en cálculo

Con `OP-BillingComponente` activo (ficticio):
- `ingreso_bruto` M13 = **479,851,110.90** (con billing indexation aplicada)

Con `OP-BillingComponente` eliminado (correcto):
- `ingreso_bruto` M13 = **454,629,498.37** (sin billing indexation ficticia)

La indexación salarial real sigue funcionando a través de `get_componente_indexacion()`
→ `OP-Componente` → IPC=5.27% / SMLV variable.

---

## 7. Resultado de tests

| Suite | Resultado |
|---|---|
| `tests/golden/` (63 tests) | ✅ 63/63 pass |
| `tests/refactor/` — cadena_c (42 tests) | ✅ 42/42 pass |
| `tests/refactor/` — v0/v1 snapshots | ⚠ Pre-existing drift (no relacionado con este cambio) |

---

## 8. Contratos no modificados

Los siguientes contratos permanecen inalterados (sin breaking changes):

- `IParametrizationProvider` — Protocol público en `modules/shared/ports/`
- DTOs de entrada (`PanelDeControl`, `CondicionesCadena{A,B,C}`)
- Respuestas API (`ApiResponse`, serializers)
- `request/request.json` — sin modificaciones
- Fixtures golden existentes
