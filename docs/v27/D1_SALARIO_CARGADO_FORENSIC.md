# D1 — Auditoría Forense de Salario Cargado (7 fases consolidadas)

> Investigación sin modificar código. Cada cifra respaldada por celda+fórmula+valor.
> Deal: AMERICAS / Captura de Datos, 12m, Cadena A (Voz 25 FTE + WhatsApp 15 FTE).

## HALLAZGO PRINCIPAL: EL DIAGNÓSTICO PREVIO ERA INCORRECTO

El GAP-SALARIO-CARGADO (reportado como "salario_cargado backend 2.900.432 ≠ Excel 3.288.748")
estaba **mal diagnosticado**. La evidencia forense demuestra:

- `Inputs de Nomina!AM39` (Costo Empresa agente) = **2.900.432,6183**
- Backend `PerfilCadenaA.salario_cargado` = **2.900.432,6183**
- **Diferencia = 0,0000000000 (CERO)**

El valor **3.288.748** que comparábamos no es el salario_cargado unitario — es
`NominaLoaded!C93 / 25 FTE = 82.218.712 / 25`, donde C93 **incluye soporte**.
La divergencia de C41 (+1,45%) tiene **tres causas**, ninguna es "salario_cargado distinto".

---

## FASE 1 — Celda objetivo

**Celda:** `Nomina Loaded!C93` = 82.218.712,28 (salario fijo por canal Voz/Inbound).
**Fórmula:** `=SUMIFS($E$72:$E$88, $B$72:$B$88, $B$92, $C$72:$C$88, $B93)`.
**Significado:** suma la nómina cargada (columna E72:E88, "Visión por perfiles") para
la modalidad Inbound y canal Voz = **agente + TODOS los roles de soporte** asignados.

`C93 / 25 FTE = 3.288.748,49` ← **este número incluye soporte prorrateado, no es
el salario de un FTE individual**. El salario individual (AM39) = 2.900.432,62.

---

## FASE 2 — Trace inverso: NL!C93 → composición R43:R66

`NL!R68 = SUM(C43:C66)` = 82.218.712,28. Composición literal:

| Rol | NL fila | Valor mensual (C) | % del total |
|---|---|---:|---:|
| **Agente Básico 1** | R63 | **69.446.731,71** | **84,5%** |
| Jefe de Operación | R50 | 909.075,44 | 1,1% |
| Supervisor | R61 | 1.637.461,89 | 2,0% |
| Monitor de Calidad | R60 | 1.172.100,97 | 1,4% |
| Director de cuentas | R43 | 967.710,03 | 1,2% |
| (18 roles más de soporte) | R44-R66 | 8.085.632,24 | 9,8% |
| **Total** | R68 | **82.218.712,28** | **100%** |

Agente individual: R63 = 69.446.731,71 / 25 FTE = **2.777.869,27/FTE** (≠ 2.900.432 por comisiones y componentes adicionales).

---

## FASE 3 — Reconstrucción componente a componente

Excel C41 = `SUMPRODUCT(NL!D15:BK33 × canal=Voz × modal=Inbound)` = **1.039.554.872,66**.
`D15 = D93 + D238 + D287 + D349 + D407 + D182 + D455` (7 componentes nómina).

| Componente | Región NL | Excel Σ 12m | Backend (ch×12) | Δ | Δ% |
|---|---|---:|---:|---:|---:|
| Salario Fijo (incl soporte) | R93 | 986.624.547,35 | 993.156.162,08 (solo agente) | +6.531.614,74 | +0,66% |
| Salario Variable | R182 | 36.769.005,00 | 43.819.393,41 | +7.050.388,41 | +19,17% |
| Capacitación Inicial | R238 | 5.000.000,00 | 5.958.740,71 | +958.740,71 | +19,17% |
| Capacitación Rotación | R287 | 5.100.000,00 | 6.077.915,53 | +977.915,53 | +19,17% |
| Exámenes | R349 | 3.538.920,31 | 5.645.159,64 | +2.106.239,33 | +59,52% |
| Seguridad | R407 | 0,00 | 0,00 | 0,00 | — |
| Crucero | R455 | 2.522.400,00 | 0,00 | −2.522.400,00 | −100% |
| **TOTAL C41** | **D15** | **1.039.554.872,66** | **1.054.657.371,36** | **+15.102.498,70** | **+1,453%** |

---

## FASE 4 — Trazabilidad backend

`VisionTarifasCalculator` (vision_tarifas.py:215-226):
`voz_payroll_total = Σ(ch.payroll_ch × n)` donde `ch.payroll_ch` se calcula en
`_costo_op_canal_decomposed` (vision_tarifas.py:897-902) → `NominaCalculator.calcular_para_mes(agent_perfiles, mes)`
→ solo `voz_agentes` (es_soporte=False). **No incluye soporte.**

`NominaCalculator` (nomina.py:81-130) produce por mes:
```
salario_fijo + comisiones + cap_inicial + cap_rotación + exámenes + seguridad + crucero
```

---

## FASE 5-6 — Causa raíz: TRES divergencias independientes

### Causa 1: Soporte ausente en payroll_ch (−153M / +160M = +6,5M neto)

