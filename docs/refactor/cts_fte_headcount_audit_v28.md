# CTS-001 — Auditoría FTE / Headcount / Ramp / Staff-Variable del subtotal Payroll (V2-8)

Fecha: 2026-06-11
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`
Modo: READ-ONLY diagnóstico. Sin cambios de motor (causa = dato de entrada faltante).
Deal: SAC / METROCUADRADO / Grupo Aval, 24m. Provider: V2-7. Denominador: Panel!W31 = 221,000 tx/mes.

## Pregunta

¿Dónde vive el residual CTS-001 = `nomina_loaded` backend 5,115.79 vs Excel 5,405.23
(−289.44 COP/tx)? Hipótesis: conteo de perfiles (FTE/headcount), ramp-up o rubros "otros".

## VEREDICTO

**BLOCKED_MISSING_PARAMETRIZATION_SOURCE — el 100% del delta vive en el COSTO CARGADO de
los perfiles de SOPORTE (staff), no en agentes, conteo, FTE ni ramp.**

El delta NO es de cantidad/ponderación: agentes hacen MATCH exacto. El delta es que el
costo cargado de SOPORTE en backend NO incluye la COMISIÓN VARIABLE de Director de cuentas,
Jefe de Operación y Supervisor que el Excel SÍ embebe en su AM (loaded). Esa comisión de
staff existe SOLO en el Excel (`Inputs de Nomina`!D39/D46/D57 y `Condiciones Cadena A`); en
`request/request.json` todos los `comision_rol` de roles operativos = **0.0**. Sin tocar el
request, el motor no puede generar ese costo → no hay fix de motor trazable.

## 1. Descomposición exacta del nomina_loaded (COP/tx, ÷221,000)

| Bloque | Backend | Excel | Delta |
|---|---|---|---|
| Cargado AGENTES (AM × 260 HC) | 4,189.44 | 4,189.38 | **≈ 0 (MATCH)** |
| Cargado SOPORTE (staff) | 926.35 | 1,215.85 | **+289.50** |
| **nomina_loaded TOTAL** | **5,115.79** | **5,405.23** | **+289.44** |

- Agente: backend `salario_cargado` 3,561,022 ≈ Excel AM62 3,560,974 (MATCH). 130+50+80 = 260 HC.
- Factor de carga agente W62/F62 = 1.5147 = MATCH (verdict previo a926ec7). Confirmado.
- El delta completo (−289.44) está en el cargado de SOPORTE, no en agentes.

## 2. Por qué el split fijo/variable engañaba

El backend reporta `salario_fijo` 4,621.64 + `salario_variable` 494.15 (= raw×0.70).
`nomina_loaded = salario_fijo + comisiones` y `salario_fijo = total_cargado − comisiones`
(nomina.py:174, mismo objeto `comisiones`) → **nomina_loaded = total_cargado** (invariante a
0.70). El 0.70 (`pct_cumplimiento_variable`) NO afecta el total cargado: solo reclasifica
fijo↔variable. Por tanto la hipótesis "0.70 cumplimiento agente" es FALSA como causa del total:
solo mueve la línea fija vs variable, no el subtotal. Verificado: total_cargado backend = sf+com
= 5,115.79 exacto.

## 3. Causa raíz — STAFF_VARIABLE_NOT_IN_LOADED_COST (dato solo-Excel)

Excel embebe comisión variable de SOPORTE dentro de su costo cargado (AM = loaded(F=C+D)):

| Perfil staff | Excel base C | Excel var D | Excel AM (loaded) | AM sin var | Var cargada/HC |
|---|---|---|---|---|---|
| Director de cuentas (`Inputs de Nomina`!39) | 22,761,150 | 3,868,125 | 32,816,427 | 28,049,567 | +4,766,861 |
| Jefe de Operación (!46) | 4,329,699 | 1,500,000 | 8,065,483 | 5,990,209 | +2,075,274 |
| Supervisor (!57) | 2,334,300 | 700,000 | 4,506,462 | 3,466,840 | +1,039,621 |

Backend `salario_cargado` de esos perfiles parte SOLO de la base (sin la D) porque el deal de
entrada no la trae:

| Perfil staff (request) | base | comision_rol | salario_cargado backend |
|---|---|---|---|
| Soporte — director de cuentas | 18,505,000 | **0.0** | 25,601,964 |
| Soporte — jefe de operacion | 4,119,600 | **0.0** | 6,007,992 |
| Soporte — supervisor | 2,513,000 | **0.0** | 3,785,235 |

Ponderado por FTE de staff (61.4 FTE total, repartido en 3 canales) y dividido por 221,000,
el variable de staff cargado ≈ +289 COP/tx → el delta observado.

## 4. Tabla perfil-por-perfil (resumen)

| Perfil | HC/FTE Excel | HC/FTE backend | Cargado unit Excel | Cargado unit backend | Ramp | Veredicto |
|---|---|---|---|---|---|---|
| Agente Voz1/Voz2/WhatsApp | 130/80/50 = 260 | 130/80/50 = 260 | AM 3,560,974 | 3,561,022 | igual | MATCH |
| Soporte Director de cuentas | (D=3,868,125 en AM) | mismo FTE, AM SIN D | 32,816,427 | 25,601,964* | igual | DELTA (staff-var faltante) |
| Soporte Jefe de Operación | (D=1,500,000 en AM) | mismo FTE, AM SIN D | 8,065,483 | 6,007,992* | igual | DELTA |
| Soporte Supervisor | (D=700,000 en AM) | mismo FTE, AM SIN D | 4,506,462 | 3,785,235* | igual | DELTA |
| Resto soporte (com=0) | igual | igual | igual | igual | igual | MATCH (partición neta) |

\* el cargado backend además difiere por base distinta (Director base 18.5M vs Excel 22.76M),
parte de INPUT_DEAL_MISMATCH (V2-7 deal ≠ V2-8 Condiciones Cadena A). No se corrige aquí.

- **FTE/headcount**: MATCH (260 agentes + 61.4 soporte). NO es la causa.
- **Ramp-up**: idéntico (mismo factor de indexación/activación por mes). NO es la causa.
- **Rubros "otros" (cap inicial, rotación, exámenes, crucero)**: son C39-C43, fuera de
  nomina_loaded; sus deltas son menores y separados (examenes +12.2, crucero +10.6).
  El C35 "Payroll" 5,462.36 = nomina_loaded 5,405.23 + cap_inicial 11.59 + cap_rot 22.67 +
  examenes 12.24 + crucero 10.63. El −289.44 es exclusivamente nomina_loaded (staff variable).

## 5. Clasificación

**BLOCKED_MISSING_PARAMETRIZATION_SOURCE** (subtipo STAFF_VARIABLE_NOT_IN_LOADED_COST +
INPUT_DEAL_MISMATCH en bases de staff).

- La comisión variable de staff (Director 3.87M, Jefe Op 1.5M, Supervisor 0.7M) está SOLO en
  el Excel V2-8 (`Inputs de Nomina`!D y `Condiciones Cadena A`). El `request/request.json`
  lleva `comision_rol = 0.0` para los 72 roles operativos. Regla del proyecto: **NO TOCAR
  request/request.json**. Sin ese dato, el motor no debe inventar la comisión de staff.
- Hardcodear los valores de staff en el motor está PROHIBIDO (NO-HARDCODE).

## 6. Por qué NO se aplica fix de motor

1. El valor no existe en la fuente que alimenta el backend (request.json `comision_rol=0`).
2. Inyectarlo requiere modificar el deal de entrada (out of scope, NO TOCAR request/storage).
3. Es el patrón conocido INPUT_DEAL_MISMATCH (memory step2_excel_oracle_blocked): el V2-8
   debe recalcularse con el deal real de Condiciones Cadena A antes de un veredicto numérico.
4. Cualquier cambio en `_comisiones`/`_salario_fijo` (p.ej. quitar el 0.70) NO mueve el total
   cargado (invariante demostrada arriba); solo reclasificaría fijo↔variable.

## Anexo: celdas decisivas

- `Vision Cost To Serve`!C36 = SUM(C37:C38) = 5,405.23 (nomina_loaded).
- C37 = SUM(`Nomina Loaded`!D115:BK115)/C11/W31 = 4,629.49 (fijo); C38 = row205 = 775.74 (var).
- `Nomina Loaded`!C63 (agente fijo) = AM×HC − INDEX(variable_block) → PARTICIÓN confirmada.
- `Nomina Loaded`!C155/C162/C173/C174 = D-comisión por perfil (incluye staff: Director,
  Jefe Op, Supervisor) → staff SÍ tiene variable en Excel.
- `Inputs de Nomina`!D39=3,868,125 (Director), D46=1,500,000 (Jefe Op), D57=700,000 (Supervisor).
- `request.json` roles_operativos[*].comision_rol = 0.0 (72 ocurrencias) → staff variable ausente.
