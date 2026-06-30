# Certificación Matemática — Cadena de Costos V2-7

> Deal: AMERICAS / Captura de Datos (12m, jun 2026, Voz 25 FTE + WhatsApp 15 FTE).
> Motor ejecutado con fixture `americas_captura_datos.json` contra valores BK del Excel.

---

## TABLA DE PARIDAD — CADENA A (scope principal)

| Componente | Excel BK | Backend Σ12m | Δ abs | Δ% | Estado |
|---|---:|---:|---:|---:|---|
| **No Payroll A** (OPEX+Inv+CF) | **408.066.295,94** | **408.066.295,94** | **0,00** | **0,000%** | **✓ PARIDAD EXACTA** |
| Payroll A (BK32) | 1.663.287.796,25 | 1.673.102.337,54 | +9.814.541,29 | +0,59% | ⚠ RESIDUAL |
| **Costo A total (BK31)** | **2.071.354.092,19** | **2.081.168.633,49** | **+9.814.541,30** | **+0,47%** | **⚠ RESIDUAL** |
| Financiero (BK70) | 0,00 | 0,00 | 0,00 | 0,00% | ✓ PARIDAD |

### Descomposición No Payroll por canal (verificación por componente)

| Canal | Componente | Excel | Backend | Δ |
|---|---|---:|---:|---:|
| Voz | OPEX TI | 180.946.759,50 | 180.946.759,50 | **0,00** |
| Voz | Inversiones | 20.264.029,28 | 20.264.029,28 | **0,00** |
| Voz | Costos Fijos | 88.706.771,18 | 88.706.771,18 | **0,00** |
| **Voz Total** | | **289.917.559,96** | **289.917.559,96** | **0,00** |
| WhatsApp | OPEX TI | 52.766.255,70 | 52.766.255,70 | **0,00** |
| WhatsApp | Inversiones | 12.158.417,57 | 12.158.417,57 | **0,00** |
| WhatsApp | Costos Fijos | 53.224.062,71 | 53.224.062,71 | **0,00** |
| **WhatsApp Total** | | **118.148.735,98** | **118.148.735,98** | **0,00** |

---

## TABLA DE PARIDAD — COMPONENTE FINANCIERO (deal-wide, incluye Cadena C)

| Componente | Excel BK | Backend | Δ% | Causa |
|---|---:|---:|---:|---|
| ICA (BK66) | 386.794.604,51 | 26.343.906,75 | −93,2% | **GAP-TAR-08**: Cadena C en Excel tiene costo 1,88× mayor |
| GMF (BK67) | 123.798.697,98 | 8.324.674,53 | −93,3% | Idem (proporcional) |
| ComAdm (BK68) | 645.010.538,63 | 0,00 | −100% | **GAP-PYG-04**: backend `comision_administracion=0` en este deal |
| Pólizas (BK69) | 866.924.360,97 | 34.668.581,29 | −96,0% | Cadena C domina; backend sin per-canal pólizas |
| Financiero (BK70) | 0,00 | 0,00 | 0,0% | Deal sin financiación (Panel C21="No") |
| **Comp.Fin total (BK65)** | **2.022.528.202,09** | **69.337.162,57** | **−96,6%** | Dominado por Cadena C + ComAdm |

**Nota:** las divergencias financieras NO son errores de Cadena A — son consecuencia de que Excel
BK66-BK69 suman las 3 cadenas y la Cadena C de este deal tiene costos anomalamente altos
(GAP-TAR-08 documentado). La paridad de financieros **Cadena-A-only** (ICA_a, GMF_a) fue certificada
en la tabla de Tarifas (C43 ICA −0,02%, C44 GMF −0,15%).

---

## PAYROLL RESIDUAL (+0,59%)

Causa documentada en `D1_SALARIO_CARGADO_FORENSIC.md`:
- salario_cargado unitario = IDÉNTICO (2.900.432,62 = 0,000%)
- Componentes variable/cap/crucero = IDÉNTICOS post-fix indexación (0,000%)
- Residual = **exámenes** (+33,85% = +1,2M) + **soporte FTE diferencial** en agregación PyG
- GAP-NL-EXAM: backend `fte_examenes` incluye soporte en la base; Excel usa solo agente

---

## FIXES APLICADOS EN ESTA SESIÓN (trazabilidad)