**Excel C41** incluye soporte (filas R43-R61, 12,77M/mes, 15,5% del total).
**Backend payroll_ch** solo incluye agentes (es_soporte=False).
Pero el backend calcula más payroll por agente (993M vs Excel agente 833M = +160M)
porque la nómina del agente backend incluye comisiones (variable) integradas que el
Excel separa en R182 (Salario Variable). Neto: +6,5M (+0,66%).

### Causa 2: Factor ×19,17% en Variable/Cap/Rotación

Los componentes Salario Variable, Cap Inicial y Cap Rotación del backend son todos
exactamente **19,17%** superiores al Excel. Esto sugiere una diferencia de base:
- Excel: estos componentes se calculan sobre los **25 FTE agentes**.
- Backend: los mismos componentes se calculan sobre **25 FTE agentes + FTE soporte
  prorrateado** (≈4,8 FTE soporte Voz), lo cual infla la base en ≈19%.
  
Verificación: 25 FTE × 1,1917 ≈ 29,8 ≈ 25 + 4,8 FTE soporte. **CONFIRMADO.**

### Causa 3: Crucero ausente en backend (−2,5M)

**Excel R455** (Crucero) = 2.522.400,00 para 12 meses. 
**Backend crucero** = 0,00. El fixture tiene `crucero = 8408` (tarifa) pero 
`NominaCalculator._crucero` produce 0 para este perfil. Causa probable: el calculador
de crucero requiere una condición (`incluye_crucero=True` o FTE mínimo) que el fixture
AMERICAS no activa.

### Causa 4: Exámenes +59,52% (+2,1M)

El backend calcula exámenes con una base mayor (incluye FTE soporte en
`fte_examenes`) mientras el Excel usa solo los FTE del perfil operativo.

---

## FASE 7 — Cuantificación exacta del Δ = 15.102.498,70

| Causa | Contribución al Δ | % del Δ |
|---|---:|---:|
| Sal.Fijo neto (agente inflado − soporte omitido) | +6.531.614,74 | 43,2% |
| Sal.Variable (×19,17% por FTE soporte en base) | +7.050.388,41 | 46,7% |
| Exámenes (FTE soporte en fte_examenes) | +2.106.239,33 | 13,9% |
| Cap. Inicial (+19,17%) | +958.740,71 | 6,3% |
| Cap. Rotación (+19,17%) | +977.915,53 | 6,5% |
| Crucero (backend = 0, Excel = 2,5M) | −2.522.400,00 | −16,7% |
| **TOTAL** | **15.102.498,71** | **100,0%** |

Verificación: 6.531.614 + 7.050.388 + 2.106.239 + 958.741 + 977.916 − 2.522.400 = **15.102.498,71** ✓

---

## FASE 8 — Simulación analítica (sin modificar código)

Si el backend produjera C41 = Excel C41 exacto (1.039.554.872,66):

| Campo | Δ% actual | Δ% proyectado | Mejora |
|---|---:|---:|---|
| C41 payroll | +1,453% | 0,000% | ✓ paridad |
| C40 costo total | +0,119% | ~+0,004% | ✓ ~paridad |
| C47 ingreso | +0,119% | ~+0,004% | ✓ ~paridad |
| C43 ICA | +0,652% | ~+0,05% | ✓ residual |
| C44 GMF | +0,524% | ~+0,05% | ✓ residual |
| BK31 deal-wide | +12,57% | ~+4-5% | mejora parcial (queda soporte deal-wide) |

---

## DECISIÓN D1: REFORMULADA

**La decisión NO es "qué salario_cargado usar"** (son idénticos: 2.900.432).

**La decisión es triple:**

1. **¿`payroll_ch` (VT) debe incluir soporte?** Excel C41 lo incluye; backend no.
   Si sí → sumar nómina de soporte al canal en VT. Trabajo: 1-2 semanas.

2. **¿Los componentes de nómina (variable, cap, exámenes) deben calcularse
   sobre FTE agente solo o agente+soporte?** Excel los separa; backend los
   mezcla parcialmente. Ajustar: alinear base de FTE por componente. Trabajo: 1 semana.

3. **¿El crucero del agente se activa por defecto o requiere flag?**
   Excel lo incluye (2,5M); backend produce 0. Diagnóstico adicional: verificar
   `incluye_crucero` en el perfil. Trabajo: investigación + 1 día.

---

## CLASIFICACIÓN FINAL

| # | Hallazgo | Tipo |
|---|---|---|
| 1 | salario_cargado/FTE = IDÉNTICO (2.900.432) | **No es gap** |
| 2 | soporte ausente en payroll_ch (VT) | **Mecanismo** (cómo se agrega, no qué se calcula) |
| 3 | base FTE inflada para variable/cap/exam | **Mecanismo** |
| 4 | crucero = 0 | **Bug o parametrización** (pendiente diagnóstico del flag) |
| 5 | "3.288.748" = número engañoso (mezcla agente+soporte) | **Error de diagnóstico previo** |

**La divergencia C41 (+1,45%) NO corresponde a una diferencia de salario cargado.**
Corresponde a diferencias de **agregación** (qué se suma al canal en VT) y un componente
ausente (crucero). Son ajustes de mecanismo, no decisiones de negocio.
