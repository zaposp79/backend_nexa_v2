# Veredicto forense: ¿Excel V2-8 cuenta la comisión variable de forma ADITIVA o es doble-conteo?

Fecha: 2026-06-11
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`
Modo: READ-ONLY (sin cambios de motor)

## Pregunta

¿El Excel V2-8 suma la comisión variable raw (D62 = 600,000) ENCIMA del costo cargado
completo (W62 = 3,560,973.86) de forma intencional (modelo aditivo), o es un doble-conteo
del propio Excel?

## VEREDICTO

**NO_ADITIVO / NO_DOBLE_CONTEO — Excel usa modelo de PARTICIÓN (igual que el backend).**

La premisa "Excel suma comisión raw encima del cargado" es FALSA. El Excel construye el
cargado W62 SOBRE una base que YA incluye la comisión (F62 = C62 + D62), y luego, para
separar la nómina en línea fija y línea variable, RESTA la comisión de la línea fija y la
re-expone como línea variable. fijo + variable reconstruye exactamente el cargado total.
No hay suma encima ni doble-conteo.

## 1. Fórmula del cargado W62 y su base

`'Inputs de Nomina'`:

| Celda | Etiqueta (fila 38) | Fórmula | Valor |
|---|---|---|---|
| C62 | Salario Base | `=INDEX('Condiciones Cadena A'!E12:S12, MATCH(...))` | 1,750,905 |
| D62 | Variable/Comisión | `=INDEX('Condiciones Cadena A'!E13:S13, MATCH(...))` | 600,000 |
| F62 | T. Imponible | `=SUM(C62:D62)` | 2,350,905 |
| W62 | C. Empresa (cargado) | `=+M62+P62+U62+V62` | 3,560,973.86 |
| AM62 | Costo Empresa + Comisiones | `=W62` | 3,560,973.86 |

W62 se descompone en seguridad social (M62), parafiscales (P62), prestaciones (U62) y
dotaciones (V62). Todos esos rubros parten de H62 = SUM(F62, G62, AL62), y F62 ya incluye
D62 (la comisión). Por tanto **la comisión está embebida dentro del cargado W62**.

Prueba aritmética de la base:
- W62 / F62 = **1.514725** → factor de carga limpio aplicado sobre la base CON comisión.
- W62 / C62 = 2.033790 → factor inflado (artefacto de dividir por la base sin comisión).
- F62 − C62 = 600,000 = D62 (la comisión está dentro de la imponible).

El factor de carga "limpio" (~1.51) confirma que el cargado se aplica sobre F62 (base CON
comisión), no sobre C62.

## 2. Cadena de atribución Inputs de Nomina → Nomina Loaded → Vision CTS

`'Nomina Loaded'` separa la nómina en dos bloques sobre el mismo escenario:

### Bloque FIJO (filas 43-83 → total fila 115 → Vision CTS C37)
Fórmula representativa (C43):
```
= INDEX('Inputs de Nomina'!$AM$39:$AM$76, MATCH(perfil)) * conteo_perfil
  - INDEX($C$155:$Q$178, MATCH(perfil), MATCH(mes))      <-- RESTA el bloque variable
```
Usa columna **AM** (= W62 = cargado total CON comisión) y le RESTA el bloque variable.
→ línea fija = cargado_total − comisión.

### Bloque VARIABLE (filas 155-178 → total fila 205 → Vision CTS C38)
Fórmula representativa (C155):
```
= INDEX('Inputs de Nomina'!$D$39:$D$76, MATCH(perfil)) * conteo_perfil
```
Usa columna **D** (= D62 = Variable/Comisión raw).
→ línea variable = comisión.

## 3. Factor de carga sobre cada base candidata

| Base | Fórmula | Factor | Interpretación |
|---|---|---|---|
| F62 (con comisión) | W62 / F62 | **1.5147** | factor de carga real, limpio |
| C62 (sin comisión) | W62 / C62 | 2.0338 | artefacto, no es el factor real |

El cargado se aplica sobre la base CON comisión. La comisión NO está fuera del cargado.

## 4. Prueba de partición vs doble-conteo

```
línea fija     = AM62 - D62 = 3,560,973.86 - 600,000 = 2,960,973.86
línea variable = D62        =                            600,000.00
                                                       --------------
fija + variable             =                          3,560,973.86  == AM62 (= W62, cargado)
```

fija + variable == cargado total exacto → **PARTICIÓN**. La comisión se cuenta UNA sola vez:
embebida en el cargado, se resta de la línea fija y se re-expone como línea variable.

- ¿Comisión contada dos veces? **NO.**
- ¿Comisión sumada encima del cargado? **NO.** El cargado nunca se infla con D62 adicional.

## 5. Implicación para el backend

El backend YA usa el modelo correcto: fijo + variable = total_cargado (comisión absorbida
dentro, partición). Esto coincide exactamente con el Excel.

**El delta CTS-001 (−289.44 COP/tx en subtotal payroll; backend 5,115.79 vs Excel 5,405.23
o C35 5,462.36) NO se explica por modelo aditivo vs partición.** Esa hipótesis queda
DESCARTADA con evidencia de celdas. La causa del delta está en otra parte y debe re-aislarse:

Candidatos a investigar (fuera del alcance de este veredicto):
- Diferencia en factor de carga aplicado (¿backend aplica 1.51 sobre base sin comisión vs
  con comisión, generando una base imponible distinta?).
- Diferencia en conteo de perfiles / FTE o ramp-up por escenario.
- Diferencia en denominador transaccional (CTS-001 ya tocó este punto en commit ed07c42).
- Rubros de cargado (seguridad social, parafiscales, prestaciones, dotaciones, recargos AL62)
  con parámetros HR distintos a los del Excel.

NO se debe reescribir la nómina a modelo aditivo: introduciría un doble-conteo de 600,000
COP/perfil que el Excel NO tiene.

## Anexo: celdas decisivas

- `'Inputs de Nomina'!F62 = SUM(C62:D62)` → base imponible incluye comisión.
- `'Inputs de Nomina'!W62 = M62+P62+U62+V62` → cargado sobre base con comisión, factor 1.5147.
- `'Inputs de Nomina'!AM62 = W62` ("Costo Empresa + Comisiones").
- `'Nomina Loaded'!C43 = INDEX(AM...)*conteo - INDEX($C$155:$Q$178...)` → fijo resta variable.
- `'Nomina Loaded'!C155 = INDEX('Inputs de Nomina'!D...)*conteo` → variable = comisión raw.
