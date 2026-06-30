# Contract Design — `cargos_adicionales` (V2-8)

> **⮕ ACTUALIZACIÓN 2026-06-12 — `CONTRACT_CHANGE_CARGOS_ADICIONALES_APPLIED`.** El diseño de este
> documento (Alternativa A) fue **implementado**. Resumen:
> - Campo `cargos_adicionales: float = Field(default=0.0, ge=0.0)` en `PerfilCadenaAV1`; espejo en
>   `PerfilCadenaAInput` (DTO) y `PerfilCadenaA` (dominio). Builder `_perfil_a`/`_construir_perfil_a` lo propagan.
> - Fórmula: `fte_base_soporte = fte + cargos_adicionales` SOLO en el loop de soporte regular
>   (`context_builder_perfiles_soporte_mixin.py`). `fte_base` (Especialista/salario agentes) intacto → sin doble conteo.
> - Request V2-8: SAC=12, Crecimiento=7.384615, WhatsApp=0 (default).
> - **CTS-001: -128.4328 → -61.3335 COP/tx (+67.10, 0.985%).** Residual = E95 override DIFERIDO (≈-49) +
>   cap/crucero/exám no cableados (-3.84) + estructural (~-8.5). Supervisor SAC = 7.1 = (130+12)/20 (NO 9.5).
> - **E95=9.5 override per-rol: DIFERIDO** (`E95_OVERRIDE_DEFERRED`). Hardcodes nuevos en motor: 0.
> - Gates: support FTE golden 6/6 · CTS 2/2 · PyG 7/7 (anchors backend refrescados) · validate-excel-v28 6/6 ·
>   make all baseline match. Detalle: `cts_001_v28_evidence.md`.

