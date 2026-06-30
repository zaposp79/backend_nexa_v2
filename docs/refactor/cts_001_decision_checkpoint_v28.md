# CTS-001 — Decision Checkpoint (V2-8)

Fecha: 2026-06-11 · Rama: `refactor/modular-pure` · Modo: **READ-ONLY diagnóstico**
(sin tocar `modules/`, `request.json`, `storage/`, tests expected/providers; sin `make baseline`).
Commit base: `81e9b3c` (`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`).
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`.
Deal: SAC / METROCUADRADO COM SAS / Grupo Aval — 24m, denominador Panel!W31 = 221,000 tx/mes.

## Estado congelado

```
CTS-001 backend = 6,155.30 COP/tx   (post CTS_EXAM_APPLIED)
CTS-001 excel   = 6,224.58 COP/tx   (Vision CTS!C34)
delta           =   -69.27 COP/tx   (1.113%)   →  MAX_DELTA(0.000001) NO cumplido
CTS-001_FULL_MATCH = BLOCKED
Motivo            = cargos_adicionales sin fuente en contrato/context/provider
```

`CTS-001_FULL_MATCH` **NO se declara.** Estado: `PARTIAL_BEST` / `BLOCKED_MISSING_SOURCE`.

---

## 1. Matriz de frentes residuales

| Gap | Delta COP/tx | Fuente | Fix posible sin contrato nuevo | Estado |
|-----|--------------|--------|--------------------------------|--------|
| Support FTE (Supervisor / numerador) | ≈ -68 (dominante) | `cargos_adicionales` CCA!E26/E30/E34 (12/0/7.3846) — **ausente** del contrato | **no** | `BLOCKED_MISSING_SOURCE` |
| OPEX no-payroll (OPEX Fijo) | **+71.95** (backend SOBRE Excel) | `request.json` perfiles `opex_fijo.items[]` (campo existente) | **sí** | `OPEX_NO_PAYROLL_FIXABLE_WITH_REQUEST` |
| Crucero | ~~-10.63~~ **-0.74** residual | `incluye_crucero=true` **APLICADO** (2026-06-11) | **sí** | `CTS_CRUCERO_PARTIAL` |

---

## 2. Fase 2 — OPEX no-payroll

**Anchors Excel** (`Vision Cost To Serve`): OPEX Fijo `C46` = **308.1382**; Inversiones `C47` = 103.0436;
Costos Fijos x Estación `C48` = 351.0375; No Payroll total `C45` = 762.2192.

**Backend** (post estado actual, ref. `support_fte_input_decision_v28.md` §6): OPEX Fijo ≈ **380.09**
(+71.95), CAPEX ≈ 119.76 (+16.72), Costos Fijos ≈ 347.87 (-3.17).

**Origen backend del OPEX Fijo:** `request.json` → `condiciones_cadena_a.perfiles[].opex_fijo.items[]`
(p.ej. "Internet dedicado" 450,000 × 78, "Plataforma CCaaS" 180,000 × 78, …) → consumido por
`context_builder_perfiles_soporte_mixin._calcular_opex_ti_total` (filtra ítems TI, divide por
estaciones presenciales) → CTS `opex_fijo = avg(no_payroll.opex_ti)/denominador_cadena_a`
(`cost_to_serve_calculator.py:29`).

| Componente OPEX | Excel COP/tx | Backend COP/tx | Delta | Request/provider path | Requiere contrato nuevo | Recomendación |
|-----------------|--------------|----------------|-------|-----------------------|-------------------------|---------------|
| OPEX Fijo | 308.14 (C46) | ≈ 380.09 | **+71.95** | `request.json` perfiles `opex_fijo.items[]` (existe) | **no** | reconciliar ítems request vs Excel "No payroll" (R107) — request-scope |
| Inversiones (CAPEX) | 103.04 (C47) | ≈ 119.76 | +16.72 | `request.json` perfiles `inversiones[]` (existe) | no | reconciliación de plazos/precios — request-scope |
| Costos Fijos x Estación | 351.04 (C48) | ≈ 347.87 | -3.17 | `request.json` perfiles `costos_fijos_mensual` (existe) | no | menor; request-scope |

**Clasificación: `OPEX_NO_PAYROLL_FIXABLE_WITH_REQUEST`.** El insumo ya existe como campo aceptado
(`opex_fijo.items`); no requiere campo nuevo ni `modules/`. La fórmula backend es correcta; el delta es
**data-level** (los ítems OPEX del deal en `request.json` exceden la derivación per-estación del Excel
V2-8 para SAC). Falta una reconciliación ítem-a-ítem contra la hoja Excel "No payroll" para confirmar
cierre 100% vs residual de fórmula.

> **⚠️ Señal crítica:** OPEX Fijo backend está **POR ENCIMA** de Excel (+71.95). Como el total CTS-001
> backend está **por debajo** de Excel (-69.27), el sobre-OPEX está **enmascarando** el déficit de
> payroll de soporte (Support FTE). Corregir OPEX hacia abajo *en aislamiento* **empeoraría** el
> headline CTS-001 (de -69.27 a ≈ -141). No es una mejora independiente del headline.

---

## 3. Fase 3 — Crucero

**Anchor Excel:** `Vision CTS!C43` = **10.6293** COP/tx ← `Condiciones Cadena A`!E152:G152
(1,193,936 + 420,400 + 734,730 = 2,349,066 COP/mes).

**Ground truth (corrige docs previos):**
- `request.json` línea 13: `datos_operativos.crucero = 8408` → **SÍ presente** (no 0.0).
- `user_input_loader.py:323`: `"tarifa_crucero": float(ops.get("crucero", 0.0))` → `tarifa_crucero = 8408`.
- `incluye_crucero` **ya existe en el contrato público**: `modules/shared/contracts/api_v1/request/cadena_a.py:36`
  (`incluye_crucero: bool = False`), cableado vía `user_input_builders_cadena_a.py:159`
  (`bool(d.get("incluye_crucero", False))`) → `PerfilCadenaAInput.incluye_crucero` (`user_inputs.py:204`).
- `nomina.py:304-308`: `_crucero` retorna 0 si `not perfil.incluye_crucero`; de lo contrario
  `tarifa_crucero × perfil.fte × indexacion`.

**Por qué backend = 0:** los perfiles de `request.json` no declaran `incluye_crucero: true` (default
False). La tarifa (8408) ya está cargada. Consistencia del modelo: `8408 × ~279 FTE ≈ 2.35M/mes` ≈
Excel 2,349,066/mes → el modelo per-FTE replica el total Excel.

| Concepto Crucero | Excel | Backend | Path request/provider | Requiere contrato nuevo | Recomendación |
|------------------|-------|---------|-----------------------|-------------------------|---------------|
| Crucero COP/tx | 10.6293 (C43) | 0.0 | — (depende del flag) | **no** | activar flag en perfiles |
| tarifa_crucero | 2,349,066/mes total → ~8408/FTE | 8408 (cargada) | `datos_operativos.crucero` (existe) | no | ya presente |
| incluye_crucero | TRUE (deal) | False (default) | `condiciones_cadena_a.perfiles[].incluye_crucero` (existe en contrato) | **no** | `true` en perfiles Cadena A |

**Clasificación: `CTS_CRUCERO_FIXABLE_WITH_REQUEST`.** No requiere campo nuevo (el contrato ya expone
`incluye_crucero`) ni `modules/`. Activar el flag en los perfiles de `request.json` cerraría +10.63
COP/tx y **reduciría** el déficit CTS-001 (mejora directa del headline).

> Corrección de doc: el comentario del golden `test_cts_exam_crucero_v28.py` ("tarifa_crucero = 0.0 in
> request.json (not set)") y `cts_exam_crucero_audit_v28.md` §2 (`CTS_CRUCERO_REQUIRES_INPUT_SCOPE` por
> tarifa ausente) están **desactualizados**: la tarifa SÍ existe (8408); lo que falta es el flag
> `incluye_crucero`, ya soportado por el contrato. No se modifican tests/providers en esta sesión.

---

## 4. Fase 4 — Matriz de decisión final

| Frente | Delta COP/tx | Tipo de cambio | Requiere contrato nuevo | Requiere modules | Riesgo | Recomendación |
|--------|--------------|----------------|--------------------------|------------------|--------|---------------|
| Support FTE / cargos_adicionales | ≈ -68 (dominante, raíz) | contrato/context | **sí** | no (solo fórmula, pero sin insumo) | alto | **DEFERRED** — abrir contrato solo tras agotar request-scope y aislar residual |
| OPEX no-payroll | +71.95 (signo opuesto) | request/input (data) | no | no | medio | reconciliar request vs Excel; **no corregir en aislamiento** (enmascara FTE) |
| Crucero | -10.63 | request/input (flag) | no | no | bajo | activar `incluye_crucero` en perfiles (request-scope) — mejora directa |

### ¿Conviene abrir contrato ahora o agotar primero request-scope existente?

**Agotar primero request-scope: SÍ. Abrir contrato ahora: NO (DEFERRED).**

Razonamiento:
1. **Crucero** y **OPEX** son corregibles con **campos ya existentes** (`incluye_crucero`,
   `opex_fijo.items`) sin tocar el contrato público ni `modules/`. Solo `cargos_adicionales` (Support
   FTE) exige un campo nuevo.
2. Los frentes request-scope **interactúan con signo opuesto** sobre el headline CTS-001:
   Crucero (+10.63 mejora) y OPEX (+71.95 de sobre-costo que enmascara el déficit FTE). Abrir contrato
   para `cargos_adicionales` **antes** de reconciliar OPEX produciría un número engañoso (el déficit
   FTE está parcialmente compensado por el sobre-OPEX). El residual real de Support FTE solo se aísla
   **después** de corregir OPEX a paridad.
3. Secuencia recomendada (en sesiones de request-scope, fuera de esta):
   a. Activar `incluye_crucero` en perfiles Cadena A (request.json) → +10.63, cierra Crucero.
   b. Reconciliar `opex_fijo.items` / `inversiones` vs hoja Excel "No payroll" → aísla el residual
      OPEX real (data-level) y desenmascara el déficit FTE verdadero.
   c. Con el residual de Support FTE aislado y cuantificado, **entonces** decidir el cambio de contrato
      `cargos_adicionales` (`CONTRACT_CHANGE_CARGOS_ADICIONALES_REQUIRED`).

Estado de esta sesión: **`CONTRACT_CHANGE_CARGOS_ADICIONALES_DEFERRED`**.

---

## 5. Veredicto

**`CTS_INPUT_DECISION_CHECKPOINT_COMPLETED`** ·
**`OPEX_NO_PAYROLL_INPUT_DECISION_READY`** (request-scope, no contrato) ·
**`CTS_CRUCERO_INPUT_DECISION_READY`** (request-scope, no contrato) ·
**`CONTRACT_CHANGE_CARGOS_ADICIONALES_DEFERRED`**.

No se modificó motor. No se tocó request.json/storage. No se regeneró baseline.
Hardcoded nuevos en motor: 0. Gates: CTS golden 4/4 PASS, validate-excel-v28 6/6 PASS, make all PASS.
