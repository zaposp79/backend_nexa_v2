# SUPPORT FTE — Matriz de decisión del gap dominante (V2-8)

Fecha: 2026-06-11 · Modo: **READ-ONLY diagnóstico** (sin fix de motor, sin re-baseline, sin tocar request.json).
Commit base: `6ce1eb7` (`CTS_EXAM_APPLIED` / `CTS_CRUCERO_BLOCKED`).
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`.
Provider de test: `tests/refactor/_v28_deal_provider.py` (active HR + W-override 20 roles staff + SENA/Incl + exam patch).
Deal: SAC / METROCUADRADO COM SAS / Grupo Aval — 24m, denominador Panel!W31 = 221,000 tx/mes.

CTS-001 actual: backend **6,155.30** vs Excel **6,224.58** → delta **-69.27 COP/tx (1.113%)**. PARTIAL_BEST_IMPROVED.

---

## ⚠️ REFUTACIÓN de la auditoría previa ("Excel soporte ≈ 71, backend ≈ 61.4, gap -9.6 FTE")

La hipótesis previa (`cts_residual_structural_audit_v28.md` §3 y `cts_exam_crucero_audit_v28.md` §5)
afirmaba que Excel tiene **~71 FTE de soporte vs backend 61.4**, con un gap de **dotación (FTE)** de
~10 FTE / ~-138 COP/tx. **Esa cifra es FALSA.** Provenía de leer agregados de costo en la sección
"Visión por perfiles / por Canal" de `Nomina Loaded` (que mezcla COP, no headcount) y dio valores
imposibles (SENA HC=308), por lo que nunca fue una cifra firme.

La extracción limpia del **bloque FTE por rol de Excel** (`Condiciones Cadena A`!E77:G100, donde
E/F/G = escenarios SAC / WhatsApp / Crecimiento) da:

```
Excel  soporte total (excl. agentes + validador) = 59.5526 FTE
Backend soporte total (3 bloques)                = 61.4452 FTE
delta = backend - excel = +1.8925 FTE   →  BACKEND TIENE MÁS FTE, NO MENOS
```

**El gap NO es "backend infra-dotado de soporte".** El total de FTE es prácticamente equivalente
(backend +1.9). Lo que difiere es la **composición/mezcla por rol** y la **base del numerador**.

---

## 1. FTE soporte Excel — trazabilidad por perfil (`Condiciones Cadena A`!E77:G100)

Fórmula Excel (verificada en celdas E78/E80/E84/E87): 
`FTE_rol = IF(activo, (FTE_agentes + cargos_adicionales) / ratio_rol [× Panel!C20 si rotación], 0)`
donde numerador = `E9 (FTE agentes) + E26 (FTEs cargos adicionales) + E30 + E34`.

| Perfil soporte | Celda Excel | FTE Excel (E+F+G) | Ratio (E122 etc.) | Activo Excel | Observación |
|---|---|---|---|---|---|
| Director de cuentas | E77:G77 | 0.3725 | 750 | sí | base expandida |
| Director de Performance | E78:G78 | 1.1600 | 1200 | sí | piso G78=1.0 (Crecimiento) |
| Jefe Comercial Regional | E79:G79 | **0.0000** | 800 | **NO (C79=False)** | desactivado en Excel |
| Analista profesional AFAC | E80:G80 | **0.0000** | 400 | **NO (C80=False)** | desactivado en Excel |
| Lider de Entrenamiento | E81:G81 | 0.2794 | 1000 | sí | |
| Lider de Experiencia | E82:G82 | 0.2794 | 1000 | sí | |
| Lider de Planeación Op. | E83:G83 | 0.2794 | 1000 | sí | |
| Jefe de Operación | E84:G84 | 1.6932 | 165 | sí | |
| Works force | E85:G85 | 0.9313 | — | sí | |
| Reporting | E86:G86 | 0.9313 | — | sí | |
| GTR | E87:G87 | **0.0000** | 120 | **NO (C87=False)** | desactivado en Excel |
| Analista Prof. Selección (Inicial) | E88:G88 | 5.0797 | 55 | sí | |
| Analista 1 Reclutamiento (Inicial) | E89:G89 | 2.5399 | 110 | sí | |
| Analista Prof. Selección (Rotación) | E90:G90 | 0.4140 | 55 | sí | ×Panel!C20 (rotación) |
| Analista 1 Reclutamiento (Rotación) | E91:G91 | 0.2070 | 110 | sí | ×Panel!C20 (rotación) |
| Analista 2 Service Desk | E92:G92 | 0.7551 | 370 | sí | |
| Formadores | E93:G93 | 3.9912 | 70 | sí | |
| Monitor de Calidad | E94:G94 | 3.9912 | 70 | sí | |
| **Supervisor** | E95:G95 | **16.3692** | 20 | sí | **SAC E95=9.5 (override/base ampliada)** |
| Aprendiz SENA | E98:G98 | 15.9329 | 20 | sí | fórmula especial |
| Inclusión | E99:G99 | 3.3459 | 100 | sí | fórmula especial |
| Especialista de Proyectos | E100:G100 | 1.0000 | — | sí | piso 1.0 |
| **TOTAL soporte** | | **59.5526** | | | |

Base del numerador (CCA por escenario): `E9 FTE=130/50/80` (agentes) **+** `E26 "FTEs cargos
adicionales"=12 / 0 / 7.3846`. Crecimiento verificado: `(80+7.3846)/20 = 4.369 = G95` ✔.

