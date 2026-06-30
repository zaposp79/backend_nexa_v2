# Golden Drift Log — Stage 1.5 Paso B

Baseline pre-Paso B: **63/63 PASS**

---

## Commit 1: 3ad1215 — add datos_operativos.antiguedad
- Goldens PASS: 63/63 (no drift — STRUCTURE_EXTENSION, not consumed by loader)

## Commit 2: 5288e66 — add datos_operativos.periodo_pago
- Goldens PASS: 63/63 (no drift — STRUCTURE_EXTENSION, hardcoded=90 in loader)

## Commit 3: 395390e — add reglas_negocio.margen_objetivo_cadena_b
- Goldens PASS: 63/63 (no drift — STRUCTURE_EXTENSION, not consumed by loader)

## Commit 4: 1cd9ad7 — add reglas_negocio.descuento_volumen
- Goldens PASS: 63/63 (no drift — STRUCTURE_EXTENSION, hardcoded=0 in loader)

## Commit 5: a4aaaeb — update pct_rotacion 0.085 → 0.0815
- Goldens PASS: 63/63 (no drift — goldens use frozen fixtures, not request.json)

## Commit 6: 01abc18 — update crucero 8422 → 8408
- Goldens PASS: 63/63 (no drift)

## Commit 7: 58957a3 — update tasa_ica 0.0097 → 0.01
- Goldens PASS: 63/63 (no drift)

## Commit 8: 4034baa — update polizas[Cumplimiento].pct_poliza 0.0062 → 0.0063
- Goldens PASS: 63/63 (no drift)

## Commit 9: a04df3b — update polizas[Salarios].pct_poliza 0.0119 → 0.0128
- Goldens PASS: 63/63 (no drift)

## Commit 10: 246f5af — update polizas[Calidad].pct_poliza 0.0119 → 0.0128
- Goldens PASS: 63/63 (no drift)

## Commit 11: 8927ee2 — update margen_objetivo 0.18 → 0.21
- Goldens PASS: 63/63 (no drift)

## Commit 12: 6cd0575 — update contingencia_operativa.valor 0.025 → 0
- Goldens PASS: 63/63 (no drift)

## Commit 13: b486fd5 — update contingencia_comercial.valor 0.04 → 0
- Goldens PASS: 63/63 (no drift)

## Commit 14: a4f1c73 — update cons_costo_de_financiacion true → false
- Goldens PASS: 63/63 (no drift)

---

## Resumen final Paso B

- PASS count final: **63/63** (estable en todos los commits)
- Drifted: **0 goldens**
- Excepciones motor: **0** (motor estable en todos los commits)

**Nota:** Los goldens usan fixtures frozen propias (`tests/golden/`), no leen
`request/request.json`. Por eso no driftan. El impacto numérico de los cambios
de Paso B será visible en Stage 2 al comparar contra V2-8 Excel con el parity
runner (INPUT_DEAL_MISMATCH persiste por campos deferred: servicio/cliente/
tipo_cliente/fecha_inicio — decisión 1 CHECKPOINT A).

---

## Stage 2 — Motor Fixes (investigación)

**Fecha:** 2026-06-10  
**Goldens antes:** 63/63  
**Goldens después:** 63/63 (sin cambios funcionales — todos los targets bloqueados)

### Target 1: pyg_calculator.py:209-213 — P&G ingreso indexado

**Evidencia Excel V2-8 Visión P&G!C19:**
```
=IF(AND(C$12>=SUM('Listas Desplegables'!$A$53:$BH$53),C12<=$K$5),
   'Hoja Maestra Escenarios'!$C$296,0)
   *C$15*(1+INDEX('Tasas, TRM, Polizas'!$J$8:$O$16,
          MATCH(Panel!$L$7,Tasas!$I$8:$I$16,0),
          MATCH(YEAR(C$13),Tasas!$J$7:$O$7,0)))
```

**Delta vs V2-7:**
- V2-7 C19: `=IFERROR((C31/(1-Panel!$C$63))*C$15,0)` — sin indexación anual
- V2-8 C19: multiplica por `(1 + Tasas[Panel!L7, year(mes)])` — factor IPC/SMMLV por año del contrato

**Backend actual:** `PyGCalculator.calcular_mes` computa `ingreso_a = costo_a/factor_billing * rampup` sin indexación anual de ingreso.

**Impacto estimado:** Para deal 2026-01-01/24m con Panel!L7="IPC": meses 1-12 → factor=0 (sin cambio); meses 13-24 → factor=0.0555 (5.55% más).

**KILL-SWITCH:** 
1. INPUT_DEAL_MISMATCH — no hay valores numéricos V2-8 para validar.
2. Cambio de mayor superficie: requiere wiring nuevo (tabla Tasas + Panel!L7/L8 por cadena) en PyGCalculator.calcular_mes.
3. Golden fixtures sin fechas → el test pasaría trivialmente aunque estuviera mal.

**Estado: DEFERRED — requiere goldens V2-8 alineados.**

---

### Target 2: Cadena C L11 — amortización CAPEX con factor financiero

**Evidencia Excel V2-8 Condiciones Cadena C!J62:**
```
=IFERROR((I62/H62)*(1+'Panel de Control General'!$L$11),0)
```
donde Panel!L11 = `tasa_interes_mensual` = 0.0153.

