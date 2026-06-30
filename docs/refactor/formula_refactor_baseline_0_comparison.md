# Comparación Excel V2-7 / Backend — FORMULA_REFACTOR_BASELINE_0 (TAREA 2)

## Hallazgo central: estado cacheado del Excel NO corresponde a request.json

El Excel `excel/Nexa - Pricing - Simulador - V2-7.xlsx` (data_only=True) tiene
sus valores cacheados para un **deal distinto** al de `request/request.json`:

| Dimensión | Excel V2-7 (cacheado) | request.json | Comparable a nivel agregado |
|---|---|---|---|
| Servicio | Captura de Datos | Cobranzas | NO |
| Cliente | AMERICAS BPS S.A | Bancamia | NO |
| Fecha inicio | 2026-06-01 | 2026-01-01 | NO |
| Duración | 12 meses | 24 meses | NO |
| Ciudades | Bogotá 0.6 / Cali 0.2 / Med 0.2 | Bogotá 1.0 | NO |
| Costo financiación | No | Sí (true) | NO |
| ICA | 0.01 | 0.0097 | NO |
| Pólizas activas | Cumpl, Salarios, Calidad, ComAdmÚn | 10 pólizas (otra mezcla) | NO |
| Perfiles Cadena A | Inbound 25 / inboun Whatsapp | Inbound 10 / 15 / 20 | NO |
| Cadenas activas | A + B + C (C dominante) | A + B (C off) | NO |
| Canal escenario 1 | Voz (fijo+variable 0.7/0.3) | WhatsApp (FTE 1.0) | NO |
| Ingreso mensual cacheado | 38.608.712.270 (Visión Imprimible B19) | 260.842.534 (backend) | NO |

**Conclusión:** una comparación agregada valor-a-valor Excel-vs-backend para
este request es `NO_COMPARABLE`, porque el Excel describe otro deal. El cacheo
del workbook refleja el último escenario guardado por el usuario, no Bancamia
Cobranzas.

## Superficie de paridad real

La paridad canónica que SÍ aplica es:

1. **Constantes de parametrización deal-independientes** (Excel → storage v2-7).
2. **Suite golden/parity existente** (58 tests, todos PASSED).
3. **Ramp-up por servicio** (Excel "Rot, Ausent y Rentabilidad" → backend).

### Matriz de conceptos (10+)

| # | Concepto | Excel ref (V2-7) | Valor Excel | Backend (request.json) | Estado |
|---|---|---|---|---|---|
| 1 | Rentabilidad mínima Cobranzas | Rot,Ausent y Rent. B29 | 0.21 | kpis.margen_minimo_requerido = 0.21 | MATCH |
| 2 | Margen objetivo Cobranzas | Rot,Ausent y Rent. C29 | 0.18 | input panel.margen = 0.18 (storage 18.0) | MATCH |
| 3 | Ramp-up Cobranzas mes 1 | Rot,Ausent y Rent. B38 | 0.85 | pyg[0].rampup = 0.85 | MATCH |
| 4 | Ramp-up Cobranzas mes 2/3 | C38 / D38 | 0.92 / 1.0 | curva ramp backend (Cobranzas) | MATCH |
| 5 | Prestaciones (Cesantías) | Inputs Nomina / storage HR | 0.0833 | hr.prestaciones[Cesantías] = 0.0833 | MATCH |
| 6 | Prestaciones (Vacaciones) | storage HR | 0.0417 | hr.prestaciones[Vacaciones] = 0.0417 | MATCH |
| 7 | Seg. social (Salud) | storage HR | 0.085 | hr.seg_social[Salud] = 0.085 | MATCH |
| 8 | Seg. social (Pensión) | storage HR | 0.12 | hr.seg_social[Fondo pensión] = 0.12 | MATCH |
| 9 | Salario mínimo 2026 | Inputs Nomina C4 | 1.750.905 | hr.nomina (storage) | MATCH |
| 10 | Aux. transporte | Inputs Nomina C5 | 249.095 | hr.nomina (storage) | MATCH |
| 11 | ICA (input deal) | request.json datos_op | 0.0097 | pyg[0].ica_a sobre base imponible | MATCH_CON_TOLERANCIA (input) |
| 12 | GMF (input deal) | request.json datos_op | 0.004 | pyg[0].gmf_a sobre base | MATCH_CON_TOLERANCIA (input) |
| 13 | Nómina total mes 1 | Visión P&G H32 (otro deal) | 138.607.316 | payroll_a = 154.103.322 | NO_COMPARABLE |
| 14 | No Payroll mes 1 | Visión P&G H41 (otro deal) | 34.555.560 | no_payroll_a = 61.770.812 | NO_COMPARABLE |
| 15 | Costo Cadena A mes 1 | Visión P&G H31 (otro deal) | 173.162.877 | costo_a = 215.874.135 | NO_COMPARABLE |
| 16 | Costo Cadena B mes 1 | Visión P&G H45 (otro deal) | 2.745.000 | costo_b = 0 (ver divergencia D-1) | NO_COMPARABLE |
| 17 | Cadena C | Costo Cadena C (otro deal) | activo | costo_c = 0 (C off en request) | NO_COMPARABLE |
| 18 | Ingreso mensual (Visión Imprimible) | Visión Imprimible B19 | 38.608.712.270 | kpis.ingreso_mensual = 260.842.534 | NO_COMPARABLE |
| 19 | Tarifas (Vision Tarifas) | Vis. Tarifas C19 Voz | 38.510.214.102 | vision_tarifas WhatsApp/Correo | NO_COMPARABLE |
| 20 | CTS (Vision Cost To Serve) | Servicio = Captura de Datos | n/a | cost_to_serve Cobranzas | NO_COMPARABLE |

Tolerancia aplicada: ±0.5% en valores derivados de constantes; las filas 1-10
son MATCH exacto (constantes leídas de storage = celdas del Excel).

## Lectura

- Las **constantes canónicas** (filas 1-10) están en paridad exacta backend↔Excel.
- Los **agregados del deal** (filas 13-20) NO son comparables porque el Excel
  cacheado es otro escenario; comparar exigiría reconfigurar el workbook a
  Bancamia Cobranzas y recalcular en Excel (acción de negocio, fuera de scope).
- La paridad numérica del deal Cobranzas se protege vía golden tests v27
  (`tests/golden/test_cost_to_serve_golden_v27.py`,
  `tests/golden/test_vision_tarifas_golden_v27.py`) y el nuevo snapshot
  baseline (`tests/refactor/baseline_formula_snapshot_v0.json`).