---

## 2. FTE soporte backend — trazabilidad (`context_builder_perfiles_soporte_mixin.py`)

Fórmula backend (verificada): `FTE_rol = fte_agentes / ratio [× pct_rotacion si rotación]`, computada
**por cada perfil base** (SAC=130, WhatsApp=50, Crecimiento=80) y sumada. Numerador = **solo
`fte_agentes`** (NO incluye `cargos_adicionales`). Ratios desde `provider.get_ratios_staff("SAC")`
(fuente: HR-Ratios parametrización; **coinciden** con Excel CCA: supervisor=20, GTR=120, etc.).

| Perfil soporte | FTE backend (3 bloques) | Fuente backend | Activo backend | Δ vs Excel |
|---|---|---|---|---|
| Aprendiz SENA | 15.1554 | SENACalculator + ratio 20 | sí | -0.777 |
| Supervisor | **13.0000** | 130/20 + 50/20 + 80/20 | sí | **-3.369** |
| Analista Prof. Selección (Inicial) | 4.7273 | ratio 55 | sí | -0.352 |
| Analista Prof. Selección (Rotación) | 4.7273 | ratio 55 | sí | **+4.313** (¿rotación no aplicada?) |
| Formadores | 3.7143 | ratio 70 | sí | -0.277 |
| Monitor de Calidad | 3.7143 | ratio 70 | sí | -0.277 |
| Inclusión | 3.1826 | InclusionCalculator | sí | -0.163 |
| Analista 1 Reclutamiento (Inicial) | 2.3636 | ratio 110 | sí | -0.176 |
| Analista 1 Reclutamiento (Rotación) | 2.3636 | ratio 110 | sí | **+2.157** (¿rotación no aplicada?) |
| GTR | **2.1667** | ratio 120 | **sí** | **+2.167** (Excel desactivado) |
| Jefe de Operación | 1.5758 | ratio 165 | sí | -0.117 |
| Works force | 0.8667 | — | sí | -0.065 |
| Reporting | 0.8667 | — | sí | -0.065 |
| Analista 2 Service Desk | 0.7027 | ratio 370 | sí | -0.052 |
| Analista profesional AFAC | **0.6500** | ratio 400 | **sí** | **+0.650** (Excel desactivado) |
| Director de cuentas | 0.3467 | ratio 750 | sí | -0.026 |
| Jefe Comercial Regional | **0.3250** | ratio 800 | **sí** | **+0.325** (Excel desactivado) |
| Lider Entrenamiento/Exp/Plan | 0.2600 c/u | ratio 1000 | sí | -0.019 c/u |
| Director de Performance | **0.2167** | ratio 1200 | sí | **-0.943** (Excel piso 1.0) |
| **TOTAL soporte** | **61.4452** | | | **+1.8925** |

---

## 3. Causa raíz del gap de COSTO soporte (no de conteo)

El gap de **costo** payroll soporte (`Vision CTS`: backend 1,043.47 vs Excel 1,215.85 ≈ **-172 COP/tx**,
Excel más caro) **no se explica por menos FTE** (backend tiene +1.89 FTE total). Se explica por la
**mezcla**: Excel concentra FTE en el rol **caro** (Supervisor 16.37 vs backend 13.0, **-3.37 FTE**),
mientras backend reparte FTE en roles **baratos** que Excel desactiva (GTR/JCR/AFAC, +3.14 FTE backend).

