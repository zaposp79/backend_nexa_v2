# Wave Forense — Inputs de Nomina (Excel V2-7)

> Fuente maestra de nómina para `Nomina Loaded`. Deal: AMERICAS / Captura de Datos.

---

## FASE 1 — Inventario

**Dimensiones:** A3:AP133 (42 cols, 133 filas). **2.320 celdas**: 1.898 fórmulas, 1 array, 169 números, 252 textos.

### Bloques funcionales

| Bloque | Filas | Propósito |
|---|---|---|
| **Parámetros globales** | R4-R8 | SMMLV, auxilio, %cumplimiento, dotaciones |
| **Salario Agente Básico** | R11 | Resultado calculado (2.730.864) |
| **Proporciones SS/Prestaciones** | R13 | Tasas de seguridad social y prestaciones (I-T) |
| **ESTRUCTURA DEFINIDA** (soporte) | R16-R38 | 23 roles de soporte con salario + cadena de cargas |
| **PERFILES** (agentes) | R39-R51 | Hasta 13 perfiles operativos con salario + cargas |
| **Equipo Soporte Mantenimiento** | R56-R71 | 12 roles Cadena B |
| **Equipo HITL** | R73-R82 | 6 roles HITL |
| **Roles Implementación** | R84-R102 | 14 roles implementación |
| **Ratios de personal** | R106-R133 | 23 roles × 6 servicios (agentes por rol) |

---

## FASE 2 — Mapa funcional

### Cadena de cálculo de salario cargado (cols C→AM)

```
C (Sal Base) → F (T.Imponible=C+D) → H (T.Haberes=F+G) 
→ I-L (SS: Salud 8.5%, Pensión 12%, ARL 0.522%) → M (Total SS)
→ N-O (Parafiscales: Caja 4%, ICBF+SENA 4%) → P (Total Paraf)
→ Q-T (Prestaciones: Cesantías 8.33%, Prima 8.33%, Int.Ces 12%, Vacaciones 4.17%) → U (Total Prest)
→ V (Dotaciones)
→ W (C.Empresa = M + P + U + V) ← "salario_cargado" del backend
→ X-AK (Recargos) → AL (Total Recargos)
→ AM (C.Empresa + Comisiones = W + AL)
```

### Fórmulas de salario base (col C)

Los roles de soporte (R16-R38) derivan su salario base multiplicando un **salario base 2025** × `(1+IPC)`:
```
C16 = 18505000 × (1+23%)    [Director de cuentas: 22.761.150]
C17 = 13000000 × (1+Tasas!B4) [Director Performance: salario2025 × (1+5,27%)]
```
**Patrón mixto:** algunos usan `(1+23%)` literal (SMLV 2026), otros `(1+Tasas!B4)` (IPC=5,27%).

Los perfiles (R39-R51) leen de `Condiciones Cadena A`:
```
C39 = INDEX('Condiciones Cadena A'!E$20:S$20, MATCH(perfil)) = 1.750.905 (SMMLV)
```

---

## FASE 3 — Origen de datos

| Celda/Rango | Valor | Fuente | Evidencia |
|---|---|---|---|
| C4 (SMMLV) | 1.750.905 | **INPUT** (hardcoded) | Constante 2026 |
| C5 (Aux.Transporte) | 249.095 | **INPUT** | Constante 2026 |
| C6 (%Cumplimiento) | 0.7 | **INPUT** | Panel/request |
| C7 (Dotaciones) | 184.500 | **CALCULADO** | `=(50000/4)×12×(1+23%)` ← constante con IPC |
| C16-C38 (Sal base soporte) | 22.761.150... | **CALCULADO** | `salario2025 × (1+IPC)` o `× (1+23%)` |
| C39-C51 (Sal base agentes) | 1.750.905 | **REFERENCIA** | `Condiciones Cadena A!E20:S20` |
| I13-T13 (Tasas SS/Prest) | 0.085/0.12/... | **PARÁMETRO** | Constantes regulatorias Colombia |
| R110-R133 (Ratios) | 750/1200/... | **PARÁMETRO** | Tabla de ratios por servicio |

---

## FASE 4 — Cobertura de parametrización

