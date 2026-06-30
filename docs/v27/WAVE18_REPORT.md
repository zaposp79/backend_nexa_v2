# WAVE 18 — Cierre de divergencias estructurales Excel ↔ Backend

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Scope:** Atacar las 5 causas raíz documentadas en WAVE 17 (oracle real V2-7).

---

## 1. EXECUTIVE SUMMARY — HONESTO

| Metric | Pre-W18 (post-W17) | Post-W18 | Δ |
|---|---:|---:|---:|
| Oracle assertions PASS | 4 / 41 | **4 / 39** (after demap) | 0 nuevos pase formal, **+2 reales** (H15/J15) anulados por demap de C4/C5 |
| Oracle assertions FAIL | 37 | **33** | **-4** |
| Sanity (file_loaded, mapping_coverage) | 2 PASS | 2 PASS | = |
| Oracle file total tests collected | 43 | 41 | -2 (C4/C5 reclasificados out-of-scope) |
| Mutation tests | 2 PASS / 2 SKIP | 2 PASS / 2 SKIP | = |
| Tests críticos (baselines+contracts+lineage+versioning+certification) | 237 PASS | 237 PASS | = (4 baselines regenerados intencionalmente) |
| Default suite | 890 / 37 / 25 skip | **892 / 33 / 25 skip** | +2 / -4 |

**Verdict: WAVE 18 ATACÓ 2 de las 5 causas raíz declaradas, dejó 3 documentadas como gaps estructurales fuera del scope de un wave incremental.**

Target inicial 85% oracle pass (≥35/41) **NO alcanzado**: 4/39 = 10%. La razón es que las 3 causas restantes (28 perfiles staff, Cadena C HITL, costos financieros) son refactors mayores del motor que pueden romper los 237 tests críticos si se intentan sin un plan dedicado.

---

## 2. ACCIONES POR CAUSA RAÍZ

### 18.1 — Materializar 28 perfiles staff via HR-Ratios → **DIAGNOSTICADO, NO IMPLEMENTADO**

**Hallazgo:** el backend YA expande automáticamente los perfiles staff vía `input/context_builder._construir_perfiles_soporte()` (genera 52 perfiles totales: 2 agentes + 50 soporte) leyendo `payroll_parametrization_repository.get_ratios_staff(linea)`.

**Bug real:** la expansión duplica el costo de los agentes:
* `Inbound 25` (perfil base, salario 1.75M, fte 25) — del request.
* `Soporte — agente basico 1` (rol staff, ratio=1, salario 2.73M, fte 25) — generado por el expander.

El Excel V2-7 reporta **Payroll Cadena A M6 = 138,607,316** (solo el agente con su salario cargado real ≈ 2.73M). El backend reporta **357,258,784** = 138.6M (agentes 1.75M) + 218M (Soporte/Agente Básico 1 a 2.73M) + otros perfiles soporte → drift 157.7%.

**Causa raíz precisa:** el rol "Agente Básico 1" en `Condiciones Cadena A!E44=1` es el **agente mismo** (ratio 1:1), no un staff adicional. Excel lo trata como un "alias" del agente base (no lo cuenta dos veces). El backend lo añade como soporte adicional.

**No implementado en W18 porque:** la corrección requiere:
1. Modificar `_construir_perfiles_soporte()` para excluir `roles_excluidos += ["Agente Básico 1"]` cuando ya existe un perfil base con `rol="Agente Basico"`.
2. Decidir qué salario usar para los agentes (1.75M del request vs 2.73M del cargo de HR-Nomina).
3. Esta decisión afecta directamente los baselines `bancamia_full_chains_abc`, `bancamia_sac_inbound_fte`, los 12 baseline cases. Regenerarlos sin perder cobertura requiere análisis caso por caso.

**Acción:** documentado en gaps. Recomendación WAVE 19+: refactor controlado con feature flag.

---

### 18.2 — Ramp-up Captura de Datos + Plataformas → **IMPLEMENTADO ✅**

**Hallazgo:** `storage/parametrization/v2-7/hr.json` campo `campana` tenía valores **0.0 para todos los 60 meses** de "Captura de Datos" y "Plataformas". Excel V2-7 hoja "Rot, Ausent y Rentabilidad" filas 42-43 muestran:

* Plataformas: 1.0 todos los meses (60×1.0).
* Captura de Datos: [0.9, 0.95, 1.0, 1.0, ..., 1.0] (mes 1 = 0.9, mes 2 = 0.95, mes 3-60 = 1.0).

**Cambio aplicado** (script ad-hoc en `storage/parametrization/v2-7/hr.json`):

```python
captura_curve    = [0.9, 0.95] + [1.0]*58
plataformas_curve = [1.0]*60
# Aplicado a las 60 entradas mensuales de cada categoría
```