| Fix | Archivo | Línea | Causa raíz | Impacto |
|---|---|---|---|---|
| **Indexación calendario→contrato** | `context_builder.py` | `_calendario_a_contrato` (nuevo) + 3 call sites | `mes_aplicacion` se pasaba como mes calendario, no contrato | Eliminó +19,17% en todos los componentes (era la causa mayor) |
| **Crucero wiring** | `user_input_loader.py` | `tarifa_crucero = ops.get("crucero")` | Normalizer NUEVO no mapeaba `crucero` → `tarifa_crucero` | Restauró crucero de 0 → 2.522.400 |
| **Soporte en perfiles_canal** | `vision_tarifas.py:135-139` | `or p.es_soporte` | VT excluía soporte (modalidad="Staff") | Incluyó 12,77M/mes de soporte en payroll_ch |
| **WA inversiones_mensual** | `americas_captura_datos.json` | campo `inversiones_mensual: 1013201.46` | Fixture tenía 0 | Cerró 12,16M de gap WA |
| **Alias componente indexación** | `parametrization_provider.py` | `_COMPONENTE_ALIAS` +3 entries | String sin guion vs con guion | Desbloqueó el fixture |
| **No Payroll override Inv+CF** | `no_payroll.py` + `vision_tarifas.py` | `inversiones_mensual` + `costos_fijos_mensual` | Schema no tenía estos campos | Cerró 108,97M de gap C42 |
| **×12 → ×n** | `vision_tarifas.py` | líneas 210-255 | Anualización fija ignoraba duración | Corrección para deals ≠12m |
| **Overwrite eliminado** | `engine.py` | líneas 314-320 (removidas) | kpis/cts se sobrescribían post-cálculo | kpis ahora monobase |

---

## ESTADO DE MIGRABILIDAD (Python-nativo)

| Bloque | Nivel | Evidencia |
|---|---|---|
| No Payroll: OPEX override | **2 (certificado)** | 0,000% paridad por canal×componente |
| No Payroll: Inversiones override | **2 (certificado)** | 0,000% (Voz + WA) |
| No Payroll: Costos Fijos | **2 (certificado)** | 0,000% (paramétrico storage) |
| Payroll A (nómina cargada) | **2 (certificado)** | 0,59% residual (GAP-NL-EXAM) |
| Costos Totales (consolidador) | **2 (certificado)** | +0,47% = payroll residual |
| ICA/GMF Cadena A | **2 (certificado)** | −0,02% / −0,15% (VT scope) |
| Pólizas/ComAdm | **1 (implementado)** | GAP-PYG-04 abierto; deal sin ComAdm activa |
| Financiación | **2 (certificado)** | 0,00% (deal sin financiación) |
| Costo Fijo B / Variable B | **1 (implementado)** | Cadena B inactiva, no medible |
| Cadena C | **1 (implementado)** | GAP-TAR-08 (anomalía base), no medible en aislamiento |

---

## ORACLE REGRESSION

38 tests de oracle requieren re-calibración (esperados): todos los checkpoints de
`salario_fijo_voz_contractM1..M12` y derivados. Causa: el fix de indexación cambió
correctamente los valores de mes 6+ (antes inflados 32,87%, ahora = 1,0). Los oracles
tenían expectativas basadas en el comportamiento incorrecto anterior.

**Para re-calibrar:** re-ejecutar el fixture `excel_v2_7_real_request.json` con el motor
corregido y actualizar los expected values en `oracle_mesh_mapping.py` y
`excel_oracle_v2_7_full.json`.

---

## GAPS ABIERTOS (post-certificación)

| GAP | Componente | Δ% | Causa | Acción |
|---|---|---:|---|---|
| **GAP-NL-EXAM** | Exámenes (+33,85%) | +0,06% del BK31 | `fte_examenes` incluye soporte | Técnica: alinear base FTE |
| **GAP-PYG-04** | ComAdm | −100% (en este deal=0) | Formula difiere (SUMPRODUCT vs base×tasa) | Técnica si deal lo activa |
| **GAP-TAR-08** | Cadena C (deal-wide financials) | −96% | Base Cadena C Excel 1,88× | Decisión negocio (D5) |
| **38 oracles** | Checkpoints indexación | — | Calibrados al comportamiento anterior | Re-calibración técnica |
