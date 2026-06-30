# STAKEHOLDER BRIEFING — NEXA Backend Engine V2-7

**Audiencia:** Product Owner, Tech Lead, Stakeholders comerciales
**Branch:** `refactor/engine-v2`
**Estado:** Pausa controlada — esperando decisiones Q1-Q6 antes de F4 implementación
**Fecha:** 2026-05-28
**Autor:** Equipo de motor (Semantic Reconstruction Program)

---

## 1. Estado actual honesto

| Métrica | Valor | Lectura |
|---|---|---|
| Suite tests | **918 passed / 162 failed / 25 skipped** | 162 failures son **legítimos** — el mesh F6 expone drift real contra Excel V2-7. NO son regresiones. |
| Paridad real (mesh) | **22 / 161 checkpoints passing (~14%)** | NO es el "39/39 ≤ 0.01%" que afirmaba el reporte W15. Esa cifra fue refutada en W16 (forense). |
| Stages limpios | `COSTO_B`, `RAMPUP` | Único territorio en paridad numérica. |
| Stages críticos | `COSTOS_FINANCIEROS 28/28 fail 96.66%`, `NO_PAYROLL_A 7/7 fail 67.55%`, `PAYROLL_A median 14.37%`, `COSTO_C 100%` | Drift concentrado y categorizable. |
| PR W1-W8 | `[DO NOT MERGE]` | Sin cambio. Vigente hasta cerrar F4-F5. |

**Conclusión honesta:** el motor V2-7 NO está en paridad con Excel. La afirmación
original W1-W15 ("paridad certificada ≤ 0.01% en 39/39 celdas") fue una
construcción circular — el oracle se autovalidaba contra los outputs del motor.
W16-W17 lo demostraron. F1-F6 reconstruyen la verdad.

---

## 2. Cronología honesta

| Hito | Resumen |
|---|---|
| **W1-W15** | Afirmadas como "paridad certificada". Reporte W15 publicó la métrica `39/39 ≤ 0.01%`. **Claim falso** descubierto posteriormente. |
| **W16-W17 (auditoría forense)** | Revela que (a) el oracle era circular (validaba motor contra sí mismo); (b) existen **8 hacks** (H1-H8) hardcodeados; (c) la "certificación" no era reproducible desde Excel real. |
| **W18 (rampup)** | Cerrada divergencia estructural Captura de Datos. |
| **W19 (duplicación staff)** | Bug real de duplicación en `_construir_perfiles_soporte` resuelto. |
| **F1** | Bloqueo formal de merge + reemplazo de claims falsos en docs/PR. |
| **F2** | Eliminado hack H1: comision_pct para Director (0.05) y GTR (0.10) era invento; Excel V2-7 lista 0 en E16/E26. Baselines regenerados. |
| **F3** | Runtime Unification. `calculators/pyg.py` y `calculators/vision_tarifas.py` delegan a `domain/`. Mutation detection 2/4 → 5/6. |
| **F4 (audit-only)** | Audit exhaustivo de ICA / GMF / Pólizas / Comisión Admin / Costo Financiación / No-Payroll. **Revela 6 ambigüedades semánticas (Q1-Q6) que requieren decisión de Product Owner antes de implementar fixes.** |
| **F6** | Validation mesh con 1118 celdas Excel + 161 checkpoints + drift heatmap por stage. Reemplaza el oracle circular. |

---

## 3. Hallazgos críticos del F4 audit

1. **Mesh mis-labeled (estructural).** `pyg.polizas` y `pyg.financiacion` en el
   código apuntan a celdas Excel equivocadas. F4.PRE re-mapea antes que cualquier
   implementación. **2h de trabajo, no bloqueado por stakeholder.**

2. **ICA — fuente incorrecta.** Excel calcula ICA usando `Panel!C34 = 0.01` (escalar
   manual). El backend usa la matriz por ciudad (`Tasas, TRM, Polizas!A34:F54` → ej.
   Cali 1.97%). Las dos fuentes producen valores diferentes por ~1.97×.

3. **Excel `H69` overlap.** La fórmula de Pólizas adicionales suma `J12:J163` (rango
   ICA) + `J198:J327` (rango pólizas). El primer SUMPRODUCT es idéntico al rango
   de H66 (ICA). Excel **doble-cuenta ICA dentro de "Pólizas adicionales"** — o es
   un bug de regresión V2-5 → V2-7. **Necesita confirmación PO.**