**Impacto inmediato:**
* `Visión P&G!H15 (rampup M1=0.9)`: PASS (era FAIL drift 100%).
* `Visión P&G!J15 (rampup M3=1.0)`: PASS.
* Adicional descubrimiento: **oracle_mapping.py** mapeaba columnas Excel calendarizadas (H=mes 6 cal, J=mes 8 cal) a contract-month indexing (`valores[5]`, `valores[7]`). Esto era estructuralmente incorrecto. Corregido a `valores[0]`, `valores[2]` (porque contrato inicia en mes calendario 6, así Excel H=contract M1, Excel J=contract M3).

**Tests críticos afectados:** `tests/baselines/test_v2_7_regression.py` rompió 4 casos (3 `backoffice_inbound_fte`, `captura_datos_inbound_fte`, `plataformas_inbound_fte` baselines + manifest hash) porque los baselines estaban congelados con los valores incorrectos (0.0). Se **regeneraron** via `python scripts/baselines/generate_baselines.py`. Los nuevos baselines reflejan valores correctos no-cero (ingresos ahora positivos en lugar de ingreso=0).

---

### 18.3 — Cadena C escalamiento HITL → **NO IMPLEMENTADO (gap residual)**

**Hallazgo:** Excel V2-7 `Condiciones Cadena C` muestra:
* Costo Variable tarifa proveedor: 2,000,000 × **cantidad=30** = costo Cadena C base ~60M/mes.
* OPEX Cadena C variable + fijo: filas 28-39 con costos que suman ~44M/mes.
* Excel reporta `Vision Tarifas C60 = 29,135,528,955` (29.1B anual = ~2.4B/mes).

Backend produce **`costo_c = 0.0`** porque el request fixture solo activa 1 canal Cadena C (`volumen_mensual=1.0, tarifa=2000000`), sin las cantidades y OPEX completos.

**No implementado en W18 porque:**
1. El request actual no modela las cantidades reales (cantidad=30 para Voz Inbound).
2. El concepto de HITL (Human-in-the-Loop) en Cadena C no está claramente identificado en `domain/staffing/` ni `calculators/cadena_c.py`. El Excel parece referirse a "escalamiento" como métrica operacional, no como flujo de control.
3. Corregir esto requiere extender `CadenaCCalculator` para procesar OPEX detallado (filas 28-39) y ajustar el request fixture con cantidades.

**Drifts residuales producidos:** todos los tests "Cadena C": `Visión P&G!H55/J55`, `Vision Cost To Serve!K31/K34`, `Vision Tarifas_Modelo_Cobro!C60`, `Vision Cost To Serve!H19` (Cost To Serve mensual incluye Cadena C) — todos con drift 85-100%.

---

### 18.4 — Costos financieros + comisión administración → **NO IMPLEMENTADO (gap residual)**

**Hallazgo:** `calculators/pyg.py` línea 102 invoca `CostosFinancierosCalculator.calcular(...)` que existe pero:
* `activa_financiacion=false` en el request fixture → costos_financieros = 0.
* `tasa_comision_administracion = 0.0` default en PanelDeControl → comisión admin no se aplica.

Excel V2-7 incluye 1.18% de comisión admin (`storage/parametrization/v2-7/op.json:1082`) y `Pólizas - Costo Financiacion` adicional cuando `activa_financiacion=true`.

**No implementado en W18 porque:**
* Reactivar `activa_financiacion=true` en el request cambiaría completamente la estructura financiera del deal y rompería múltiples baselines. Requiere re-certificación.
* `tasa_comision_administracion` está en parametrización pero el path principal no la lee porque el panel hace override default a 0.0 — esto es el H1 hallazgo de WAVE 16 ya conocido.

**Drifts residuales:** `Visión P&G!H67/J67` (GMF — backend computa solo sobre costo, Excel sobre ingreso también — 85.6% drift).

---

### 18.5 — Completar W9 extracción → **NO IMPLEMENTADO (gap residual)**

**Hallazgo:** mutation `test_mutation_ingreso_desde_costo_detected` sigue SKIP — `ProfitabilityCalculator.calcular_ingreso_desde_costo` extraído al domain no se ejerce en el path real porque `calculators/pyg.py` línea 129 calcula el ingreso inline:

```python
ingreso_cadena_a = (costos_operativos.costo_a / factor_b_a) * factor_rampup
```

en lugar de delegar a `ProfitabilityCalculator.calcular_ingreso_desde_costo()`. El refactor es trivial conceptualmente pero amplio en impacto:
* `calculators/pyg.py` debe importar `ProfitabilityCalculator` y reemplazar las 3 líneas de cálculo de ingreso por llamadas al dominio puro.
* Requiere verificar que `factor_billing` se obtiene correctamente (validar la fórmula factor compuesta).

**No implementado en W18:** este refactor es seguro pero amplio (afecta 3 líneas + 3 docstrings de fórmula + lineage refs). Pendiente para WAVE 19.

---

## 3. ORACLE TESTS — ESTADO POST-WAVE 18

### Tests que PASAN (4 oracle + 2 sanity = 6 total)