| Concepto Excel | Storage (v2-7/hr.json) | Estado |
|---|---|---|
| Salarios soporte (R16-R38 col C) | `nomina[].salario` (58 roles) | **EXISTE Y SE USA** |
| Costo empresa (R16-R38 col W) | `nomina[].costo_empresa_excel` | **EXISTE Y SE USA** |
| Costo empresa + comisiones (col AM) | `nomina[].costo_empresa_override` | **EXISTE** (solo Director tiene override; resto = excel) |
| Tasas SS (I13:L13) | `seg_social[]` (5 items: Salud 0.085, Pensión 0.12, ARL 0.00522) | **EXISTE Y SE USA** |
| Tasas Prestaciones (Q13:T13) | `prestaciones[]` (4 items: Cesantías 0.0833, Primas 0.0833, Int.Ces 0.12, Vac 0.0417) | **EXISTE Y SE USA** |
| Ratios (R110-R133) | `ratios[]` (138 entries = 23 roles × 6 servicios) | **EXISTE Y SE USA** |
| SMMLV (C4) | `salarios[0].valor = 1.750.905` | **EXISTE Y SE USA** |
| Auxilio (C5) | `salarios[1].valor = 249.095` | **EXISTE Y SE USA** |
| %Cumplimiento (C6) | `salarios[2].valor = 0.7` | **EXISTE Y SE USA** |
| Dotaciones (C7) | **NO EXISTE** (calculado en Excel `=(50000/4)×12×(1+23%)`) | **GAP** |
| Parafiscales Caja (N13=4%) | seg_social no la tiene explícita | **PARCIAL** (backend calcula Caja via PayrollCalculator) |
| ICBF+SENA (O13=4%) | seg_social no lo tiene | **PARCIAL** (backend tiene reglas Ley 1819) |
| Recargos (X-AK) | `recargos[]` (7 items) | **EXISTE** (no aplica a agentes, solo festivos/nocturnos) |
| Exámenes médicos (R312-314) | `med_seg[]` (35 items por ciudad) | **EXISTE Y SE USA** |
| Ramp-up/Campaña | `campana[]` (360 = 6 servicios × 60 meses) | **EXISTE Y SE USA** |
| Costo fijo infraestructura | `costo_fijo[]` (91 items por localidad) | **EXISTE Y SE USA** |

---

## FASE 5 — Consumo por Nomina Loaded

| Dato Inputs Nomina | Celda | Consumo en Nomina Loaded |
|---|---|---|
| AM16:AM51 (salario cargado por rol) | col AM | `NL!C43:C66` fórmula `INDEX(AM, MATCH(rol))` → base del costo por rol |
| R39-R51 (perfiles agentes) | filas 39-51 | `NL!C63` (Agente Básico) + `NL!C42` (nombre perfil para dispatch) |
| R16-R38 (roles soporte) | filas 16-38 | `NL!C43-C62` (soporte via INDEX(AM) × FTE ratio de Cond.A) |
| C4 (SMMLV) | parámetro | Regla auxilio transporte: `IF(F<2×SMMLV, aux, 0)` |
| R110-R133 (Ratios) | filas 110-133 | `Condiciones Cadena A!E25:S48` (FTE soporte = FTE agente / ratio) |

---

## FASE 6 — Catálogo de cargos

| Cargo | Tipo | Salario Base (C) | Costo Empresa (W) | Costo+Com (AM) | Fuente |
|---|---|---:|---:|---:|---|
| Agente Básico (Inbound 25) | Perfil | 1.750.905 | 2.900.433 | 2.900.433 | Cond.A → SMMLV |
| Director de cuentas | Soporte | 22.761.150 | 28.049.567 | 29.031.301 | 18.505.000×1.23 |
| Director Performance | Soporte | 13.685.100 | 18.933.555 | 18.933.555 | 13.000.000×1.0527 |
| Supervisor | Soporte | 3.090.990 | 4.584.893 | 4.584.893 | 2.513.000×1.23 |
| Monitor Calidad | Soporte | 2.149.179 | 3.281.883 | 3.281.883 | 1.747.300×1.23 |
| Formadores | Soporte | 2.057.790 | 3.155.445 | 3.155.445 | 1.673.000×1.23 |
| Aprendiz SENA | Especial | 1.750.905 | 2.496.241 | 2.496.241 | SMMLV (Ley 789) |
| Especialista Proyectos | Especial | 5.405.151 | 7.478.113 | 7.478.113 | 5.134.560×1.0527 |

**Reglas de costo:**
- Alto salario (>10×SMMLV): Salud al 70% del 8,5% (R82 Data Steward: 30M base)
- Auxilio transporte: solo si salario < 2×SMMLV
- ICBF+SENA: 0 para empleados por Ley 1819 (la mayoría)
- Recargos: 0 para todos (no aplica en este deal)

---

## FASE 7 — Reglas de negocio