4. **Factor 0.0118 vs 0.016756.** `D188 = 0.016756` es pre-grossed (`Panel!D45 = 0.0118 / factor_margenes ≈ 0.7039`). Backend usa 0.0118 directo. Off-by-1.42×.

5. **Costo Financiación dormido.** `Panel!C21 = "No"` apaga el stack completo
   (`D365 = 0` → `E370 = 0`). Backend tiene la lógica pero el boolean
   `activa_financiacion` la enmascara. Bug latente.

6. **Excel 365 features.** Las fórmulas de `Pólizas - Costo Financiacion` usan
   `LET`, `FILTER`, `IFERROR` y array spilling. No se pueden traducir trivialmente a
   pandas vectorizado — requieren dispatch per-canal × per-cadena con bracketing
   mensual.

---

## 4. Decisiones pendientes — Q1 a Q6

Cada decisión bloquea o desbloquea un sub-wave de F4. Sin ellas, el equipo NO
puede continuar de forma honesta.

### Q1 — ICA: ¿Panel!C34 o matriz por ciudad?
- **Pregunta:** ¿la tasa ICA debe leerse del escalar manual `Panel!C34 = 0.01` o de la matriz por ciudad?
- **Opciones:**
  - (A) Replicar Excel exactamente → leer `Panel!C34`. Backend pierde la matriz por ciudad como insumo activo.
  - (B) Mantener matriz por ciudad → fix Excel para que use lookup.
- **Implicación código:** (A) elimina rama por-ciudad en `calculators/`; (B) requiere fix Excel + backend.
- **Recomendación técnica:** (A) — Excel es source of truth para certified mode.

### Q2 — ICA bracket double-counting
- **Pregunta:** Excel ICA gross-up incluye `+E198` (pólizas adic) y `+E378` (costo financ) dentro del bracket. Luego H69 y H70 los suman como líneas P&G separadas. ¿Doble conteo intencional o bug?
- **Opciones:** (A) Intencional → certified replica el doble conteo; (B) Bug → backend implementa la versión "limpia".
- **Recomendación técnica:** A clarificar con PO; replicar Excel hasta orden contraria.

### Q3 — H69 J12:J163 overlap (CRÍTICA)
- **Pregunta:** `Visión P&G!H69` suma `J12:J163` (ICA range) + `J198:J327` (polizas range). ¿Bug de template o intencional?
- **Opciones:**
  - (A) Bug en Excel → fix Excel primero, backend implementa versión limpia. **Esfuerzo Excel no estimado.**
  - (B) Intencional → backend replica el doble conteo y se documenta como excepción.
- **Implicación:** sin respuesta a Q3, `F4.C` (Pólizas, 12h) está bloqueado indefinidamente.
- **Recomendación técnica:** ninguna — pregunta de negocio.

### Q4 — Comisión Administración: 0.0118 o 0.016756?
- **Pregunta:** ¿`tasa_comision_administracion` debe ser pre-gross (0.0118) o post-gross (0.016756)?
- **Opciones:** (A) post-gross → backend almacena 0.016756 y elimina factor_margenes inline; (B) pre-gross + cálculo dinámico → backend aplica `/(1-factor_margenes)` en runtime.
- **Recomendación técnica:** (B) — más flexible para escenarios con factor_margenes distinto al default.

### Q5 — `pyg.financiacion` mis-labeling
- **Pregunta:** la variable `pyg.financiacion` del backend, ¿representa Comisión Admin (label actual mal puesto) o Costo Financiación (Excel H70)?
- **Opciones:** (A) renombrar a `pyg.comision_admin` y crear `pyg.costo_financiacion` separado; (B) mantener nombre pero re-mapear semánticamente.
- **Recomendación técnica:** (A) — claridad semántica > backward compat en branch refactor.

### Q6 — No-Payroll rows 107-125
- **Pregunta:** las 19 filas de OPEX no-payroll en Excel (107-125) — ¿enumerar todas como conceptos individuales o agruparlas?
- **Opciones:** (A) 19 conceptos individuales (auditable, alineado con Excel); (B) bucket único `no_payroll_opex` (resumen).
- **Recomendación técnica:** (A) — auditabilidad supera simplicidad.

---