Dos mecanismos verificados:

1. **Base del numerador (FORMULA, modules/)** — Excel: `(FTE_agentes + cargos_adicionales)/ratio`;
   backend: `fte_agentes/ratio`. `cargos_adicionales` (CCA!E26 = 12 SAC / 7.38 Crecimiento) **no se
   suma** al numerador de soporte en backend. Impacto dominante en Supervisor (ratio 20, el más
   sensible): backend 13.0 vs Excel 16.37 ≈ **-3.37 FTE × ~4.5M cargado ≈ -68 COP/tx**.

2. **Activación de perfiles (MAPPING, request/staff_config)** — Excel desactiva (C-flag=False) GTR,
   Jefe Comercial Regional y AFAC; backend los mantiene activos (+3.14 FTE backend, roles baratos).
   Efecto neto pequeño en costo, pero infla el conteo backend y enmascara el déficit de Supervisor.

3. **(a investigar) Rotación** — backend "Analista … (Rotación)" tiene **MÁS** FTE que Excel
   (+4.31, +2.16): Excel aplica `×Panel!C20` (factor rotación) al numerador y backend aplicaría
   `×pct_rotacion` distinto, o no lo aplica. Sentido inverso al supervisor; requiere forensics modules/.

**Ratios: NO son la causa** (Excel CCA = backend `ratios_staff` exactos). **Dotación total: NO es la
causa** (backend +1.9 FTE). La causa es **estructura de fórmula del numerador + activación de perfiles**.

---

## 4. Matriz de decisión — clasificación por frente

| Frente | Δ COP/tx | Fuente del gap | Fix sin modules | Requiere request | Requiere modules | Riesgo | Recomendación / Estado |
|---|---|---|---|---|---|---|---|
| **Support FTE (Supervisor / base numerador)** | ≈ -68 (dominante) | Excel suma `cargos_adicionales` (CCA!E26) al numerador; backend usa solo `fte_agentes` | **no** | no | **sí** (`context_builder_perfiles_soporte_mixin._construir_perfiles_soporte`) | alto | `SUPPORT_FTE_FORMULA_BUG` → **REQUIRES_MODULE_SCOPE** |
| **Support FTE (activación GTR/JCR/AFAC)** | ≈ +pequeño (offset) | Excel C-flags=False; backend activa | parcial (staff_config) | sí (staff_config `activo` en request) | no | medio | `SUPPORT_FTE_PROFILE_MAPPING_MISMATCH` → **REQUIRES_REQUEST_SCOPE** |
| **Support FTE (rotación analistas)** | dirección inversa | `×Panel!C20` vs `×pct_rotacion` backend | no | no | sí (forensics) | medio | `SUPPORT_FTE_RAMP_MISMATCH` (a confirmar) → REQUIRES_MODULE_SCOPE |
| **Crucero** | -10.63 | `incluye_crucero` ausente en request.json (flag), **tarifa SÍ existe = 8408** | no (flag per-perfil, no inyectable vía HR/GN/OP) | **sí** (`incluye_crucero:true` en perfiles) | no | medio | `CTS_CRUCERO_INPUT_DECISION_REQUIRED` |
| **OPEX no-payroll** | +71.95 | `no_payroll_mensual` de perfiles (request.json) > Excel; backend OPEX 380.09 > Excel 308.14 | no | **sí** (request.json) | no | medio | `OPEX_NO_PAYROLL_INPUT_DECISION_REQUIRED` |

---

## 5. Crucero — decisión de input (CORRIGE doc previo)

El doc previo afirmaba `tarifa_crucero = 0.0 en request.json` → **FALSO**. `request.json`
`datos_operativos.crucero = 8408` mapea a `tarifa_crucero` (`user_input_loader.py:323`). El backend
devuelve crucero=0 **no por tarifa ausente sino porque `incluye_crucero` está ausente** de los
perfiles (default False); `_crucero` (`nomina.py:304`) retorna 0 si `not perfil.incluye_crucero`.