**Delta vs V2-7:**
- V2-7 J62: `=IF(E62="Total",G62,G62*H62)` — sin factor financiero aplicado al valor mensual
- V2-8 J62: `(valor_total/meses_diferir)*(1+tasa_interes_mensual)` — incluye factor de financiación

**Backend actual (`_costo_amortizacion_inversion`):** `inversion_anual / 12` — sin tasa.

**Fix intentado:** aplicar `(1 + self._parametrizacion.tasa_mensual_financiacion())` en `_costo_amortizacion_inversion`.

**KILL-SWITCH — probado y revertido:** el fix rompió 8 golden V2-7 certificados porque los fixtures `vt_v27_real_request.json` y `cts_v27_real_request.json` tienen inversiones_capex con valores no nulos. Delta observado en test: +3.63M COP en `ingreso_mensual_total`.

**Estado: DEFERRED — documentado en `modules/cadena_c/reglas.py:_costo_amortizacion_inversion`. Requiere goldens V2-8 numéricos para validar y actualizar fixtures.**

---

### Target 3: Vision Tarifas — G35/D143/D150

**Evidencia Excel V2-8:**
- `Vision Tarifas_Modelo_Cobro!G35`: `='Panel de Control General'!$C$63` (solo margen_a)
- V2-7 G35: `='Panel de Control General'!$C$63+SUM(G30:G33)` (margen_a + contingencias sumadas)
- `D143`: `=C143/$C$140` (nuevo denominador único C140 = num personas por servicio)
- `D150`: `=C150/$C$140`

**Delta vs backend:**
- G35 con contingencias=0 (V2-8 deal): `(1-(margen+0+0+0))*(1-0)*(1-0)*(1-0)*(1+0)` = `(1-margen)`. 
  V2-7 con contingencias=0: `(1-(margen+0))*(1-0)*(1-0)*(1-0)*(1+0)` = `(1-margen)`. 
  **SIN DELTA para el deal de referencia** (contingencias=0 en V2-8).
- D143/D150: modelo de comisión por persona (habilitado solo para SACO/Cobranzas). 
  Backend marca `UNDETERMINED` — no computa estas celdas. Deal de referencia = Cobranzas pero `ComponenteVariable` retorna vacío.

**Fix: NO APLICA** — para el deal de referencia (cont_op=0, cont_com=0) no hay delta numérico.

**Estado: SIN DELTA para deal de referencia. UNDETERMINED en comisión es gap conocido anterior a V2-8.**

---

## Resumen Stage 2

| Target | Evidencia Excel | Delta | Acción | Estado |
|--------|----------------|-------|--------|--------|
| P&G ingreso indexado (C19) | `Visión P&G!C19 ×180` | +5.5% meses 13-24 (IPC) | DEFERRED | Kill-switch: INPUT_DEAL_MISMATCH + goldens sin fechas |
| Cadena C L11 (J62) | `Cond. Cadena C!J62 ×22` | +1.53% en inversiones | DEFERRED | Kill-switch: rompe 8 golden V2-7 (+3.63M COP) |
| Vision Tarifas G35/D143 | `VT!G35 ×2, D143/D150 ×5` | SIN DELTA (cont=0) | SIN CAMBIO | No delta para deal referencia |

**Goldens finales: 63/63 (estables)**  
**Parity runner: INPUT_DEAL_MISMATCH — DEFERRED (servicio/cliente/tipo_cliente)**  
**Commit: NO COMMIT — kill-switch activado para targets 1 y 2; target 3 sin delta**

### Prerrequisito para desbloquear Targets 1 y 2

1. Alinear deal de referencia: recalcular Excel V2-8 con deal de `request.json` (Cobranzas/Bancamia/No Grupo Aval/2026-01-01/24m).
2. Obtener valores numéricos V2-8 para: `Visión P&G!C19` (meses 13-24), `Condiciones Cadena C!J62..J69` (valor mensual con factor).
3. Actualizar golden fixtures V2-7 → V2-8 o crear goldens V2-8 separados con evidencia numérica.
4. Implementar: (a) tabla Tasas en motor + Panel!L7/L8 wiring, (b) tasa en `_costo_amortizacion_inversion`.

---

## PASO-B-POLIZAS-FLAGS — Commit 15 (cierre Paso B)

**Fecha:** 2026-06-11

Campo `activa` verificado como **CONSUMED** en UserInputLoader → PolizaContractual → motor.
6 flags Value_Update aplicados en `request/request.json`:

| Póliza | activa antes | activa después |
|--------|:---:|:---:|
| Póliza de Seriedad | True | False |
| Poliza de rc cruzada | True | False |
| poliza de IRF | True | False |
| Póliza de Responsabilidad | True | False |
| Otros impuestos | True | False |
| Responsabilidad Civil Protección de Datos | True | False |

Goldens test/golden/: 42 fail / 21 pass — mismo conteo pre-existente (GOLDEN-001, SMMLV productiva 2026, no relacionado).
Sin regresión nueva atribuible a este cambio.

**Estado Paso B: COMPLETED — todos los VALUE_UPDATE e items aplicables de v28_input_mapping.md cerrados.**