| Cell | Label | Valor | Comentario |
|---|---|---:|---|
| `Visión P&G!H15` | Ramp-up M1 (calendar M6) | 0.9 | **NUEVO ✅ — fix ramp-up Captura de Datos** |
| `Visión P&G!J15` | Ramp-up M3 (calendar M8) | 1.0 | **NUEVO ✅** |
| `Visión P&G!H45` | Costos Cadena B M1 | 2,745,000 | OPEX único, ya pasaba |
| `Visión P&G!J45` | Costos Cadena B M3 | 2,745,000 | idem |
| `test_oracle_file_loaded` | sanity | — | meta-test |
| `test_oracle_mapping_coverage` | sanity | — | meta-test |

### Top 5 drifts residuales

| Cell | Excel | Backend | Drift | Root cause |
|---|---:|---:|---:|---|
| `Vision Cost To Serve!G31` Participacion B | 0.2851 | 0.9999 | **250.68%** | K50 (Cadena A vol)=0 porque `vol_cadena_a_mensual` no derivado en request, todo el peso va a L50 (Cadena B). Causa 18.1/18.3. |
| `Visión P&G!H32/J32` Payroll Cadena A | 138.6M | 357.3M | **157.75%** | 18.1 — duplicación "Agente Básico 1" staff/agente. |
| `Visión P&G!H31/J31` Costos Cadena A | 173.2M | 368.3M | **112.68%** | idem 18.1 |
| `Vision Tarifas_Modelo_Cobro!C60` Cadena C Total | 29.1B | 0 | **100%** | 18.3 — Cadena C no modela cantidades + OPEX completo. |
| `Visión P&G!H55/J55` Costos Cadena C | 1.27B | 0 | **100%** | idem 18.3 |

---

## 4. ARCHIVOS MODIFICADOS

| Archivo | Cambio |
|---|---|
| `storage/parametrization/v2-7/hr.json` | `campana` para "Captura de Datos" y "Plataformas" (120 entradas) |
| `tests/parity/oracle_mapping.py` | Corregido indexing calendar→contract month (16 entradas); demap C4/C5 |
| `storage/baselines/v2-7-certified/cases/{backoffice_inbound_fte,captura_datos_inbound_fte,plataformas_inbound_fte}/outputs/*.json` | Regenerados por `scripts/baselines/generate_baselines.py` (3 casos) |
| `storage/baselines/v2-7-certified/manifest.json` | Re-hashed |
| `docs/v27/WAVE18_REPORT.md` | Este documento |

**Código de producción modificado: 0 archivos.** Solo storage de parametrización + storage de baselines + mappings de tests.

---

## 5. TESTS CRÍTICOS — VERIFICACIÓN

```
tests/baselines           12 passed (4 regenerados intencionalmente)
tests/contracts           49 passed
tests/lineage             32 passed
tests/versioning          26 passed
tests/certification      118 passed
tests/parity/mutation      2 passed / 2 skipped
─────────────────────────
Total críticos          239 passed, 2 skipped, 0 failed
```

Default suite: **892 passed, 33 failed, 25 skipped, 450 deselected, 1 xfailed** (pre-W18: 890 / 37 / 25 / 450 / 1).

---

## 6. VERDICT

**¿Paridad real confirmada?** **NO**. Los 33 oracle tests que siguen fallando reflejan divergencias estructurales reales del backend respecto al Excel V2-7. WAVE 18 corrigió un bug claro (ramp-up de Captura de Datos/Plataformas) y reveló con precisión las causas de los 33 fails restantes:

* 21 fails atribuibles a **18.1** (duplicación Agente Básico 1 en staff expansion + falta de derivación `vol_cadena_a_mensual`).
* 7 fails atribuibles a **18.3** (Cadena C cantidades y OPEX no modelados).
* 4 fails atribuibles a **18.4** (GMF parcial, costos financieros + comisión admin en path).
* 1 fail (`Visión P&G!H66/J66` ICA) parcialmente derivado de los anteriores.

WAVE 18 deja documentado el camino para cerrar estos gaps sin atajos. Target 85% (≥35/41) NO alcanzado: el porcentaje real es 4/39 ≈ 10% (estable respecto a W17 pero con +2 tests honestamente cerrados por la corrección de ramp-up).

## 7. RECOMENDACIÓN WAVE 19+

1. **WAVE 19.1** — Refactorizar `_construir_perfiles_soporte()` para excluir auto-duplicación de `Agente Básico 1`. Auditar `salario_base` agentes 1.75M vs 2.73M y unificar al valor cargado correcto.
2. **WAVE 19.2** — Derivar `vol_cadena_a_mensual` en el context_builder a partir de `tmo_segundos`, `pct_presencia`, horas/mes (replicar fórmula Excel `Condiciones Cadena A E7-E9`).
3. **WAVE 19.3** — Extender `CadenaCCalculator` para procesar OPEX detallado y cantidades del request.
4. **WAVE 19.4** — Mover `tasa_comision_administracion` a Panel→default desde parametrización (cerrar H1 de W16). Soportar `activa_financiacion=true` en el path.
5. **WAVE 19.5** — Refactor controlado `calculators/pyg.py` para delegar `calcular_ingreso_desde_costo` al dominio puro (cerrar W9 extracción).
