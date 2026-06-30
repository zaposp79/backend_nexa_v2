# Visión P&G — Matriz de Activación

## Casos probados contra Excel V2-7

| Caso | Configuración | Ingreso Bruto A | Ingreso B | Ingreso C | Costo A | Comp.Fin | Contribución |
|------|---------------|-----------------|-----------|-----------|---------|----------|--------------|
| 1 | Solo Cadena A | > 0 | 0 | 0 | > 0 | > 0 | ingreso_neto - costo_a - fin |
| 2 | Cadena A + B | > 0 | > 0 | 0 | > 0 | > 0 | — |
| 3 | Cadena A + B + C | > 0 | > 0 | > 0 | > 0 | > 0 | — |
| 4 | Cadena A inactiva (margen=1.0) | IFERROR → 0 | — | — | 0 | 0 | 0 |
| 5 | Rampup mes 1 = 0 | 0 | 0 | 0 | > 0 | > 0 | negativa |
| 6 | Imprevistos = 0 | > 0 | — | — | — | — | sin impacto |
| 7 | Imprevistos > 0 | > 0 | — | — | — | — | reduce ingreso_neto |
| 8 | Financiación activa | — | — | — | — | fin > 0 | reduce contribución |
| 9 | Todos los meses activos | valores > 0 en todos | — | — | — | — | — |
| 10 | Costo Fijo (C78) | — | — | — | — | — | siempre 0 (hardcoded) |

## Comportamiento por celda cuando cadena inactiva

| Row | Condición | Excel muestra |
|-----|-----------|---------------|
| C19 Ingreso A | margen_a = 1.0 | IFERROR → **0** (no "#DIV/0!") |
| C20 Ingreso B | costo_b = 0 | **0** |
| C21 Ingreso C | costo_c = 0 | **0** |
| C31 Costos A | FTE = 0 | **0** |
| C45 Costos B | cadena_b desactivada | **0** |
| C55 Costos C | cadena_c desactivada | **0** |

## Columnas mensuales

- Columnas C…CO = meses 1…N del contrato.
- Si mes > meses_contrato → columna vacía (no incluida en backend output).
- Rampup por mes viene de `Rot, Ausent y Rentabilidad` sheet → backend: `calcular_rampup()`.

## Fase 2 — Filas de detalle (GAP-PYG-HIER-1/2/3) y Contribución por Puesto (HIER-4)

Las `filas_detalle` se emiten solo cuando el builder recibe los calculadores
(el motor los pasa siempre; llamadas legacy con solo pyg+kpis → `filas_detalle=[]`).

| Parent | Sub-componentes emitidos | Fuente | Suma == parent |
|--------|--------------------------|--------|----------------|
| payroll_a | salario_fijo, salario_variable, cap_inicial, cap_rotacion, examenes, estudios_seguridad, crucero | ResultadoNomina | Sí (verificado) |
| no_payroll_a | opex_fijo_a, inversiones_a, costos_fijos_a | ResultadoNoPayroll | Sí |
| costo_b | opex_fijo_b, inversiones_b, sm_b, tarifa_canal_b, tasa_escalamiento_b, hitl_b | ResultadoCadenaB | Sí (6 campos; OPEX Variable UNDETERMINED) |
| costo_c | tarifa_proveedor_c, opex_fijo_integ_c, inversiones_integ_c, equipo_integ_c, tasa_escalamiento_c, opex_var_integ_c, hitl_c | ResultadoCadenaC | Sí cuando hitl/equipo/opex_var=0 (caveat total_pyg) |

**Contribución por Puesto** (fila 75): `contribucion[mes] / estaciones`,
`estaciones = Σ(fte × pct_presencia)` no-soporte. Validado == 24 (workbook C14).
