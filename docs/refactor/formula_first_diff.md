# Formula-First Diff — CTS-001 V2-8 (E95 override + CAPEX amortization)

Fecha: 2026-06-12 · Rama: `refactor/modular-pure` · Sesión: `E95_OVERRIDE_FAST_PARITY` (Opción 3: E95 + CAPEX)
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`. Deal: SAC / METROCUADRADO COM SAS / Grupo Aval, 24m.
Provider: `tests/refactor/_v28_deal_provider.py` (W-override). Denominador Cadena A: Panel!W31 = 221,000 tx/mes.

> **Hallazgo clave:** el headline CTS-001 era `+1.05 COP/tx` (0.0169%) **falso** — una cancelación
> entre déficit de payroll (-74.94, brecha E95) y sobre-amortización CAPEX (+75.99). No era paridad real.
> Esta sesión corrige **cada componente individualmente** contra Excel (sin compensación).

---

## Diff por componente (Vision Cost To Serve, COP/tx)

| Concepto | Celda Excel | Valor Excel | Backend ANTES | Backend DESPUÉS | Δ después | Status |
|----------|-------------|-------------|---------------|-----------------|-----------|--------|
| Cost To Serve (total) | C34 | 6,224.5751 | 6,225.6249 (+1.05, falso) | 6,197.0484 | **-27.53 (0.44%)** | HONEST_RESIDUAL |
| Payroll | C35 | 5,462.3559 | 5,387.4182 (-74.94) | 5,437.9972 | **-24.36** | IMPROVED (+50.58) |
| No Payroll | C45 | 762.2192 | 838.2067 (+75.99) | 759.0512 | **-3.17** | IMPROVED |
| — OPEX Fijo | C46 | 308.1382 | 308.1382 | 308.1382 | **0.0000** | EXACT |
| — Inversiones (CAPEX) | C47 | 103.0436 | 182.1991 (+79.16) | 103.0436 | **+0.0000** | **EXACT MATCH** |
| — Costos Fijos x Est. | C48 | 351.0375 | 347.8694 | 347.8694 | -3.17 | minor (separate) |
| Supervisor SAC (FTE) | E95 | 9.5 | 7.1 = (130+12)/20 | 9.5 | 0.0 | **EXACT (override)** |

**Sin compensación:** C47 queda EXACT (Δ=0.0000) y C35 mejora +50.58 hacia Excel, cada uno por separado.
El residual honesto -27.53 = brecha aditiva salario_fijo/variable (C37 +210.53 / C38 -281.63: Excel suma
la comisión cruda D62 sobre el cargado AM, el backend la particiona) + costos_fijos -3.17. Ambos son frentes
separados documentados, NO enmascarados.

---

## P1 — E95 Supervisor override (override opt-in per-rol)

**Excel V2-8 `Condiciones Cadena A`!E95 = 9.5** (literal manual; la fórmula `(col9+col26+col30+col34)/col122`
daría `(130+12)/20 = 7.1`). F95/G95 (WhatsApp/Crecimiento) SÍ son derivados (2.5 / 4.3692).

Mecanismo (sin hardcode en motor; el 9.5 vive en `request.json`):
- Contrato: `fte_soporte_overrides: Dict[str, float]` en `PerfilCadenaAV1` (default vacío = legacy).
- DTO `PerfilCadenaAInput` + dominio `PerfilCadenaA` + builder `_perfil_a` + `_construir_perfil_a` propagan el campo.
- `context_builder_perfiles_soporte_mixin`: tras computar `fte_contable` del rol, si hay override (keyed por
  rol normalizado) lo reemplaza ANTES de la cascada SENA/Inclusión (consistente con Excel, que lee el literal).
- Request V2-8: `condiciones_cadena_a.perfiles[0]` (SAC) → `"fte_soporte_overrides": {"Supervisor": 9.5}`.
  WhatsApp/Crecimiento sin override (sus F95/G95 son fórmula).

Verificado: Supervisor SAC 7.1 → 9.5 (= E95). Default vacío reproduce baseline (legacy byte-idéntico).

---

## P2 — CAPEX amortización (C47, fórmula corregida)

**Excel V2-8 `Vision CTS`!C47** = `SUM('No payroll'!D193:BK193 + D205:BK205) / C11 / W31`.
Las filas 193/205 = amortización mensual por perfil = `'No payroll'!E167/E168/E169`:
```
E167 = SUMPRODUCT($D$134:$D$162 ["Precio mensual"], FILTER(qty por escenario)) × (1 + Panel!L11)
```
- Columna D ("Precio mensual") = `precio_total / "Meses a diferir"` (C). Ej. PC: 3,508,260/60 = 58,471.
- **Cobro PLANO durante TODOS los meses del contrato** (row 167: cols L..AI = valor constante; 0 fuera).
- `meses_a_diferir` (60 PC / 1 licencias / 12 SFTP) **NO** aparece en la fórmula salvo para derivar precio_mensual;
  el horizonte de cobro es el contrato completo (24m), NO el plazo de diferimiento.

**Bug backend (2 causas):**
1. Leía `meses_amortizacion` (ausente; el request usa `meses_a_diferir`) → `meses` defaulteaba a 1 →
   `precio_mensual = precio/1 = precio_total` (3,508,260 en vez de 58,471).
2. Gate `mes ≤ meses` con `meses=1` → TODO el CAPEX caía en el mes 1 (966M) → promediado /24 = 182.20.

**Fix (`context_builder_perfiles_soporte_mixin._build_amortizable_item`):**
- `precio_mensual` = columna del request (= precio/meses_a_diferir); fallback `precio/meses_a_diferir`.
- `meses` (horizonte de cobro) = `meses_contrato` → cobro plano en todos los meses del contrato (= Excel).
- `meses_a_diferir` solo deriva precio_mensual; ya NO gatea el cobro mensual.
- `meses_contrato` se cablea desde `panel.meses_contrato` a ambos builders (agregado y per-perfil).

Resultado: C47 182.20 → **103.0436 (Δ+0.0000, EXACT MATCH)**.

---

## Gates

| Gate | Resultado |
|------|-----------|
| `tests/golden/test_cts_001_v28.py` | 2/2 PASS |
| `tests/golden/test_cts_exam_crucero_v28.py` | 2/2 PASS |
| `tests/golden/test_support_fte_v28.py` | 6/6 PASS (anchors actualizados: E95 aplicado, opt-in verificado) |
| `make validate-excel-v28` | PASS (6/6, 1 skip) |
| `make all` | PASS (test 36 · **verify baseline match (sin drift)** · validate-excel V2-4 match) |
| `make baseline` | NO ejecutado (no requerido — verify pasa) |

**Hardcodes nuevos en motor: 0** (el 9.5 vive en request.json; precio_mensual viene del request).

### Drift esperado (frozen v27 golden snapshots — NO en make all/verify)

4 anchors `no_payroll` per-canal en `test_cost_to_serve_golden_v27.py` (Voz/WhatsApp) y
`test_vision_tarifas_golden_v27.py` (no_payroll_ch) drift por la corrección CAPEX (ej. Voz 890,666 → 912,667).
Son snapshots congelados de salida backend (deal v27 fixture, NO el deal SAC Excel); solo `no_payroll` cambió
(payroll/salario_fijo/nomina_loaded/costos_fijos intactos → fix quirúrgico). Requieren regeneración de snapshot
(`SNAPSHOT_REGENERATION_REQUIRED`, diferido — no se regenera sin aprobación, política CLAUDE.md). < 10 fallos,
explicados contra Excel V2-8. Las otras 24 fallas v27 son pre-existentes (`GOLDEN-001`, productiva 2026).

---

## P3 — Estructura salarial C37/C38 (`CTS_SALARY_ADDITIVE_STRUCTURE`, 2026-06-12)

**Excel V2-8 `Nomina Loaded`!205 ← `Inputs de Nomina`!D62** = comisión CRUDA (`salario_base × comision_pct` =
600,000 para SAC), indexada (row 198 = `$C198 × factor_indexación`). **SIN factor de cumplimiento (0.70)** y
sin carga social adicional. `Vision CTS`!C38 (Salario Variable) = Σ canales × idx; C37 (Salario Fijo) = C36 − C38
(partición; el carve-out es idéntico en Excel y backend — la antigua hipótesis "aditiva" era una lectura errónea).

**Bug backend (`nomina.py:_comisiones`):** aplicaba `× pct_cumplimiento_variable (0.70)` a la línea de costo
variable, que NO existe en la columna D62 del Excel. Como `salario_fijo = total_cargado − comisiones`, el 0.70
inflaba salario_fijo (carve-out) y reducía la variable, distorsionando el split sin cambiar el total.

**Fix:** removido `× pct_cumplimiento_variable` de `_comisiones` (variable = `salario_base × FTE × comision_pct ×
idx` = comisión cruda Excel D62). **Total-invariante** (`fijo + variable = total_cargado`) → C34/C36/PyG/Tarifas/
baseline NO cambian; solo se corrige el split C37/C38.

| Componente | Celda | Excel | Backend ANTES | Backend DESPUÉS | Δ después |
|------------|-------|-------|---------------|-----------------|-----------|
| Salario Fijo | C37 | 4629.49 | 4890.60 (+261.11) | 4678.83 | **+49.35** |
| Salario Variable | C38 | 775.74 | 494.12 (-281.63) | 705.88 | **-69.86** |
| Nomina Loaded | C36 | 5405.23 | 5384.72 (-20.51) | 5384.72 | -20.51 (invariante) |
| Payroll | C35 | 5462.36 | 5437.997 (-24.36) | 5437.997 | -24.36 (invariante) |
| Cost To Serve | C34 | 6224.58 | 6197.05 (-27.53) | 6197.05 | -27.53 (invariante) |

C37 y C38 mejoran **individualmente** ~212 COP/tx cada uno; **sin compensación falsa** (C34 invariante).

**Residual (frente separado `CTS_VARIABLE_INDEXATION_AGING` / staff-commission):** C38 -69.86 / C37 +49.35.
Excel C38 incluye (a) envejecimiento por indexación de la comisión agente (factor ≈1.0989 sobre la cruda) y
(b) comisión cruda de roles de soporte (Director `Inputs de Nomina`!D39=3,868,125 / Jefe D46=1,500,000 /
Supervisor D57=700,000) sumada a la variable — `C198 Voz1` = 86.67M incluye 8.67M de soporte sobre 78M de agentes.
El backend lleva la comisión de soporte dentro del cargado (provider W-override `costo_empresa_override`), no en
la línea variable, y `comision_rol=0` para staff en el request. Cerrar esto requiere descomponer el override
staff en base+comisión o poblar `comision_rol` + reestructurar → toca provider/request/indexación (afecta total →
`STOP_LARGER_NOMINA_REDESIGN`). **Diferido.** Hardcodes nuevos: 0.

Gates: CTS 2/2 · nomina_variable_load 2/2 · exam/crucero 2/2 · support FTE 6/6 · validate-excel-v28 6/6 ·
`make all` PASS (verify baseline match, sin drift). Golden suite: **0 fallos nuevos** vs HEAD (diff before/after = ∅).
Las 3 fallas `test_pyg_v28_ingreso_indexado` son pre-existentes (drift de E95 sobre payroll, commit bbdb94f),
NO de este cambio (invariante respecto a PyG).

---

## P4 — Comisión variable de staff (`CTS_VARIABLE_COMMISSION_STAFF`, 2026-06-12)

**Corrección de diagnóstico previo:** la hipótesis "envejecimiento por indexación ≈1.0989" era **FALSA**.
Verificado con `openpyxl`: las filas de nómina de Vision CTS son **PLANAS los 24 meses** (`Nomina Loaded`!108
fijo = 515,206,200 constante; !198 variable = 86,673,274 constante) — **no hay aging**. Además los **agentes
YA coinciden** exactamente: Excel fijo agente = `Agente Básico 1` row 63 = 384,926,602 = 130×(W62−D62) = (loaded
− comisión cruda), **partición idéntica al backend** (no aditiva). Backend agentes: fijo 3483.50 = Excel 3483.50,
var 705.88 = Excel 705.88. MATCH.

**Causa raíz real = comisión variable de roles de SOPORTE.** El bloque variable de Excel (`Nomina Loaded` filas
155-181) suma comisión por rol = `Inputs de Nomina`!D-col × FTE-staff:
- Supervisor: D57(700,000) × **9.5 FTE (E95)** = 6,650,000
- Jefe de Operación: D46(1,500,000) × FTE = 1,290,909 (Voz1)
- Director de cuentas: D39(3,868,125) × FTE = 732,365 (Voz1)

El backend tenía `comision_pct=0` para staff → variable de soporte = 0 (la comisión quedaba dentro del cargado
fijo). Staff variable Excel = 171,439,248 − 156,000,000 (agentes) = 15,439,248/mes = **69.86 COP/tx** = exactamente
el residual C38.

**Fix (`tests/refactor/_v28_deal_provider.py`, `_V28_STAFF_COMISION`):** poblar `salario`(=Excel C) y
`comision_pct`(=Excel D/C) para Director/Jefe/Supervisor (filas existentes + alias accent-stripped, porque
`get_comision_pct_rol` usa `.lower()` sin quitar acentos y "jefe de operación" no resolvía). Particiona igual que
agentes: `salario_fijo = total_cargado − comisiones` → comisión de staff entra a la variable, sale del fijo,
**total de soporte invariante**. Sin hardcode en `modules/` (valores en el test provider, trazables a Excel C/D).
`salario` de soporte alimenta SOLO la línea de comisión (el cargado viene de `costo_empresa_override`).

| Componente | Celda | Excel | Backend ANTES | Backend DESPUÉS | Δ después |
|------------|-------|-------|---------------|-----------------|-----------|
| Salario Fijo | C37 | 4629.49 | 4678.83 (+49.35) | 4608.97 | **-20.51** |
| Salario Variable | C38 | 775.74 | 705.88 (-69.86) | 775.74 | **+0.0000 EXACT** |
| Nomina Loaded | C36 | 5405.23 | 5384.72 (-20.51) | 5384.72 | -20.51 (invariante) |
| Payroll | C35 | 5462.36 | 5437.997 (-24.36) | 5437.997 | -24.36 (invariante) |
| Cost To Serve | C34 | 6224.58 | 6197.05 (-27.53) | 6197.05 | -27.53 (invariante) |

C38 **EXACTO**; C37 mejora (+49.35 → -20.51); C34/C35/C36 invariantes (**sin compensación falsa**).

**Clasificación: `PROVIDER_VALUE_MISMATCH`** (comisión staff existe en Excel `Inputs de Nomina` D-col; el provider
devolvía 0). **Residual restante = `CTS_SUPPORT_LOADED_MAGNITUDE`:** C37/C36 -20.51 = el cargado de soporte del
backend (`costo_empresa_override` W) está ~20.51 COP/tx por debajo del Excel (precisión de los overrides W /
composición de FTE de soporte). Frente separado, menor. C35 -24.36 = C36 + cap/exám/crucero (-3.85); C34 -27.53
= C35 + costos_fijos (-3.17). Hardcodes nuevos en `modules/`: 0.

Gates: CTS 2/2 · nomina_variable_load 2/2 · exam/crucero 2/2 · support FTE 6/6 · validate-excel-v28 6/6 ·
`make all` PASS (verify baseline match, sin drift). Golden suite: **0 fallos nuevos** vs HEAD. Baseline: NO requerido.

---

## §P5 — Cierre temporal CTS-001 known_delta (2026-06-12)

**Estado**: `CTS-001_FUNCTIONAL_PARITY_WITH_KNOWN_DELTA`
**Residual**: -27.53 COP/tx (0.44%)
**FULL_MATCH**: NO — `MAX_DELTA = 0.000001` no se cumple
**Decisión**: diferir `CTS_SUPPORT_LOADED_MAGNITUDE` hasta completar mapa general de fórmulas V2-8

| Componente | Celda | Excel | Backend | Δ | Status |
|------------|-------|-------|---------|---|--------|
| Cost To Serve (total) | C34 | 6,224.575126 | 6,197.048 | **-27.53 (0.44%)** | KNOWN_DELTA_DEFERRED |
| Payroll | C35 | 5,462.356 | 5,437.997 | -24.36 | KNOWN_DELTA_DEFERRED |
| Nomina Loaded | C36 | 5,405.230 | 5,384.720 | -20.51 | `CTS_SUPPORT_LOADED_MAGNITUDE` |
| Salario Fijo | C37 | 4,629.49 | 4,608.97 | -20.51 | KNOWN_DELTA_DEFERRED |
| Salario Variable | C38 | 775.74 | 775.74 | **+0.0000** | EXACT ✅ |
| OPEX Fijo | C46 | 308.138 | 308.138 | **0.0000** | EXACT ✅ |
| CAPEX/Inversiones | C47 | 103.044 | 103.044 | **+0.0000** | EXACT ✅ |
| Supervisor SAC FTE | E95 | 9.5 | 9.5 | 0.0 | EXACT ✅ (override) |

Razón del pause:
- El residual -20.51 (`CTS_SUPPORT_LOADED_MAGNITUDE`) requiere auditar overrides W staff
  (`Inputs de Nomina`!W39:W58) y la composición de FTE de soporte — trabajo de mayor scope.
- Completar el mapa de fórmulas general V2-8 dará mejor contexto para aislar si el override W
  es la única raíz o si hay un gap estructural adicional en la dotación de soporte.
- No se declara FULL_MATCH: el umbral estricto no se cumple y declararlo sería incorrecto.

Siguiente frente: `V28_ENGINE_FORMULA_MAP_CONTINUATION` — ver `v28_backlog.md`.