| Regla | Implementación Excel | Backend | Estado |
|---|---|---|---|
| Salario base = constante2025 × (1+IPC/23%) | `C16 = 18505000×(1+23%)` | `storage nomina[].salario` = valor final | **Mecanismo** (backend usa resultado, no fórmula) |
| Auxilio si T.Imp < 2×SMMLV | `G = IF(AND(F<2×C4, F>0), C5, 0)` | `PayrollCalculator._aux_transporte` | Equivalente |
| Salud solo para alto salario | `I = IF(F>10×C4, F×8.5%×70%, 0)` | `PayrollCalculator._salud` | Equivalente |
| ICBF+SENA = 0 (Ley 1819) | `O = 0` para la mayoría | Backend aplica Ley 1819 | Equivalente |
| Cesantías/Prima = F×H×8.33% / F | `Q = (H×Q13×12)/12 = H×8.33%` | `PayrollCalculator._cesantias` | Equivalente |
| Dotaciones = `(50000/4)×12×(1+23%)/12` | `V = IF(F<2×C4, C8, 0)` | backend usa input | **GAP-DOT** (constante 15.375 vs dinámico) |

---

## FASE 8-9 — Paridad parametrización

| Dato | Excel | Storage | Backend loaded | Δ | Estado |
|---|---|---|---|---:|---|
| SMMLV | 1.750.905 | 1.750.905 | 1.750.905 | 0 | **PARITY** |
| Auxilio | 249.095 | 249.095 | 249.095 | 0 | PARITY |
| Salud % | 8,5% (I13) | 8,5% (seg_social) | 8,5% | 0 | PARITY |
| Pensión % | 12% (J13) | 12% | 12% | 0 | PARITY |
| ARL % | 0,522% (L13) | 0,522% | 0,522% | 0 | PARITY |
| Cesantías | 8,33% (Q13) | 8,33% | 8,33% | 0 | PARITY |
| Primas | 8,33% (R13) | 8,33% | 8,33% | 0 | PARITY |
| Vacaciones | 4,17% (T13) | 4,17% | 4,17% | 0 | PARITY |
| Director cuentas sal | 22.761.150 | 22.761.150 | 22.761.150 | 0 | PARITY |
| Director cuentas AM | 29.031.301 | 29.031.301 (override) | 29.031.301 | 0 | PARITY |
| Agente Básico AM | 2.900.433 | (calc via PayrollCalc) | **2.900.433** | **0** | **PARITY** ✓ |
| Ratios Dir.Cuentas/Cobranzas | 750 | 750 | 750 | 0 | PARITY |
| Dotaciones | 15.375 (`50000/4×12×1.23/12`) | **NO EXISTE** | input fixture | — | **GAP** |

---

## FASE 10 — Gaps

| GAP | Descripción | Severidad | Impacto |
|---|---|---|---|
| **GAP-NI-DOT** | Dotaciones (C7=15.375) calculadas con fórmula `(50000/4)×12×(1+23%)/12`; backend las toma como input. No hay constante 50.000 en storage. | Baja | 15.375/mes para agentes con salario < 2×SMMLV; ya incluido en salario_cargado |
| **GAP-NI-SAL-FORMULA** | Salarios base de soporte se calculan como `constante2025 × factor_aumento` en Excel. Storage guarda el resultado final, no la fórmula. Correcto para un punto en el tiempo; puede divergir si se actualiza solo uno de los dos. | Baja | Riesgo de drift temporal, no de paridad actual |
| **GAP-NI-OVERRIDE** | `costo_empresa_override` existe solo para Director de cuentas (29.031.301 vs excel 28.049.567). Los demás roles usan `costo_empresa_excel`. Causa: Director tiene comisión especial que infla AM. | Info | No afecta cálculo (backend usa `costo_empresa_override` cuando presente) |

---

## Criterio de cierre

| Pregunta | Respuesta |
|---|---|
| ¿De dónde sale cada valor usado por Nomina Loaded? | Documentado: AM (salario cargado) ← cadena C→W→AM; FTE ratio ← Condiciones A W25:AK48 ← Ratios R110:R133 |
| ¿Está en Storage? | **SÍ** para los 58 roles (salario+costo_empresa), SS, prestaciones, ratios, exámenes, ramp-up, infraestructura |
| ¿Está en Excel? | **SÍ** — completo en cols C-AM para cada rol + ratios R110-R133 |
| ¿Está duplicado? | **SÍ** — los 58 salarios/costos están tanto en Excel (Inputs Nomina) como en Storage (hr.json nomina[]). Los valores son idénticos (verificado para Director, Agente). |
| ¿Está implementado en Backend? | **SÍ** — `PayrollCalculator` reproduce la cadena SS+Prestaciones+Dotaciones. `ParametrizationProvider` lee de storage. Resultado final (AM39=2.900.433) = Excel (**PARITY EXACTA**). |

**Wave cerrada.** Siguiente hoja recomendada: `No payroll` o `Condiciones Cadena A`.