- **Path request**: `request.json` → cada perfil de `condiciones_cadena_a.perfiles[].incluye_crucero` (ausente → False). `tarifa_crucero` ya presente vía `datos_operativos.crucero=8408`.
- **Modelo**: backend = `8408 × FTE × indexación`; Excel = `Σ costos mensuales` (CCA!E152:G152 = 2,349,066/mes). `8408 × ~279 FTE ≈ 2.35M` → **el modelo es consistente**, solo falta activar el flag.
- **Provider/test hook**: `incluye_crucero` es per-perfil desde request.json (`user_input_builders_cadena_a.py:159`), **no** inyectable vía provider HR/GN/OP. Un hook de test podría mutar `perfil.incluye_crucero=True` tras `construir()`, pero es frágil y simula un cambio de deal.
- **Clasificación**: `CTS_CRUCERO_INPUT_DECISION_REQUIRED` — decisión de negocio: activar `incluye_crucero` en los perfiles de Cadena A (request.json). NO BLOCKED (la tarifa existe).

---

## 6. OPEX no-payroll — decisión de input

- Delta: **OPEX Fijo +71.95 COP/tx** (backend 380.09 > Excel 308.14). CAPEX +16.72, Costos Fijos -3.17.
- Componente principal: `no_payroll_mensual` de los perfiles (request.json) — backend lleva un OPEX
  mensual por perfil superior al que el Excel deriva para el deal SAC.
- Fuente: request.json (no provider, no modules). **Corrección confirmada**: el supuesto "CAPEX
  month-1 spike +119.72" fue un mis-diagnóstico; Excel también amortiza CAPEX (VCS!C47=103.04).
- Clasificación: `OPEX_NO_PAYROLL_INPUT_DECISION_REQUIRED` — REQUIRES_REQUEST_SCOPE (NO TOCAR request.json).

---

## 7. Veredicto (módulo) — CORREGIDO 2026-06-11 a `SUPPORT_FTE_BLOCKED_MISSING_SOURCE`

> **Actualización (sesión `SUPPORT_FTE_MODULE_FIX`, commit base `821e590`).** La clasificación previa
> `SUPPORT_FTE_REQUIRES_MODULE_SCOPE` asumía que el fix era puramente de fórmula en
> `context_builder_perfiles_soporte_mixin._construir_perfiles_soporte`. La verificación de Fase 1
> (fuente de `cargos_adicionales`) y Fase 2 (fórmula Excel exacta) demuestra que **el insumo no
> existe en el contrato de entrada del backend**, por lo que el fix de fórmula no es aplicable sin
> crear un campo público nuevo (prohibido en esta sesión) o hardcodear los valores en el motor
> (prohibido). Veredicto firme: **`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`**. Ver §8 y §9.

---

## 8. Fase 1 — Existencia de `cargos_adicionales` en backend (request / context / provider)

Búsqueda exhaustiva (`rg "fte_adicional|cargos_adicionales|fte_extra|adicional_fte|fte_cargos"` en
`modules tests request`): **0 coincidencias**. El único insumo de dotación en el contrato de entrada
es `PerfilCadenaAInput.fte` (número de agentes). Ni `StaffRolInput` (solo `nombre/activo/ratio_override`)
ni `CondicionesCadenaAInput` (solo `perfiles` + `staff_config`) ni `IParametrizationProvider` exponen
las FTE de "cargos adicionales".

| Concepto | Excel | Backend source | Existe | Observación |
|----------|-------|----------------|--------|-------------|
| FTE agentes SAC | `CCA!E9` = 130 | `PerfilCadenaAInput.fte` (perfil base SAC) | **sí** | se usa como numerador actual |
| FTE agentes WhatsApp | `CCA!F9` = 50 | `PerfilCadenaAInput.fte` (perfil WhatsApp) | **sí** | |
| FTE agentes Crecimiento | `CCA!G9` = 80 | `PerfilCadenaAInput.fte` (perfil Crecimiento) | **sí** | |
| cargos_adicionales SAC | `CCA!E26` = **12** (+E30=0, +E34=0) | — | **no** | sin campo equivalente |
| cargos_adicionales WhatsApp | `CCA!F26` = **0** (vacío) | — | **no** | (=0, no afecta) |
| cargos_adicionales Crecimiento | `CCA!G26` = **7.3846** (+G30=0, +G34=0) | — | **no** | sin campo equivalente |

