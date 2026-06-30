# WAVE 19 — Fix bug duplicación staff + normalización ratios

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Scope:** Cerrar la causa raíz 18.1 documentada en WAVE 18 — duplicación de
agentes como perfiles soporte ("Agente Básico 1") y exclusiones rotas por
mismatch de casing entre `ratios` (normalizadas) y `reglas_staff`
(capitalizadas).

---

## 1. EXECUTIVE SUMMARY — HONESTO

| Metric                         | Pre-W19  | Post-W19 | Δ       |
|--------------------------------|---------:|---------:|--------:|
| Oracle assertions PASS         | 6 / 39   | 6 / 39   | 0       |
| Oracle assertions FAIL         | 33       | 33       | 0       |
| Críticos (baselines+contracts+lineage+versioning+certification) | 237 PASS | **237 PASS** | = |
| Default suite                  | 892 / 33 / 25 skip | 892 / 33 / 25 skip | = |
| Baselines regenerados          | —        | **12 / 12** | (justificado abajo §6) |
| Drift Cadena A H31             | 112.68%  | **2.08%**   | -110.6 pp |
| Drift Cadena A H32 payroll     | 157.75%  | **14.39%**  | -143.4 pp |
| Drift Contribucion M6 (H74)    | 71.60%   | **86.50%**  | +14.9 pp (ahora visible al subir el costo C/D) |
| Perfiles staff por agente      | 25 (con 3 dups) | **22 (sin dups)** | -3 |

