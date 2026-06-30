# V2-7 GAP Closure — Status Report (Fase 2)

Fecha: 2026-05-29 · Rama: refactor/engine-v2

Toda afirmación trazable a fuente de workbook (`Nexa - Pricing - Simulador - V2-7.xlsx`)
verificada con openpyxl (`data_only` formulas + valores). Cero datos fabricados.

## Resumen ejecutivo

| GAP | Estado | Verificación workbook |
|-----|--------|-----------------------|
| GAP-PYG-HIER-1 | ✅ CERRADO | payroll_a/no_payroll_a detail suma exacta al parent (12 meses) |
| GAP-PYG-HIER-2 | ⚠️ PARCIAL | 6/7 sub-componentes; OPEX Variable = UNDETERMINED |
| GAP-PYG-HIER-3 | ✅ CERRADO | 7 sub-componentes desde ResultadoCadenaC |
| GAP-PYG-HIER-4 | ✅ CERRADO | estaciones=24.0 == workbook C14=24 |
| GAP-CTS-HIER-1 | ✅ CERRADO | crucero=11.17 == workbook fila 43 (premisa "0" corregida) |
| GAP-CTS-ACT-1 | ✅ CERRADO (servicio-driven) | catálogo `Listas Desplegables!A4:A9`; servicio driver de nómina/ramp-up, NO de chains/channels |
| GAP-CTS-CHAN-1 | ⛔ UNDETERMINED | requiere validación mapeo volumen por canal |

## Detalle por GAP

### ✅ GAP-PYG-HIER-1 — Sub-componentes Payroll/No-Payroll (Cadena A)
- **Cierre**: `VisionPyGBuilder.construir()` recibe `calc_nomina`, `calc_no_payroll`, `perfiles`. Emite `VisionPyG.filas_detalle` (nuevo campo, retrocompatible — vacío sin calculadores).
- **Trazabilidad**: 7 filas payroll (Excel 34-40) + 3 no-payroll (Excel 42-44), por mes desde `ResultadoNomina`/`ResultadoNoPayroll`.
- **Validación**: suma de detail == fila summary `payroll_a`/`no_payroll_a` para los 12 meses (test `test_payroll_detail_sums_to_parent`).

### ⚠️ GAP-PYG-HIER-2 — Sub-componentes Cadena B (PARCIAL)
- **Cerrado**: OPEX Fijo, Inversiones, S&M, Tarifa Canal, Tasa Escalamiento, HITL (6 campos desde `ResultadoCadenaB`).
- **UNDETERMINED — requires workbook validation**: "OPEX Variable" (Excel fila 52). `ResultadoCadenaB` no modela ese campo separado; el código CTS existente ya lo trataba como 0.0 ("not separately tracked"). **No se emite fila fabricada.** Cerrar requiere validar qué `'Costo Variable'!`-source alimenta la fila 52 y si difiere de `costo_variable`.

### ✅ GAP-PYG-HIER-3 — Sub-componentes Cadena C
- **Cierre**: `calc_cadena_c` añadido al dict de calculadores del motor; 7 filas (Excel 56-64) desde `ResultadoCadenaC`.
- **Caveat trazable**: el summary `costo_c` usa `ResultadoCadenaC.total_pyg` (excluye hitl/equipo_integ/opex_var_integ → fluyen a `costo_c_fin`). Excel fila 55 los incluye. En el fixture real esos 3 campos = 0 (verificado: H60=0, H63=0, H64=0), por lo que suma(detail)==parent. Si fueran ≠0, divergiría — discrepancia **preexistente** de convención backend, no introducida aquí.

### ✅ GAP-PYG-HIER-4 — Contribución por Puesto
- **Cierre**: fila `contribucion_por_puesto` (Excel 75) = `contribucion[mes] / estaciones`.
- **Fuente estaciones**: `Σ(fte × pct_presencia)` sobre perfiles no-soporte — la misma fórmula que `context_builder` usa para estaciones presenciales, y que el workbook codifica en `'Condiciones Cadena A'!E19:S19`.
- **Validación numérica**: backend=24.0 == workbook C14=24 (row17 FTE=40 × pct_presencia 0.6 = 24). No se añadió campo a `PyGMensual` (contrato certificado intacto); se calcula en el builder.