**Conclusión Fase 1:** `cargos_adicionales` (CCA!E26/E30/E34) **no existe** en request/context/provider.
No se crea campo público nuevo en esta sesión → **`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`**.

---

## 9. Fase 2 — Fórmula Excel confirmada (`openpyxl`, `Condiciones Cadena A`)

Fórmula real (F95/G95, no override): `FTE_rol = IF(C=TRUE, (col9 + col26 + col30 + col34) / col122, 0)`
con variante `×Panel!C20` para roles de rotación. Verificado celda a celda:

| Perfil | Escenario | FTE agentes (r9) | Cargos adic. (r26+r30+r34) | Ratio (r122) | FTE Excel | Fórmula |
|--------|-----------|------------------|-----------------------------|--------------|-----------|---------|
| Supervisor | SAC (E) | 130 | 12 + 0 + 0 = 12 | 20 | **9.5** | `E95 = 9.5` (literal hardcodeado, **override manual**, no la fórmula → (130+12)/20=7.1) |
| Supervisor | WhatsApp (F) | 50 | 0 | 20 | **2.5** | `=(F9+F26+F30+F34)/F122 = 50/20` |
| Supervisor | Crecimiento (G) | 80 | 7.3846 | 20 | **4.3692** | `=(G9+G26+G30+G34)/G122 = 87.3846/20` |

Dos hallazgos críticos:
1. **`cargos_adicionales` es un insumo separado** del Excel (12 / 0 / 7.3846), no derivable de `fte`.
2. **SAC Supervisor `E95` está hardcodeado a `9.5`** (literal, no fórmula). El ejemplo "(130+60)/20=9.5"
   del diagnóstico previo es un *reverse-engineering* de ese literal, no la fórmula real (que daría 7.1).
   Reproducir 9.5 exigiría además un mecanismo de override manual per-celda inexistente en backend.

**Sin estos dos insumos (cargos_adicionales + override SAC), el fix de fórmula en el motor no replica Excel.
Agregar `+0` no cambia nada; cualquier otro valor sería un hardcode prohibido.**

---

## 10. Veredicto final

**`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`** — el gap dominante de soporte (~-68 COP/tx vía Supervisor) NO
es un simple `SUPPORT_FTE_FORMULA_BUG` corregible en `modules/`: el numerador correcto requiere
`cargos_adicionales` (CCA!E26/E30/E34) que **no existe en el contrato de entrada** (request/context/
provider), más un **override manual** SAC Supervisor (E95=9.5) sin mecanismo equivalente en backend.

Resolverlo exige una **decisión de contrato** (agregar un campo de entrada de dotación adicional por
escenario en `PerfilCadenaAInput`/`CondicionesCadenaAInput`), fuera del scope de esta sesión
(prohibido crear campo público nuevo / hardcodear). Reclasificado de `REQUIRES_MODULE_SCOPE` →
`BLOCKED_MISSING_SOURCE` + `REQUIRES_CONTRACT_DECISION`.

**No se modificó motor. No se regeneró baseline. Hardcoded nuevos en motor: 0. Gates: no ejecutados
(sin cambio de motor). Solo documentación.**

---

## 11. Checkpoint de decisión (2026-06-11) — request-scope antes que contrato

Auditados los frentes alternativos antes de abrir contrato para `cargos_adicionales`:

- **Crucero** → `CTS_CRUCERO_FIXABLE_WITH_REQUEST` (campo `incluye_crucero` **ya en contrato**, tarifa
  8408 ya en request.json). Cierra +10.63 COP/tx, mejora directa del headline.
- **OPEX no-payroll** → `OPEX_NO_PAYROLL_FIXABLE_WITH_REQUEST` (campo `opex_fijo.items` ya existe). Pero
  backend está **+71.95 SOBRE** Excel → corregir OPEX en aislamiento **empeora** CTS-001 (enmascara el
  déficit FTE). Reconciliar ítem-a-ítem antes de aislar el residual real de Support FTE.

**Decisión:** abrir contrato `cargos_adicionales` **NO ahora** →
`CONTRACT_CHANGE_CARGOS_ADICIONALES_DEFERRED`. Agotar primero request-scope (Crucero + OPEX), aislar el
residual FTE verdadero, y luego decidir el contrato. Detalle: `cts_001_decision_checkpoint_v28.md`.