**Verdict: la causa raíz 18.1 está CERRADA.** El bug de duplicación se eliminó
(perfiles "Soporte — agente basico 1", "Soporte — validador", "Soporte —
aprendiz sena" lowercase y "Soporte — inclusion" lowercase ya no se generan).
Los drifts estructurales de Cadena A bajaron 110+ puntos porcentuales (H31 de
112% a 2%). **El target de +10 oracle tests no se alcanzó** porque los 27
fails restantes están dominados por causas 18.3 (Cadena C unmodeled, ~7 tests)
y 18.4 (costos financieros, GMF over-income, ICA, ~6 tests), y por un drift
residual ~14% en payroll Cadena A causado por la divergencia entre el
`salario_cargado` que el motor computa (~2.9M) y el `costo_empresa_excel`
pre-cargado en HR-Nomina (~2.73M) — un gap distinto de duplicación.

---

## 2. BASELINE PRE-W19

```
33 failed, 6 passed in tests/parity/test_excel_oracle_v2_7_real.py
```

Lista de los 33 fails (drift al inicio de W19):

| Sección | Cell | Drift pre-W19 |
|---|---|---:|
| Vision Tarifas | C40 (Cadena A Costo Total) | 73.03% |
| Vision Tarifas | C50 (Cadena B Costo Total) | abs vs 0 |
| Vision Tarifas | C60 (Cadena C Costo Total) | 100.00% |
| Vision Tarifas | C72 (Facturacion Total) | 98.78% |
| Vision CTS | B19, H19, C/G/K 31/34, G49 | 6.7–250.7% |
| P&G monthly | H/J 18 (Ingreso Bruto) | ~74% |
| P&G monthly | H/J 30 (Costo Total) | ~74% |
| P&G monthly | H/J 31 (Costos Cadena A) | **112.68%** |
| P&G monthly | H/J 32 (Payroll Cadena A) | **157.75%** |
| P&G monthly | H/J 41 (No Payroll A) | ~68% |
| P&G monthly | H/J 55 (Costos Cadena C) | 100.00% |
| P&G monthly | H/J 66 (ICA) | ~71% |
| P&G monthly | H/J 67 (GMF) | ~85.6% |
| P&G monthly | H/J 74 (Contribucion) | ~72–302% (sign flip pre-W18) |
| P&G monthly | H/J 79 (Utilidad Neta) | idem |

---

## 3. RE-EXTRACCIÓN HOJA "Inputs de Nomina" (sub-causa 19.A)

Se inspeccionó la hoja "Inputs de Nomina" del Excel V2-7 con `openpyxl
data_only=True`. La estructura coincide con la documentada en WAVE 4–5
(`docs/v27/NOMINA_LAYOUT_V2_7.md`):

| Sección                              | Filas | Roles |
|--------------------------------------|-------|------:|
| Empleado                             | 15–40 | 25    |
| Equipo de Soporte y Mantenimiento    | 59–71 | 12    |
| Equipo de HITL                       | 76–82 | 6     |
| Roles de Implementación              | 88–102| 14    |
| **TOTAL**                            |       | **57**|

**Hallazgo clave:** Excel V2-7 hoja "Condiciones Cadena A" **no lista los 28
perfiles staff** — los infiere via `Ratios` (columnas E/F filas 25–48). El
único perfil agente con `incluir_en_deal=True` y `ratio=1` es **"Agente Básico
1"** en `D44/E44`, que es la **fila self-reference** del propio agente en la
tabla de ratios (Excel calcula `W44 = fte_agente / 1 = fte_agente` sólo para
totalizar). Excel **no** lo añade como una línea de payroll adicional — usa
sus 25 (Voz) + 15 (WhatsApp) FTE × cargado del agente directamente.

Diff vs WAVE 4: **0 perfiles nuevos**. La extracción W4 ya era completa (57
roles). El problema de W17/W18 no era extracción incompleta sino interpretación
incorrecta de la fila "Agente Básico 1" en el motor.

---

## 4. REQUEST FIXTURE (sub-causa 19.B)

**Decisión:** mantener el fixture
`tests/parity/fixtures/excel_v2_7_real_request.json` con **2 perfiles
explícitos** (Inbound 25 Voz fte=25 y inboun Whatsapp fte=15). Esto refleja
fielmente lo que Excel V2-7 lista en `Condiciones Cadena A!E16:F18`. Los 28+
perfiles soporte se infieren del backend vía `get_ratios_staff(linea)`,
igual que Excel los infiere desde su tabla de ratios.

**No se materializaron los 28 perfiles soporte explícitamente** en el request
porque el contrato del motor (`PerfilCadenaAInput`) está diseñado para que la
expansión de soporte sea automática. Materializarlos cambiaría el contrato y
requeriría un refactor mayor del adapter — fuera de scope.

Fixture: sin cambios estructurales. Confirmado que el único "agregado" que
quedaba pre-W17 ya estaba eliminado (`salario_base=85065268.0` fake removido
en W17).

---

## 5. BUG DUPLICACIÓN — FIX (sub-causa 19.C) ✅ IMPLEMENTADO

### 5.1 Causa raíz precisa

`input/context_builder.py::_construir_perfiles_soporte()` itera sobre
`ratios.items()` cuyas claves vienen **normalizadas** (lowercase, sin acentos)
por `PayrollParametrizationRepository._normalize()`. Las comparaciones
`if rol in excluidos`, `if rol in roles_especiales`, `if rol == rol_jefe_comerc`
usaban los strings **capitalizados** provenientes de `reglas_staff` ("Aprendiz
SENA", "Inclusión", "Validador", "Director de cuentas"), por lo que **ningún
match ocurría** y los roles especiales / excluidos terminaban procesándose en
el loop principal como staff normal, además de re-procesarse luego en sus
handlers específicos.

Adicionalmente, la clave que devuelve el repositorio era
`roles_excluidos_ratios`, pero context_builder leía `roles_excluidos` —
**key mismatch** que dejaba `excluidos = ∅` siempre.

Resultado neto: por cada perfil agente se generaban **3 perfiles soporte
duplicados** (validador, aprendiz sena lowercase, inclusion lowercase) más
**1 self-clone del agente** ("Agente Básico 1" con ratio=1 → FTE = fte_agente,
salario cargado ~4M, contribución ≈ 102M en Voz + 61M en WhatsApp).

### 5.2 Fix aplicado

`input/context_builder.py::_construir_perfiles_soporte()` (líneas 527–562):

1. Normalizar TODOS los sets de comparación al mismo formato que las claves
   de `ratios` (vía `self._normalize_rol(x)`).
2. Aceptar tanto `roles_excluidos_ratios` (canónico) como `roles_excluidos`
   (legacy alias) para compatibilidad.
3. Añadir explícitamente `"Agente Básico 1"` a la lista de exclusiones — es
   la self-row del agente en la tabla de ratios, no un staff independiente.
4. Comparar `rol == rol_jefe_comerc_n` (ambos normalizados).
5. Conservar la lista original de `roles_fte_volumetrico` (`_orig`) para el
   lookup posterior de salario que sí requiere el nombre con casing original.

Diff en una sola sección, ~25 líneas modificadas. **Cero cambios en código de
producción fuera de este método.**

### 5.3 Evidencia matemática del fix

| Antes (con bug) | Después (fix W19) |
|---|---|
| Total perfiles A: 52 | Total perfiles A: 45 |
| FTE total: 93.29 | FTE total: 48.30 |
| Payroll mensual (sin rampup): 321,740,706 | Payroll mensual (sin rampup): 144,733,485 |
| "Soporte — agente basico 1" Voz fte=25 contrib=102M | (eliminado) |
| "Soporte — agente basico 1" WhatsApp fte=15 contrib=61M | (eliminado) |
| "Soporte — validador" Voz fte=0.5 contrib=1.4M | (eliminado) |
| "Soporte — validador" WhatsApp fte=0.3 contrib=0.8M | (eliminado) |
| "Soporte — aprendiz sena" (dup lowercase) | (eliminado) |
| "Soporte — inclusion" (dup lowercase) | (eliminado) |

Drift de `Visión P&G!H31 (Costos Cadena A M6)` pasa de **112.68% → 2.08%**.
Drift de `H32 (Payroll Cadena A M6)` pasa de **157.75% → 14.39%**.

El residual ~14% en H32 se debe a que el motor calcula
`salario_cargado_agente = NominaService.calcular(1750905, 0.10) ≈ 2,900,433`
mientras Excel usa el valor pre-cargado `costo_empresa_excel = 2,730,864` de
la fila "Agente Básico 1" en HR-Nomina. Este es un drift de **formula nómina
cargada**, no de duplicación. Out-of-scope para W19; documentado como gap
residual W20.

---

## 6. BASELINES REGENERADOS

Los 12 baselines `storage/baselines/v2-7-certified/cases/<case>/outputs/*.json`
**y** `manifest.json` se regeneraron via
`python scripts/baselines/generate_baselines.py`.

**Justificación matemática:** el fix elimina perfiles soporte que NO existían
en Excel V2-7. Los baselines previos congelaban valores con duplicación
estructural (e.g. `bancamia_sac_inbound_fte.contribucion_total=526.7M` con
phantom staff, vs `253.9M` real). Re-certificar mantiene los baselines como
contratos congelados del **nuevo estado correcto** (sin duplicación).

Verificación manual de 2 baselines:

| Baseline | KPI | Pre-W19 (buggy) | Post-W19 | Cambio justificable |
|---|---|---:|---:|---|
| `bancamia_sac_inbound_fte` | costo_cadena_a_promedio | 94,391,076 | 45,513,927 | -52% ≈ se elimina el clone "Agente Básico 1" cuyo fte_base coincide con el agente |
| `bancamia_sac_inbound_fte` | facturacion_mensual_proyectada | 131,960,477 | 63,629,314 | -52% idem (la facturación es ingreso = costo / factor_b) |
| `cobranzas_outbound_fte` | (proporción equivalente) | regenerado | regenerado | Consistente |

El cambio es proporcional al peso del clone duplicado (FTE=fte_base × 1 +
SENA/Inclusión/Validador phantom), que era ~50% del payroll total en estos
casos.

Tests críticos: **237 passed, 0 failed** después de la regeneración.

---

## 7. ORACLE TESTS — POST W19

```
33 failed, 6 passed in tests/parity/test_excel_oracle_v2_7_real.py
```

Mismo número que pre-W19, pero los drifts colapsaron drásticamente para
Cadena A. Top drifts residuales y root cause:

| Cell | Excel | Backend | Drift | Causa residual |
|---|---:|---:|---:|---|
| `P&G!H31` Costos Cadena A | 173.2M | 169.6M | **2.08%** | 14% drift en H32 + No Payroll faltante |
| `P&G!H32` Payroll Cadena A | 138.6M | 158.5M | **14.39%** | Salario cargado motor (2.9M) ≠ Excel costo_empresa_excel (2.73M) — formula nómina divergente |
| `P&G!H41` No Payroll A | 34.5M | 11.0M | **68.12%** | Componentes No Payroll del costo Cadena A subdesarrollados (18.4) |
| `P&G!H55` Costos Cadena C | 1.27B | 0 | **100%** | 18.3 — Cadena C HITL no modelado |
| `P&G!H67` GMF | 10.3M | 0.7M | **93.22%** | 18.4 — GMF backend sólo sobre costo, Excel sobre ingreso |
| `P&G!H66` ICA | 32.2M | 4.4M | **86.50%** | Derivado de ingreso bajo (cadena C=0 + cadena A 14% bajo) |
| `P&G!H74` Contribucion | 183.3M | 24.8M | **86.50%** | Compuesto de los anteriores |
| `Vision CTS!G31` Particip B | 0.285 | 0.999 | **250.68%** | Cadena A y C ≈ 0 → toda participación va a B |
| `Vision Tarifas!C40` Cadena A Total | 1.37B | 172M | **87.39%** | Excel C40 es anualizado; backend es mensual — gap de interpretación oracle |
| `Vision Tarifas!C60` Cadena C Total | 29.1B | 0 | **100%** | 18.3 |
| `Vision Tarifas!C72` Facturacion | 38.6B | 221M | **99.43%** | Interpretación anualizada (12 meses × 12 canales) |

---

## 8. ARCHIVOS MODIFICADOS

| Archivo | Cambio |
|---|---|
| `input/context_builder.py` | Fix `_construir_perfiles_soporte()` líneas 527–562 + 651 — normalización de comparaciones + exclusión "Agente Básico 1" |
| `storage/baselines/v2-7-certified/cases/*/outputs/*.json` | 12 casos regenerados |
| `storage/baselines/v2-7-certified/manifest.json` | Re-hashed |
| `docs/v27/WAVE19_REPORT.md` | Este documento |

**Código de producción modificado: 1 archivo, 1 método.** Storage de
baselines regenerado consistentemente.

---

## 9. TESTS CRÍTICOS — VERIFICACIÓN

```
tests/baselines           12 passed (12 regenerados — justificación §6)
tests/contracts           49 passed
tests/lineage             32 passed
tests/versioning          26 passed
tests/certification      118 passed
────────────────────────
Total                    237 passed, 0 failed
```

Default suite: **892 passed, 33 failed, 25 skipped, 450 deselected, 1 xfailed**
(idéntico a pre-W19 en counts globales — la mejora se ve en drift, no en
test count).

---

## 10. VERDICT

**Causa raíz 18.1 (duplicación staff): CERRADA.** El bug estaba en
`context_builder._construir_perfiles_soporte()` por:

1. Comparaciones case-sensitive entre claves normalizadas de `ratios` y
   strings capitalizados de `reglas_staff`.
2. Key mismatch `roles_excluidos` vs `roles_excluidos_ratios`.
3. Falta de exclusión explícita de la self-row "Agente Básico 1" del agente
   en la tabla de ratios.

Tras el fix, los perfiles Cadena A producidos por el motor son los 22 staff
reales del Excel (sin duplicados ni self-clones del agente), y el drift de
`P&G!H31` (Costos Cadena A) pasa de 112% a 2%, dentro de un orden de magnitud
correcto.

**Target +10 oracle tests NO alcanzado** (6 → 6) porque la tolerancia del
oráculo es `rel_diff ≤ 0.01%` y los 33 fails restantes están dominados por:

* 7 fails — causa 18.3 (Cadena C unmodeled, 100% drift estructural).
* 6 fails — causa 18.4 (GMF/ICA/comisión admin/costos financieros parciales).
* 14 fails — efectos compuestos (Contribucion, Utilidad Neta, Cost To Serve)
  derivados de los gaps 18.3+18.4 + el drift residual ~14% en cargado del
  agente.
* 6 fails — interpretación anualizada vs mensual del oráculo (C40, C72, B19).

Estos NO son consecuencia del bug duplicación — son gaps estructurales del
motor (Cadena C HITL, comisión admin path, GMF formula) que requieren cada
uno un wave dedicado para no romper los 237 críticos.

---

## 11. NEXT WAVE RECOMENDADA

1. **WAVE 20.1** — Cerrar drift 14% en H32 payroll Cadena A: alinear el
   `salario_cargado` que computa `NominaService.calcular(1750905, 0.10)` con
   el valor pre-cargado `costo_empresa_excel=2,730,864` en HR-Nomina. Debe
   aplicarse override consistente por canonical_rol "Agente Basico" →
   "Agente Básico 1" (V2-7 trata estas como el mismo rol con sufijo
   posicional).
2. **WAVE 20.2** — Implementar Cadena C HITL (causa 18.3) con cantidades y
   OPEX detallado.
3. **WAVE 20.3** — Cerrar 18.4 (GMF sobre ingreso, comisión admin path,
   costos financieros opcionales).
4. **WAVE 20.4** — Revisar oracle mapping: las celdas anualizadas (C40, C72,
   B19) deben mapearse al promedio mensual × meses_contrato (12) en el motor
   para evitar comparaciones apples-to-oranges.