Fecha: 2026-06-12 · Rama: `refactor/modular-pure` · Modo: **DISEÑO READ-ONLY**
(sin tocar `modules/`, `request/request.json`, `storage/`, contratos, tests, serializers, API pública; sin `make baseline`; sin aplicar fix).
Commit base: `91fe321` (`map Vision CTS formulas to backend components`).
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`, hoja **`Condiciones Cadena A`**.
Deal: SAC / METROCUADRADO COM SAS / Grupo Aval — 24m. Denominador Cadena A: Panel!W31 = 221,000 tx/mes.

> **Objetivo único:** decidir **cómo representar en backend** el gap dominante de CTS-001 —
> `cargos_adicionales` / soporte FTE / override per-rol — **sin implementarlo**. Este documento es
> una decisión de **contrato/API** con riesgo de breaking change y doble conteo. No produce código de motor.

Estado CTS-001 (post `e296c77 DIAS_CAPACITACION_REQUEST_ALIGNMENT_APPLIED`):

```
CTS-001 backend = 6,096.142357 COP/tx
CTS-001 excel   = 6,224.575126 COP/tx   (Vision CTS!C34)
delta           =  -128.432769 COP/tx   (residual 2.063%)
Payroll C35     =  -141.98  (~97% del residual)  → raíz: cargos_adicionales ausente del numerador FTE soporte
Firma -6.938% idéntica en cap_inicial (C39) / cap_rotación (C40) / crucero (C43) → raíz única FTE soporte
```

---

## Inventario contrato actual

Pipeline de dotación de Cadena A (request → contrato público → DTO interno → builder → consumidor de fórmula):

| Modelo/Clase | Archivo | Campo | Tipo | Default | Consumidor backend | Observación |
|--------------|---------|-------|------|---------|-------------------|-------------|
| `PerfilCadenaAV1` (contrato público, `extra="forbid"`, `frozen=True`) | `modules/shared/contracts/api_v1/request/cadena_a.py:24` | `fte` | `float` ≥0 | `0.0` | → builder → `PerfilCadenaAInput.fte` | único insumo de dotación de agentes |
| `PerfilCadenaAV1` | `…/request/cadena_a.py:36` | `incluye_crucero` | `bool` | `False` | `nomina.py:304` `_crucero` | precedente de campo per-perfil aditivo |
| `PerfilCadenaAV1` | `…/request/cadena_a.py:38-39` | `dias_cap_inicial/rotacion` | `int` | `10` | `nomina.py:229-257` | precedente de campo per-perfil numérico |
| `CadenaARequestV1` (contrato público) | `…/request/cadena_a.py:46` | `perfiles` | `List[PerfilCadenaAV1]` | `[]` | → `_cadena_a` | **no expone `staff_config` en V1 público** (solo `perfiles`) |
| `PerfilCadenaAInput` (DTO interno, dataclass) | `modules/calculator_motor/dto/user_inputs.py:187` | `fte` | `float` | (req) | `context_builder_perfiles_soporte_mixin:122` `fte_base` | numerador actual de soporte = `fte_base/ratio` |
| `PerfilCadenaAInput` | `…/dto/user_inputs.py:204` | `incluye_crucero` | `bool` | `False` | `nomina.py` | — |
| `StaffRolInput` (DTO interno) | `…/dto/user_inputs.py:236` | `nombre / activo / ratio_override` | `str / bool / Opt[float]` | `· True · None` | soporte mixin (activación + ratio) | **no tiene** campo de FTE/override de cantidad |
| `CondicionesCadenaAInput` | `…/dto/user_inputs.py:248` | `perfiles / staff_config` | `List[…]` | `[] / []` | soporte mixin | contenedor; `staff_config` vacío → defaults provider |
| Builder | `modules/calculator_motor/mixins/user_input_builders_cadena_a.py:138` `_perfil_a` | mapea `d[...]`→`PerfilCadenaAInput` | — | — | — | `extra="forbid"` ⇒ todo campo nuevo debe declararse aquí |
| Builder | `…/user_input_builders_cadena_a.py:128` `_staff_rol` | mapea `d[...]`→`StaffRolInput` | — | — | — | — |
| Consumidor (FÓRMULA) | `context_builder_perfiles_soporte_mixin.py:122,137-146` | `fte_base = perfil_base.fte`; `fte_contable = fte_base / ratio` | — | — | numeradores de cap/rotación/inicial/jefe | **punto exacto donde se sumaría `cargos_adicionales`** |

**Hallazgo de inventario:** No existe ningún campo de "dotación adicional" en request/contrato/DTO/provider.
Búsqueda exhaustiva previa (`rg "fte_adicional|cargos_adicionales|fte_extra|adicional_fte"`): **0 coincidencias**
(`support_fte_input_decision_v28.md` §8). El único insumo de dotación es `PerfilCadenaAInput.fte` (= agentes).

**Mapa escenario→perfil-base (clave del diseño):** el Excel modela 3 escenarios en columnas E/F/G de
`Condiciones Cadena A` (SAC / WhatsApp / Crecimiento). El backend modela cada escenario como **un
`PerfilCadenaAInput` base** (`fte` = 130 / 50 / 80). Por tanto un input "por escenario" del Excel
(E26/F26/G26) mapea **1:1 a un campo per-perfil** en `PerfilCadenaAInput`. **No es per-rol de soporte.**

---

## Fuentes Excel

Confirmado con `openpyxl` (`read_only=True`, fórmula + `data_only`) sobre `Condiciones Cadena A`:

| Concepto | Celda | Valor | Fórmula | Escenario/Perfil | Tipo de dato |
|----------|-------|-------|---------|------------------|--------------|
| FTE agentes SAC | E9 | 130 | (literal) | SAC (col E) | input |
| FTE agentes WhatsApp | F9 | 50 | (literal) | WhatsApp (col F) | input |
| FTE agentes Crecimiento | G9 | 80 | (literal) | Crecimiento (col G) | input |
| **cargos_adicionales SAC** | **E26** | **12** | (literal) | SAC (col E) | **input aditivo al numerador** |
| **cargos_adicionales WhatsApp** | **F26** | **None (=0)** | (vacío) | WhatsApp (col F) | input (=0, no afecta) |
| **cargos_adicionales Crecimiento** | **G26** | **7.384615** | (literal) | Crecimiento (col G) | **input aditivo al numerador** |
| ajuste E30 / E34 | E30 / E34 | 0 / 0 | (literal) | SAC | filas aditivas extra (0 en este deal) |
| Etiqueta fila 26 | D26 | `"Ratio"` | — | — | **etiqueta engañosa**: la fórmula suma E26 al numerador como FTE, no es un ratio |
| Supervisor SAC | **E95** | **9.5** | **(literal, NO fórmula)** | SAC (col E) | **override manual per-rol** |
| Supervisor WhatsApp | F95 | 2.5 | `=IF($C95=TRUE, …((F9+F26+F30+F34)/F122)…,0)` | WhatsApp | derivado: 50/20 = 2.5 ✔ |
| Supervisor Crecimiento | G95 | 4.369231 | `=…((G9+G26+G30+G34)/G122)…` | Crecimiento | derivado: (80+7.3846)/20 = 4.3692 ✔ |
| Ratio Supervisor | E122 | 20 | `INDEX(Inputs de Nomina…)` | — | ratio coincide con backend `ratios_staff` |
| Activación Supervisor | C95 | `True` | — | — | activo en los 3 escenarios |

**Fórmula Excel canónica del numerador de soporte** (verificada en F95/G95, sin override):
```
FTE_rol = IF(C_activo, (col9 + col26 + col30 + col34) / col_ratio  [× Panel!C20 si rotación], 0)
        = IF(activo,   (fte_agentes + cargos_adicionales)/ratio     [× pct_rotacion],          0)
