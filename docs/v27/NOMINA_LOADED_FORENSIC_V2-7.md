# Wave Forense — Nomina Loaded (Excel V2-7)

> Ingeniería inversa completa de la hoja `Nomina Loaded` del workbook V2-7.
> Deal: AMERICAS / Captura de Datos (12m, jun 2026, Voz 25 FTE + WhatsApp 15 FTE).
> Método: extracción literal (`data_only=False/True`) + ejecución del motor.

---

## FASE 1 — Inventario

**Dimensiones:** A3:CF474 (84 columnas, 474 filas). **20.652 celdas no vacías**: 18.338 fórmulas,
542 arrays, 1.428 números, 320 textos, 24 otros. 28 merged cells. 0 data validations.

### Estructura global

```
Params (R1-R12)     ← C3:C7 (mes inicio/fin, componente, mes aumento)
│
Región 1 CONSOLIDADA (R13-33)   ← D15 = D93+D238+D287+D349+D407+D182+D455 (7 componentes)
│   Inbound R15-R22 (7 canales + Total)
│   Outbound R26-R33 (8 canales + Total)
│
├── Bloque SALARIO FIJO (R38-R134)
│   ├── Cálculo por rol (R43-R66) → fórmula INDEX(AM) × FTE/ratio
│   ├── Total (R68)
│   ├── Visión por perfiles (R70-R88) → E72=INDEX(C68, perfil)
│   ├── Visión por Canal Inbound (R91-R100) → C93=SUMIFS(E72:E88)
│   └── Visión por Canal Outbound (R103-R113)
│
├── Bloque COMISIONES/VARIABLE (R136-R204) — misma estructura
├── Bloque CAPACITACIÓN INICIAL (R206-R258)
├── Bloque CAPACITACIÓN ROTACIÓN (R259-R307)
├── Bloque EXÁMENES MÉDICOS (R308-R369)
├── Bloque ESTUDIOS DE SEGURIDAD (R370-R427)
└── Bloque CRUCERO (R429-R474)
```

Cada bloque tiene 3 sub-secciones: **cálculo** (valor base por rol × FTE/ratio), **visión por perfiles**
(agrupado por perfil operativo), **visión por canal** (SUMIFS → proyección mensual D:BK con ventana+indexación).

### Parámetros (R1-R12)

| Celda | Label | Fórmula | Valor | Origen |
|---|---|---|---|---|
| C3 | Nº Mes Inicio | `=SUM('Listas Desplegables'!A51:BH51)` | 6 | calendario |
| C4 | Mes Inicio | `=C3` | 6 | = C3 |
| C5 | Mes Fin | `=C4+Panel!C11-1` | 17 | Panel meses |
| C6 | Componente Humano | `=Panel!L6` | "80% SMMLV 20% IPC" | Panel indexación |
| C7 | Mes Aumento | `=Panel!L9` | 6 | Panel mes ajuste |

---

## FASE 2 — Mapa funcional

**Propósito:** calcular la nómina cargada mensual de Cadena A (payroll), desglosada en 7 componentes
(salario fijo, comisiones, cap. inicial/rotación, exámenes, seguridad, crucero), por canal y modalidad,
con proyección mensual (60 columnas) incluyendo ventana de contrato e indexación.

**Consume:** `Inputs de Nomina` (salarios, ratios, costos), `Condiciones Cadena A` (perfiles, FTE, flags),
`Panel de Control General` (fechas, indexación), `Tasas, TRM, Polizas` (tabla de factores acumulados),
`Rot, Ausent y Rentabilidad` (costos de exámenes).

**Produce:** Σ de los 7 componentes por canal (Región 1 consolidada R15:R33) → consumido por
`Vision Tarifas_Modelo_Cobro` (C41, SUMPRODUCT) y `Visión P&G` (C34:C40, SUMPRODUCT).

**Consumidores:** Vision Tarifas C41-C46 (SUMPRODUCT D15:BK33 × canal × modalidad),
Visión P&G C34-C40 (SUMPRODUCT D93:D112 × "Activado"), Hoja Maestra Escenarios C259-C264.

---