## 5. Roadmap restante post-decisiones

| Sub-wave | Esfuerzo | Bloqueado por | Descripción |
|---|---|---|---|
| F4.PRE | 2h | nada | Re-labeling del mesh (`pyg.polizas`, `pyg.financiacion`). Ejecutable AHORA. |
| F4.A — ICA | 8h | Q1, Q2 | Refactor con bracket gross-up. |
| F4.B — GMF | 2h | Q1, Q2 | Mismo bracket que ICA. |
| F4.D — Comisión Admin | 2h | Q4 | Factor source decision. |
| F4.C — Pólizas | 12h | Q3 (crítica) | Mayor esfuerzo. SUMPRODUCT vector + matriz pólizas. |
| F4.E — Costo Financiación | 4h | Q1, Q3 | Latent — depende de `activa_financiacion`. |
| F4.F — No-Payroll | 10h | Q6 | Inventario 19 filas + mapping a constantes. |
| **F4 total** | **~40h** | Q1-Q6 | |
| F5 — Cadena C HITL | 8-10h | independiente | Reconstrucción semántica de Cadena C. |
| F3.B — Composition residual | 4-6h | independiente | Cierre del legacy_activo residual. |
| **Total restante** | **~50-60h** | | |

---

## 6. Recomendación al stakeholder

1. **Responder Q1-Q6 antes de cualquier implementación F4.** Sin respuestas, el equipo no puede avanzar honestamente — replicar bugs por defecto sería opaco; corregirlos sin autorización sería out-of-scope.
2. **F4.PRE (re-mapping mesh, 2h) puede ejecutarse mientras tanto.** No depende de decisiones.
3. **PR W1-W8 sigue marcado como `[DO NOT MERGE]`.** Eso no cambia con este checkpoint.
4. **Una vez resueltas Q1-Q6, F4 ejecutable en 1-2 sprints** (40h netas), seguido de F5 + F3.B (~15h).
5. **El branch `refactor/engine-v2` queda estable como checkpoint.** Tests determinísticos (918 passed, 162 failed legítimos) — no hay regresión silenciosa.

---

## 7. Riesgos identificados

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Si stakeholders no responden Q3 (J12:J163 overlap), F4.C queda bloqueado indefinidamente. | Mantener checkpoint estable; documentar como pending. |
| R2 | Si stakeholders deciden replicar bugs de Excel (Q2/Q3 = "doble conteo intencional"), eso entra en certified mode como **excepción documentada**. Posible deuda futura cuando Excel se corrija. | `ExecutionCertificate` ya incluye flags para excepciones documentadas. |
| R3 | Si stakeholders deciden corregir Excel primero (Q3 → bug template), el esfuerzo **no está estimado**. Requiere alcance del equipo de modelado financiero. | Sin estimación honesta posible hoy. |
| R4 | La paridad 14% del mesh implica que cualquier release comercial actual exhibe drift contra Excel comercial. Riesgo reputacional si stakeholders externos comparan. | `[DO NOT MERGE]` vigente — no shippeable hasta cerrar F4-F5. |
| R5 | Excel 365 features (LET/FILTER/IFERROR) en Pólizas no son traducibles trivialmente. Pueden requerir biblioteca de cómputo simbólico o emulación manual. | Documentado en F4.C; estimación 12h asume traducción manual. |

---

## 8. Anexos

- `docs/v27/F2_REPORT.md` — F2 (comision_pct fix + baseline regen)
- `docs/v27/F3_REPORT.md` — F3 (runtime unification)
- `docs/v27/F3_RUNTIME_INVENTORY.md` — Inventario completo `calculators/` ↔ `domain/`
- `docs/v27/F4_AUDIT.md` — Audit financiero exhaustivo (758 líneas)
- `docs/v27/F6_REPORT.md` — Mesh + drift heatmap
- `docs/v27/F6_MESH_CATALOG.md` — Catálogo de 1118 celdas
- `tests/parity/DRIFT_HEATMAP.md` — Visualización drift por stage
- `docs/v27/SEMANTIC_RECONSTRUCTION_PROGRAM.md` — Programa global
- `docs/v27/W16_VERIFICATION_REPORT.md` — Auditoría forense que destruyó el claim W15

---

**Status:** awaiting stakeholder Q1-Q6 decisions. F4.PRE ejecutable en paralelo.