```
**Fórmula backend actual** (`context_builder_perfiles_soporte_mixin.py:146`):
```
FTE_rol = fte_base / ratio   (= fte_agentes / ratio, SIN cargos_adicionales)
```

### Clasificación de cada valor

| Valor | Celda(s) | Clasificación | Justificación |
|-------|----------|---------------|---------------|
| `cargos_adicionales` (12 / 0 / 7.3846) | E26 / F26 / G26 | **`SCENARIO_LEVEL_INPUT`** | literal por columna-escenario, sumado al numerador de **todos** los roles de soporte de esa columna; no derivado de `fte` |
| ajustes E30 / E34 | E30 / E34 | `SCENARIO_LEVEL_INPUT` (= 0) | mismas semánticas que E26, valor 0 para este deal |
| Supervisor F95 / G95 | F95 / G95 | `DERIVED_FORMULA` | `(col9+col26+col30+col34)/ratio` reproducible con cargos_adicionales |
| **Supervisor SAC E95 = 9.5** | **E95** | **`PROFILE_LEVEL_OVERRIDE`** | **literal manual**: la fórmula daría `(130+12)/20 = 7.1`; el `9.5` está tecleado a mano (override real, no derivado) |

> **Aritmética crítica del override:** con `cargos_adicionales=12`, el Supervisor SAC vale `(130+12)/20 = 7.1`.
> El Excel tiene `E95 = 9.5` literal ⇒ **residual de +2.4 FTE de Supervisor** que `cargos_adicionales`
> **NO** explica. Es un override manual por celda, sin regla de negocio trazable (un número tecleado).

---

## Alternativas de contrato

### Alternativa A — Campo por escenario (per-perfil-base)

`cargos_adicionales: float = 0.0` en `PerfilCadenaAV1` (público) + `PerfilCadenaAInput` (interno).
Como cada perfil base backend = un escenario Excel, E26/F26/G26 → un valor por perfil.

```json
{ "nombre": "SAC", "fte": 130, "cargos_adicionales": 12, ... }
```

- **Ubicación:** `PerfilCadenaAV1` (`…/request/cadena_a.py`) y `PerfilCadenaAInput` (`user_inputs.py`).
- **Tipo / default:** `float`, `ge=0.0`, default `0.0` → preserva comportamiento legacy exacto (`fte/ratio`).
- **Backward compat:** ✅ `extra="forbid"` rechaza campos **desconocidos**, no campos **nuevos con default**; requests viejos sin el campo siguen validando.
- **Llega al builder:** una línea en `_perfil_a` (`float(d.get("cargos_adicionales", 0.0))`).
- **Afecta fórmula:** numerador soporte `(fte_base + perfil.cargos_adicionales)/ratio` (un punto: `soporte_mixin:122/137-146`); también alimenta cap/crucero (misma raíz, misma firma -6.938%).
- **Riesgos:** **doble conteo** si se suma a `fte` para salario de agentes; debe alimentar **solo** numeradores de soporte/cap/crucero, nunca el salario de los `fte_base` agentes.

### Alternativa B — Campo por perfil/rol de soporte

`cargos_adicionales` keyed por rol de soporte (Supervisor, GTR, …).

```json
{ "perfil": "Supervisor SAC", "cargos_adicionales": 12 }
```

- **Granularidad equivocada:** E26 es **una sola cifra por escenario** aplicada a **todos** los roles de soporte de esa columna; modelarla por rol **duplica** el mismo 12 en cada rol → redundante y propenso a error.
- **No evita ambigüedad:** introduce N entradas para un dato que es 1 por escenario.
- **Escala mal a B/C:** multiplica el contrato por rol.
- **Rompe simetría con `staff_config`** (que ya es per-rol pero solo activación/ratio).
- **Rechazada.**

### Alternativa C — Override explícito de FTE soporte

`fte_soporte_override` per-rol (replicaría E95 = 9.5 directo).

```json
{ "nombre": "Supervisor", "fte_override": 9.5 }
```

- **Replica Excel literal:** única forma de reproducir E95 = 9.5 (override manual).
- **Oculta la fórmula:** un número mágico sin ratio ni cargos detrás → **reduce trazabilidad**.
- **Contradice ratios:** rompe la invariante `FTE = (fte+cargos)/ratio` que el resto del motor respeta.
- **Riesgo de hardcode disfrazado:** un `9.5` en request es indistinguible de un hardcode.
- **Debe evitarse salvo el caso E95.** Si se adopta, **solo** como override excepcional per-rol, opt-in, documentado, y **diferido**.

### Tabla comparativa

| Alternativa | Campo(s) | Ubicación | Backward compatible | Requiere modules | Riesgo | Recomendación |
|-------------|----------|-----------|---------------------|------------------|--------|---------------|
| **A — por escenario** | `cargos_adicionales: float=0.0` | `PerfilCadenaAV1` + `PerfilCadenaAInput` | ✅ sí (default 0.0) | sí (1 punto: numerador soporte) | **bajo-medio** (doble conteo controlable) | ✅ **RECOMENDADA** |
| B — por rol soporte | `cargos_adicionales` keyed por rol | `StaffRolInput` | ✅ sí | sí | medio (granularidad errónea, duplicación) | ❌ rechazada |
| C — override FTE | `fte_soporte_override`/`fte_override` | `StaffRolInput` | ✅ sí (default None) | sí | **alto** (oculta fórmula, número mágico) | ⚠️ solo para E95, **DIFERIDA** |

---

## Decisión recomendada

**Recomendación: Híbrida con secuenciación — Alternativa A AHORA; Alternativa C DIFERIDA.**

- El contract change debe ser **por escenario (per-perfil-base)**, no por rol de soporte.
- **Sí** debe contemplar override per-rol (C) **conceptualmente**, pero **diferido** a una segunda fase.
- El override **no** debe ser parte del contrato inicial: cierra solo el residual del literal E95 (+2.4 FTE Supervisor SAC), tiene riesgo alto de número mágico y baja trazabilidad de negocio.
- **Default que preserva legacy:** `cargos_adicionales = 0.0` ⇒ numerador `(fte+0)/ratio = fte/ratio` (idéntico a hoy).
- **Campos opcionales:** ambos (`cargos_adicionales` con default 0.0; el futuro `fte_override` con default None).

Campos propuestos:

| Campo | Tipo | Ubicación | Default | Requerido | Motivo |
|-------|------|-----------|---------|-----------|--------|
| `cargos_adicionales` | `float` (`ge=0.0`) | `PerfilCadenaAV1` (público) | `0.0` | no | Excel E26/F26/G26 = 12/0/7.3846; aditivo al numerador de soporte por escenario |
| `cargos_adicionales` | `float` | `PerfilCadenaAInput` (interno) | `0.0` | no | espejo interno consumido por el soporte mixin |
| `fte_override` *(DIFERIDO)* | `Optional[float]` | `StaffRolInput` (futuro) | `None` | no | solo para casos literales tipo E95=9.5; **NO en fase 1** |

Comportamiento legacy:
- Request sin `cargos_adicionales` → `0.0` → soporte = `fte/ratio` → **resultado idéntico al baseline actual**.
- Cadenas B/C no tocadas (campo solo en `PerfilCadenaAV1` de Cadena A).
- `staff_config` (activación/ratio) sin cambios.

Fórmula backend esperada (fase de implementación, NO ahora):
```
fte_soporte = (fte_agentes + cargos_adicionales) / ratio        [× pct_rotacion si rotación]
```
en `context_builder_perfiles_soporte_mixin.py` (línea 122/137-146), un único punto de cambio.
`cargos_adicionales` alimenta numeradores de **soporte / cap_inicial / cap_rotación / crucero**;
**nunca** el salario de los `fte_agentes` (evitar doble conteo).

Override per-rol:
- **decisión:** contemplarlo en el diseño, **NO implementarlo en fase 1**.
- **motivo:** E95=9.5 es literal manual (la fórmula daría 7.1); +2.4 FTE Supervisor sin regla de negocio trazable; riesgo de número mágico; cierra solo un residual menor tras aplicar A.
- **diferido o incluido:** **DIFERIDO** → `CONTRACT_OVERRIDE_PER_ROL_DEFERRED` (reabrir si tras aplicar A el residual de Supervisor sigue siendo material y el negocio justifica el 9.5).

---

## Impacto técnico estimado

| Área | Archivo probable | Cambio esperado | Riesgo |
|------|------------------|-----------------|--------|
| Contrato/API | `modules/shared/contracts/api_v1/request/cadena_a.py` | +1 campo `cargos_adicionales: float = Field(0.0, ge=0.0)` en `PerfilCadenaAV1` | **LOW** (campo opcional con default; `extra="forbid"` no afecta a campos nuevos conocidos) |
| DTO interno | `modules/calculator_motor/dto/user_inputs.py` | +1 campo `cargos_adicionales: float = 0.0` en `PerfilCadenaAInput` | **LOW** |
| Loader/builder | `modules/calculator_motor/mixins/user_input_builders_cadena_a.py` `_perfil_a` | +1 línea `float(d.get("cargos_adicionales", 0.0))` | **LOW** |
| Nómina/FTE soporte | `modules/calculator_motor/mixins/context_builder_perfiles_soporte_mixin.py:122,137-146` | numerador `(fte_base + cargos_adicionales)` | **MEDIUM** (cambia valores de salida; debe pasar golden/baseline con evidencia Excel) |
| Cap/crucero | `modules/calculator_motor/formulas/payroll/nomina.py:229-308` | heredan numerador corregido vía FTE soporte | **MEDIUM** (firma -6.938% debe cerrarse) |
| Tests golden | `tests/golden/test_cts_001_v28.py`, `test_cts_exam_crucero_v28.py` | nuevos expected V2-8 con cargos_adicionales | **MEDIUM** (golden = evidencia Excel, no ajustar para "pasar") |
| Request V2-8 | `request/request.json` (perfiles Cadena A) | `cargos_adicionales: 12/0/7.3846` por perfil | **MEDIUM** (cambio de deal; fuera de esta sesión, kill-switch) |
| Docs | `docs/refactor/*`, `docs/ai/TASK_STATE.md` | actualizar estado | **LOW** |

Compatibilidad:
- **Request legacy sin `cargos_adicionales`** → default `0.0` → comportamiento actual idéntico. ✅
- **Default** preserva baseline (no requiere `make baseline` hasta validar paridad Excel). ✅
- **Cadenas B/C** no se tocan (campo solo en `PerfilCadenaAV1`). ✅
- **Solo Cadena A:** justificado — `cargos_adicionales` (E26) vive en `Condiciones Cadena A`; B/C no tienen análogo en el residual CTS-001.

**Riesgo global del contrato: `LOW` (contrato) + `MEDIUM` (fórmula/goldens).** No es `BREAKING_CHANGE_RISK`:
campo opcional con default neutro; `extra="forbid"` solo rechaza claves desconocidas, no claves nuevas declaradas.

**Riesgo dominante a controlar: DOBLE CONTEO.** `cargos_adicionales` debe entrar **solo** al numerador de
soporte/cap/crucero. Si se sumara a `perfil.fte` (agentes), inflaría salario de agentes y volumen — gap nuevo.

---

## Plan de implementación propuesto

> No ejecutar en esta sesión. Diseño para la futura sesión `IMPLEMENT_CARGOS_ADICIONALES_CONTRACT`.

1. **Contrato**
   - archivo: `modules/shared/contracts/api_v1/request/cadena_a.py`
   - cambio: `cargos_adicionales: float = Field(default=0.0, ge=0.0)` en `PerfilCadenaAV1`
   - tests: `tests/contract/` — request legacy (sin campo) valida; request con campo valida; negativo rechazado

2. **Loader/context (DTO + builder)**
   - archivo: `modules/calculator_motor/dto/user_inputs.py` (campo en `PerfilCadenaAInput`); `…/mixins/user_input_builders_cadena_a.py` (`_perfil_a`)
   - cambio: declarar campo + `float(d.get("cargos_adicionales", 0.0))`
   - tests: builder mapea valor; ausente → 0.0

3. **Fórmula FTE soporte**
   - archivo: `modules/calculator_motor/mixins/context_builder_perfiles_soporte_mixin.py` (líneas 122/137-146)
   - cambio: `numerador = perfil_base.fte + perfil_base.cargos_adicionales`; usar en todas las ramas (normal/rotación/inicial). Comentario obligatorio Excel V2-8 (`'Condiciones Cadena A'!E26` · `(col9+col26+col30+col34)/col122`).
   - tests: unit del mixin (Supervisor SAC: (130+12)/20=7.1); kill-switch: si `cargos_adicionales=0` resultado == baseline
   - **guard doble conteo:** verificar que `fte_base` para salario de agentes NO incluye cargos

4. **Request V2-8** *(fuera de scope; kill-switch — no modificar request.json sin sesión explícita)*
   - archivo: `request/request.json` (perfiles Cadena A)
   - cambio: `cargos_adicionales: 12 / 0 / 7.3846` por perfil base SAC/WhatsApp/Crecimiento
   - tests: golden CTS-001 recalculado vs Excel

5. **Goldens/baselines**
   - qué validar: CTS-001 C34/C35/C39/C40/C43 (firma -6.938% debe cerrarse); residual restante = override E95 (documentado)
   - baseline requerido: **sí, pero solo tras `validate-excel-v28` PASS y aprobación** — no en la sesión de contrato

**Kill-switches para la implementación:**
- `cargos_adicionales` ausente/0.0 debe reproducir el baseline byte a byte (regresión = abortar).
- No sumar `cargos_adicionales` a `fte` de agentes (doble conteo = abortar).
- No hardcodear 12 / 7.3846 / 9.5 en el motor (deben venir del request).
- No tocar Cadenas B/C.
- Si tras aplicar A el Supervisor SAC sigue desviado por el residual E95, **no** introducir override mágico sin sesión `CONTRACT_OVERRIDE_PER_ROL`.

---

## Go / No-Go

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Fuente Excel trazada | **GO** | `openpyxl`: E26=12, F26=None(0), G26=7.384615; F95/G95 fórmula `(col9+col26+col30+col34)/col122`; E95=9.5 literal |
| Campo backend viable | **GO** | per-perfil-base mapea 1:1 al escenario Excel; 1 campo en `PerfilCadenaAV1` + `PerfilCadenaAInput`; 1 punto de fórmula |
| Backward compatibility | **GO** | default `0.0` neutro; `extra="forbid"` no afecta campos nuevos declarados; legacy intacto |
| Impacto API aceptable | **GO** | campo opcional, no breaking; Cadenas B/C sin tocar |
| Riesgo de double count controlado | **GO** (con guard) | regla explícita: solo numerador soporte/cap/crucero, nunca salario de agentes; kill-switch definido |
| Override per-rol (E95=9.5) | **NEEDS_REVIEW** | literal manual sin regla de negocio; +2.4 FTE residual; DIFERIDO a fase 2 |

**Decisión: GO para `cargos_adicionales` (Alternativa A) · NEEDS_REVIEW para override per-rol (Alternativa C, diferida).**

Estado: **`CONTRACT_CHANGE_CARGOS_ADICIONALES_DESIGN_READY`**
(con `CONTRACT_OVERRIDE_PER_ROL_DEFERRED` para el override E95).

---

## Gates (sesión docs-only)

| Gate | Resultado |
|------|-----------|
| `tests/golden/test_cts_001_v28.py` | **2/2 PASS** |
| `tests/golden/test_cts_exam_crucero_v28.py` | **2/2 PASS** |
| `make validate-excel-v28` | **PASS (6/6, 1 skip)** |
| `make all` | **PASS** (36 pass · verify baseline match · validate-excel 7/7 match) |
| `make baseline` | **NO ejecutado** (prohibido) |

**Side effects:** `make all`/`validate-excel` regeneraron `reports/*` y `storage/parametrization/*/versions.json`
(ya en estado `M` antes de la sesión). **No se commitean.** Sin cambios en `modules/`, `request/`, `tests/`, `*.py`.
Hardcoded values nuevos en motor: **0**. Excel leído con `openpyxl` `read_only=True`.

---

## Veredicto

**`CONTRACT_CHANGE_CARGOS_ADICIONALES_DESIGN_READY`**

- Diseño recomendado: **Alternativa A** — `cargos_adicionales: float = 0.0` por escenario (per-perfil-base)
  en `PerfilCadenaAV1` + `PerfilCadenaAInput`, consumido en el numerador de FTE soporte.
- Override per-rol (E95=9.5, Alternativa C): **DIFERIDO** (`NEEDS_REVIEW`) — literal manual, sin regla de negocio,
  riesgo de número mágico; reabrir solo si el residual de Supervisor persiste material tras aplicar A.
- Backward compatible (default neutro), no breaking, riesgo de doble conteo controlado con guard explícito.
- Único P0 estructural de CTS-001 Cadena A; ningún otro gap comparable (OPEX exacto; CAPEX +16.72 = frente
  separado de amortización, signo opuesto).