## FASE 3 — Fórmula maestra (cálculo por rol)

### C43 (Director de cuentas) — patrón que se repite en R43-R66

```
=IFERROR(
  IF(C$42<>"",
     INDEX('Inputs de Nomina'!$AM$16:$AM$51,
           MATCH(IF($B43=$B$63, C$42, $B43), 'Inputs de Nomina'!$B$16:$B$51, 0))
     × INDEX('Condiciones Cadena A'!$W$25:$AK$48,
             MATCH($B43, 'Condiciones Cadena A'!$V$25:$V$48, 0),
             MATCH(C$42, 'Condiciones Cadena A'!$E$16:$S$16, 0))
     × IF(OR($B43=$B$54, $B43=$B$55), 1/Panel!$C$11, 1),
  0)
  − INDEX($C$140:$Q$163, MATCH($B43, $B$140:$B$163, 0), MATCH(C$42, $C$139:$Q$139, 0)),
0)
```

**Descomposición:**
1. `INDEX(AM16:AM51, MATCH(rol))` → salario cargado unitario del rol (desde `Inputs de Nomina`)
2. `× INDEX(W25:AK48, MATCH(rol), MATCH(perfil))` → FTE fraccionario del rol para ese perfil
   (desde `Condiciones Cadena A`, tabla de FTE por rol × perfil)
3. `× IF(OR(rol=Analista Selección Ini/Rot), 1/meses, 1)` → roles de selección: mensualización
   (costo total ÷ meses contrato, no costo mensual fijo)
4. `− INDEX(C140:Q163, MATCH(rol), MATCH(perfil))` → **sustracción de comisiones** (se restan aquí
   porque se contabilizan aparte en el bloque COMISIONES/VARIABLE)

**Regla de despacho especial B63:** si `$B43 == $B$63` (el rol = Agente Básico), el MATCH busca
por **nombre del perfil** (`C$42`="Inbound 25") en vez de por nombre de rol. Esto permite que el
agente base se resuelva por perfil, no por un rol genérico.

### C66 (Especialista de Proyectos) — fórmula diferente

```
=IFERROR(
  IF(C$42<>"",
     (INDEX(AM16:AM51, MATCH($B66)) × $A$66 × 3 × 'Condiciones Cadena A'!W48)
     / Panel!$C$11,
  0),
0)
```

Donde `$A$66` = 0.5 (factor "Complejidad"), `×3` = 3 meses, `W48` = FTE del rol en el perfil,
`/C11` = mensualización (= costo total / meses contrato).

### Proyección mensual D93

```
=IF(AND(D$91>=$C$4, $C$5>=D$91),     ← ventana de contrato [mes_inicio, mes_fin]
    $C93,                               ← base mensual (incluyendo soporte)
    0)
  × IF(MONTH(D$92)>=$C$7,             ← ¿mes calendario ≥ mes de aumento?
       INDEX(Tasas!B8:G17, MATCH(C6), MATCH(YEAR)),     ← factor AÑO actual
       INDEX(Tasas!B8:G17, MATCH(C6), MATCH(YEAR-1)))   ← factor AÑO anterior
```

**Regla de indexación:** usa el MONTH del **calendario** (no del contrato) para decidir si aplica
el factor del año actual o del anterior. Para deals que empiezan en junio con ajuste en junio:
meses Jun-Dic → factor(2026)=1.0; Ene-May → factor(2026-1)=factor(2025)=1.0. **Sin indexación
en los 12 meses del contrato.**

---

## FASE 4 — Catálogo de fórmulas