### ✅ GAP-CTS-HIER-1 — Crucero en DesgloseCTSCadenaA
- **Corrección de premisa**: Fase-1 documentó "siempre 0" — **FALSO**. Workbook: servicio fila 43 = 11.17, canal WhatsApp fila 107 = 8408.
- **Cierre**: campo `crucero` añadido a `DesgloseCTSCadenaA`; acumulado desde `ResultadoNomina.crucero`. Ahora los sub-componentes payroll suman exacto al agregado `nomina` (antes faltaba crucero → leve desbalance).
- **Validación**: crucero=11.1687 ≈ workbook 11.17; sum(payroll sub) == nomina.

### ✅ GAP-CTS-ACT-1 — Modelo servicio-driven (RE-ABIERTO y resuelto)
- **Re-análisis** (tras objeción válida de que el servicio es driver funcional): escaneo de los 432 refs a `Panel!C5` + los 3 únicos literales `"SAC"` en todo el workbook.
- **Catálogo único de verdad**: `Listas Desplegables!A4:A9` = Cobranzas, SAC, Ventas multicanal, SACO, Plataformas, Captura de Datos → `domain/services/servicio_catalogo.py`.
- **Servicio SÍ es driver funcional** (verificado): nómina/capacidad (`MATCH(C5, Inputs de Nomina!C109:H109)` elige columna) y ramp-up (`MATCH(C5, Rot Ausent!A38:A43)`). Ambos **ya implementados y certificados** en la capa de costos.
- **Servicio NO controla** chains (M17/M30 booleanos independientes) ni channels (volumen>0). Verificado: M17/M30 no referencian C5. **No se fabrica** un mapeo servicio→chains.
- **`IF(C27="SAC")` clasificado como gate de relevancia semántica** (no cosmético, no filtro estructural, no switch de cálculo): los datos por canal computan para todo servicio. `canal_view_habilitado` ahora deriva del catálogo (`canal_detail_habilitado(servicio)`), eliminando el string hardcoded. El backend **NO suprime cómputo**.
- **Validación**: 6 servicios del catálogo == dropdown; gate True solo para SAC; data computa idéntica para SAC y no-SAC; chains/channels invariantes al cambiar servicio.

### ⛔ GAP-CTS-CHAN-1 — CTS por canal (UNDETERMINED)
- **Por qué no se cierra**: las fórmulas (filas 64-270) dividen por `FILTER(Panel!M19:M25, K19:K25=canal)` = volumen Cadena-A **por canal**, con split inbound/outbound y SUMPRODUCT sobre `'Costos Totales'`/`'Nomina Loaded'`/`'No payroll'` filtrado por canal.
- **Bloqueo de integridad**: el backend no expone hoy una tabla de volumen Cadena-A por canal (Panel!K/L/M/P) con mapeo 1:1 trazable desde `volumetria`. Implementar el denominador por canal sin ese mapeo verificado implicaría inventar el split de volumen → prohibido por la regla de integridad.
- **Para cerrarlo**: validar en workbook el origen exacto de `Panel!K19:K25/L19:L25/M19:M25/P19:P25` y su correspondencia con el input `volumetria.{inbound,outbound}.canales[]`, luego reutilizar la decomposición por canal que ya produce `VisionTarifasCalculator`.

## Constraints honrados
- Sin hardcodes, sin ifs por cliente/escenario, sin placeholders, sin fallbacks silenciosos.
- `PyGMensual` y contratos existentes intactos (nuevos campos son aditivos y opcionales).
- Lógica certificada de Fase 1 sin alterar.

## Tests
- **Baseline certificado**: 179 + 21 verdes (sin regresión).
- **Nuevos (Fase 2)**: `tests/parity/test_vision_gap_closure.py` — 14 tests (presencia, forma estructural, paridad numérica vs workbook, reglas de activación).
- **3 fallos preexistentes** (no relacionados, confirmado con `git stash`): 2 archivos `*_tmp.py` de debug + 1 `Vision Tarifas C50` (gap cadena-B de 42M, fuera de alcance).

## Declaración final
Los GAPs documentados se cerraron con paridad Excel verificada y cero datos fabricados,
**excepto**: GAP-PYG-HIER-2 OPEX-Variable y GAP-CTS-CHAN-1, marcados explícitamente
**UNDETERMINED — requires workbook validation** por no ser derivables sin fabricar.