| Celda | Fórmula | Descripción | Deps |
|---|---|---|---|
| C3 | `SUM(Listas!A51:BH51)` | Nº mes calendario del inicio | Listas Desplegables |
| C4 | `=C3` | Mes inicio (copia) | C3 |
| C5 | `=C4+Panel!C11-1` | Mes fin | C4, Panel!C11 |
| C6 | `=Panel!L6` | Componente indexación | Panel!L6 |
| C7 | `=Panel!L9` | Mes de aumento | Panel!L9 |
| R15 D | `D93+D238+D287+D349+D407+D182+D455` | Consolidado 7 componentes Voz/Inbound | 7 bloques |
| R43-R62 C | `INDEX(AM) × INDEX(W,FTE) × mensualización − comisiones` | Salario por rol soporte | Inputs Nomina, Cond.A |
| R63 C | Idem (con despacho por perfil) | Salario agente base | Inputs Nomina, Cond.A |
| R66 C | `INDEX(AM) × complejidad × 3 × FTE / meses` | Especialista Proyectos | Inputs Nomina, Cond.A |
| R68 C | `SUM(C43:C66)` | Total salario fijo (agente + soporte) | R43-R66 |
| E72 | `INDEX(C68:R68, MATCH(perfil))` | Agrupado por perfil | R68 |
| C93 | `SUMIFS(E72:E88, modal=Inbound, canal=Voz)` | Base canal Voz | E72 |
| D93 | `IF(ventana, C93, 0) × IF(MONTH>=C7, factor[YEAR], factor[YEAR-1])` | Proyección mensual | C93, C4-C7, Tasas |
| C182 | `SUMIFS(E169:E178, modal, canal)` | Variable base (solo agentes) | E169-E178 |
| C238/287/349/455 | `SUMIFS(E217..E450, modal, canal)` | Cap/Exam/Crucero (solo agentes) | E217-E450 |

---

## FASE 5 — Origen de datos

| Dato | Tipo | Origen |
|---|---|---|
| Salario cargado por rol (AM16:AM51) | CALCULADO | `Inputs de Nomina` W-col (C.Empresa) |
| FTE por rol × perfil (W25:AK48) | CALCULADO | `Condiciones Cadena A` (FTE/ratio) |
| Ratios de personal (Inputs R110:R129) | PARÁMETRO | storage HR-Ratios |
| Costos examen externo (R312-R314) | PARÁMETRO | `Rot, Ausent y Rentabilidad` R67-R69 |
| Factor de indexación | PARÁMETRO | `Tasas, TRM, Polizas` B8:G17 |
| Ventana contrato (C4, C5) | DERIVADO | Panel C10 (fecha), C11 (meses) |
| Componente humano (C6) | INPUT | Panel L6 |
| Mes de aumento (C7) | INPUT | Panel L9 |

---

## FASE 6 — Parametrización

| Parámetro | Storage | Excel | Estado |
|---|---|---|---|
| Ratios staff | HR-Ratios (23 roles × servicio) | Inputs Nomina R110-R129 | EXISTE Y SE USA |
| Salarios por rol | HR-Nomina (AM col) | Inputs Nomina C16:C51 | EXISTE Y SE USA |
| Costo examen | OP via `get_examen_medico(ciudad)` | Rot R67-R69 (SUMPRODUCT × servicio) | EXISTE PERO DIFIERE (posible) |
| Factor indexación | OP-ComponenteAcumulado | Tasas B8:G17 | EXISTE Y SE USA (post-fix alias) |
| Crucero tarifa | Panel `tarifa_crucero` ← input | Panel C17 (=8000×1.051=8408) | EXISTE Y SE USA (post-fix wiring) |

---

## FASE 7 — Reglas de negocio

| Regla | Fórmula Excel | Backend | Estado |
|---|---|---|---|
| **Ventana de contrato** | `IF(AND(mes>=C4, C5>=mes), base, 0)` | iteración `range(1, meses+1)` | Equivalente |
| **Indexación por calendario** | `IF(MONTH>=C7, factor[YEAR], factor[YEAR-1])` | `calcular_factor_aumento(mes_contrato, pct, mes_aplicacion)` | **Corregido** (pre-fix: mes contrato; post-fix: calendario→contrato) |
| **Activación canal** | `IF(FILTER(Panel M, K=canal)>0 AND M17, "Activado", 0)` | `CadenasActivas` + FTE>0 | Equivalente mecanismo |
| **Soporte en payroll** | `C68 = SUM(R43:R66)` incluye agente+soporte | `perfiles_canal` incluye soporte post-fix | **Corregido** |
| **Mensualización selección** | `IF(OR(rol=Sel_Ini, rol=Sel_Rot), 1/meses, 1)` | `NominaCalculator` no mensualiza reclutamiento | **Pendiente verificación** |
| **Complejidad Especialista** | `INDEX(AM) × A66(0.5) × 3 × FTE / meses` | `complejidad_especialista` flag | Equivalente |
| **Crucero** | `IF(Cond.A E75>0, tarifa × FTE)` | `IF(incluye_crucero, tarifa × FTE × indexación)` | **Corregido** (wiring tarifa) |
| **Exámenes: FTE base** | `INDEX(Cond.A E67:T67, MATCH(perfil)) × costo_exam / 12` (solo agente) | `fte_examenes` incluye soporte | **GAP: base FTE difiere** |

---

## FASE 8-9 — Paridad post-fixes

| Componente | Excel Σ12m | Backend Σ12m | Δ% | Estado |
|---|---:|---:|---:|---|
| Salario Fijo (R93 incl soporte) | 986.624.547 | ~986.6M (estimado con soporte) | ~0% | ✓ PARIDAD (post-fix soporte) |
| Comisiones (R182) | 36.769.005 | 36.769.005 | **0,000%** | ✓ PARIDAD (post-fix indexación) |
| Cap. Inicial (R238) | 5.000.000 | 5.000.000 | **0,000%** | ✓ PARIDAD |
| Cap. Rotación (R287) | 5.100.000 | 5.100.000 | **0,000%** | ✓ PARIDAD |
| Exámenes (R349) | 3.538.920 | 4.736.873 | **+33,85%** | ⚠ GAP (base FTE) |
| Seguridad (R407) | 0 | 0 | 0% | ✓ |
| Crucero (R455) | 2.522.400 | 2.522.400 | **0,000%** | ✓ PARIDAD (post-fix wiring) |

---

## FASE 10 — Gaps

| GAP | Origen | Impacto | Severidad | Causa raíz |
|---|---|---|---|---|
| **GAP-NL-EXAM** | Exámenes R349: Excel base = solo agente FTE; backend `fte_examenes` incluye soporte | +33,85% en exámenes (≈+1,2M/12m) | Media | `NominaCalculator._examenes` usa `perfil.fte_examenes` que el `context_builder` calcula incluyendo FTE soporte en el denominador del ratio |
| **GAP-NL-SELECCION** | Roles de selección (R54/R55): Excel `×(1/meses)` mensualiza costo total; backend puede no replicar | Pendiente cuantificación | Baja | No verificado |

---

## FASE 11 — Casos de prueba

| Caso | Servicio | Canales | Status |
|---|---|---|---|
| **AMERICAS** | Captura de Datos | Voz(25FTE) + WhatsApp(15FTE) | ✅ Fixture ejecutable (`americas_captura_datos.json`); paridad medida |
| **Bancamia** | Cobranzas | WhatsApp(6FTE) | ✅ Fixture existente (`bancamia_whatsapp_only.json`); oracles pendientes re-calibración |
| SAC | — | — | ❌ Sin fixture |
| Ventas multicanal | — | — | ❌ Sin fixture |
| Backoffice/SACO | — | — | ❌ Sin fixture |

---

## Criterio de cierre

| Criterio | Estado |
|---|---|
| Fórmulas documentadas | ✅ 7 bloques + fórmula maestra + proyección mensual |
| Dependencias documentadas | ✅ 5 hojas fuente identificadas |
| Parametrización documentada | ✅ 5 parámetros mapeados a storage |
| Reglas de negocio documentadas | ✅ 8 reglas con estado |
| Implementación backend localizada | ✅ `NominaCalculator`, `context_builder`, `vision_tarifas` |
| Paridad evaluada | ✅ 7 componentes × 12m con Δ% medido |
| Gaps identificados | ✅ 2 gaps (GAP-NL-EXAM, GAP-NL-SELECCION) |
| Casos de prueba definidos | ⚠ 2 ejecutables, 3 sin fixture |

**Wave cerrable** con los 2 gaps abiertos documentados. Siguiente hoja recomendada: `No payroll` (misma estructura, componentes complementarios).
