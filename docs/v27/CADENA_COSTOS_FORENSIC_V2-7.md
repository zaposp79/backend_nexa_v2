# Wave Forense — Cadena de Costos V2-7 (6 hojas)

> Ingeniería inversa consolidada de: No payroll, Costo Fijo, Costo Variable,
> Costo Cadena C, Costos Totales, Pólizas - Costo Financiación.
> Deal: AMERICAS / Captura de Datos (12m, jun 2026).

---

## INVENTARIO GLOBAL

| Hoja | Filas | Cols | Celdas | Fórmulas | Arrays | Propósito |
|---|---|---|---|---|---|---|
| **No payroll** | 267 | 79 | 11.905 | 9.268 | 1.682 | OPEX TI + Inversiones + Infraestructura por canal/modalidad |
| **Costo Fijo** | 240 | 71 | 10.130 | 8.735 | 156 | OPEX fijo + Inversiones Cadena B por canal |
| **Costo Variable** | 334 | 71 | 12.855 | 10.510 | 1.054 | Tarifas por canal + OPEX variable + Escalamiento + HITL Cadena B |
| **Costo Cadena C** | 479 | 72 | 19.245 | 16.582 | 332 | Tarifa proveedor + Integración + Variable Cadena C |
| **Costos Totales** | 137 | 64 | 6.810 | 5.151 | 957 | Consolidación A+B+C por perfil → canal (alimenta P&G) |
| **Pólizas - Costo Financiación** | 459 | 64 | 20.032 | 11.807 | 5.713 | ICA + GMF + Pólizas + Comisión Adm + Financiero por cadena/canal |
| **TOTAL** | | | **80.977** | **56.053** | **9.894** | |

---

## MAPA FUNCIONAL POR HOJA

### No payroll (Cadena A — OPEX + Infraestructura)
```
Params (R1-R9): mes inicio/fin, componente tecnológico, mes aumento
Region 1 Consolidada (R13-R33): D14 = D107 + D186 + D248 (3 componentes por canal)
├── OPEX y TI (R37-R80): ítems de OPEX por perfil (licencias, internet, etc.)
│   R85-R103: Visión por perfiles (OPEX base por perfil×canal)
│   R105-R114: Visión por Canal Inbound (R107 = SUMIFS base × ventana × indexación)
├── Inversiones (R150-R200): hardware, amortización
│   R184-R200: Visión por Canal (R186 = amortización mensual)
└── Costos Fijos (R230-R267): arriendo, energía, vigilancia, aseo × estaciones
    R246-R257: Visión por Canal (R248 = Σ infraestructura × estaciones)
```
**Consumidores:** P&G filas 42-44 (`SUMPRODUCT × "Activado"`); Vision Tarifas C42 (`SUMPRODUCT D14:BK32`).

### Costo Fijo (Cadena B — OPEX fijo)
```
R36: OPEX FIJO
├── INBOUND (R39-R62): OPEX fijo por canal, 7 canales
├── OUTBOUND (R64-R90): idem
R91: Inversiones
├── INBOUND (R130-R153)
├── OUTBOUND (R154-R179)
R180: Soporte y Mantenimiento (equipo SM)
├── R195-R240: costos SM por dedicación × salario
```
**Consumidores:** P&G fila 47 (`SUMPRODUCT × "Activado"`); Vision Tarifas C51.

### Costo Variable (Cadena B — tarifas + variable)
```
R37: Tarifas por canal (unitarias × volumen)
R63: OPEX Variable
├── INBOUND (R66-R90): OPEX variable por canal
├── OUTBOUND (R91-R119)
R120: Tasa de Escalamiento (crecimiento de demanda)
R209: Visión por Productos (consolidado)
```
**Consumidores:** P&G fila 51-54; Vision Tarifas C52.

### Costo Cadena C (Tecnología / Automatización)
```
R35: Costo Fijo Total
├── R40-R58: Inbound (componente fijo por canal)    ← Tarifas!C61 lee aquí
├── R67-R85: Componente Variable por canal           ← Tarifas!C62 lee aquí
R90: Tarifa proveedor (por canal × volumen)
R116: Costo Integración (OPEX + Inversiones + Equipo)
R173: Variable (escalamiento + OPEX var + HITL)
R398: Tasa de escalamiento detallada
R437: HITL detallado
```
**Consumidores:** P&G filas 56-64; Vision Tarifas C60-C66.

### Costos Totales (Consolidador)
```
CADENA A (R6-R56): por perfil (R10-R33) → por canal (R35-R56)
├── R10: Inbound 25 = SUMIFS(Nomina Loaded + No payroll por perfil)
├── R37-R44: Inbound por canal (SUMIFS de perfiles)
├── R48-R56: Outbound por canal

CADENA B (R60-R84): por canal
├── R65-R72: Inbound = SUMIFS(Costo Fijo + Costo Variable)
├── R76-R84: Outbound

CADENA C (R87-R110): por canal
├── R91-R98: Inbound = FILTER(Costo Cadena C)
├── R102-R110: Outbound

TOTAL (R113-R137): = A + B + C por canal
```
**Consumidores:** P&G filas 31/45/55 (`SUMPRODUCT × "Activado"`).
**Pólizas consume:** `Costos Totales!E37` (base de ICA/GMF/Pólizas).

### Pólizas - Costo Financiación (16 bloques)
```
ICA:     Cadena A (R7-R30), B (R33-R56), C (R60-R83)
GMF:     Cadena A (R88-R111), B (R114-R137), C (R140-R163)
Config:  Polizas adicionales (R167-R190) — D173:G185 config pólizas
Polizas: Cadena A (R192-R216), B (R250-R274), C (R308-R327)
ComAdm:  Cadena A (R222-R241), B (R280-R299), C (R333-R351)
Fin:     Cadena A (R370-R396), B (R400-R425), C (R430-R456)
```
Cada bloque: activación (col B), canal (col C/D), mensual D:BK con ventana+indexación.

**Fórmula ICA (E12):** `IF(mes<=contrato, (CostosTotales!E37/factor_margenes + E198 + E378) × tasa_ICA, 0)`
**Fórmula GMF (E93):** `IF(mes<=contrato, (CostosTotales!E37 + E198 + E378) × tasa_GMF, 0)`
**Fórmula Pólizas (E198):** `LET(umbral, margenes, base_costo, SUMPRODUCT(config_polizas × vigencia) × base/margenes)`

**Consumidores:** P&G filas 66-70; Vision Tarifas C43-C46/C53-C56/C63-C66.

---

## PARAMETRIZACIÓN

### Storage v2-7/op.json
| Sheet Storage | Celdas Excel | Filas | Cubre |
|---|---|---|---|
| OP-OPEXFijo | No payroll R42-R53 (ítems OPEX) | 6 | Parcial (6 ítems vs ~12 en Excel) |
| OP-HardSoft | No payroll inversiones | 7 | Parcial |
| OP-Componente | Tasas anuales IPC/SMLV | 12 | Completo |
| OP-ComponenteAcumulado | Factores indexación acum. | 54 | Completo |
| OP-Poliza | Config pólizas (D173:G185) | 11 | Completo |
| OP-ICA | Tasas ICA por ciudad | 100 | Completo |

### Storage v2-7/hr.json
| Section | Cubre |
|---|---|
| `costo_fijo[]` (91 items) | Infraestructura por localidad (No payroll R248 base) |
| `med_seg[]` (35 items) | Exámenes médicos por ciudad |
| `nomina[]` (58 roles) | Salarios soporte (Costos Totales perfiles) |

### Cobertura
| Hoja | % en Storage | % en Backend | Gaps |
|---|---|---|---|
| No payroll | 70% | 85% (override OPEX + parametric infra) | Inversiones parcial, ítems OPEX individuales no migrados |
| Costo Fijo | 30% | 60% (CadenaBCalculator) | OPEX ítems en Cond.Cadena B, no storage |
| Costo Variable | 30% | 60% | Tarifas, escalamiento, HITL en input/Cadena B |
| Costo Cadena C | 20% | 50% (CadenaCCalculator) | Tarifa proveedor + integración en input |
| Costos Totales | N/A (consolidador) | 90% (CostosTotalesCalculator) | Estructura replica OK |
| Pólizas | 80% (OP-Poliza, OP-ICA) | 85% (CostosFinancierosCalculator) | Config pólizas completa; ComAdm parcial (GAP-PYG-04) |

---

## GAPS IDENTIFICADOS

| GAP | Hoja | Descripción | Severidad | Backend | Migrable |
|---|---|---|---|---|---|
| **GAP-NP-ITEMS** | No payroll | 12+ ítems OPEX individuales (licencias, internet, etc.) en R42-R53 vienen de Condiciones Cadena A R84-R95, no de storage. Backend usa override `no_payroll_mensual` (suma total). | Media | Parcial (override) | Nivel 2 (migrar ítems a storage) |
| **GAP-NP-INV** | No payroll | Inversiones por canal (R186) calculadas como amortización de CAPEX. Backend usa `inversiones_mensual` override (post-fix). Excel calcula mes a mes con amortización decreciente. | Media | Parcial (override plano) | Nivel 3 (amortización dinámica) |
| **GAP-CF-ITEMS** | Costo Fijo | OPEX fijo Cadena B (R39-R62) lee ítems de Condiciones Cadena B. Backend `CadenaBCalculator._costo_opex_fijo()` usa `parametros.opex_fijo` (suma). No desglose. | Baja | Parcial | Nivel 2 |
| **GAP-CV-ESC** | Costo Variable | Tasa de escalamiento (R120+) con fórmula compleja de crecimiento. Backend `CadenaBCalculator._costo_escalamiento()` simplificado. | Baja | Parcial | Nivel 3 |
| **GAP-CC-INT** | Costo Cadena C | Integración (R116-R172): OPEX + Inversiones + Equipo con dedicación y amortización. Backend `CadenaCCalculator` tiene estructura pero valores input. | Media | Parcial | Nivel 2 |
| **GAP-POL-COMADM** | Pólizas | Comisión Administración (R222): `SUMPRODUCT(E223:E241×filtros)` 3 bloques. Backend: `(base+fin)/fm×tasa`. | Media | Divergencia mecanismo | Nivel 3 — GAP-PYG-04 |
| **GAP-POL-LET** | Pólizas | E198 usa LET con `SUMPRODUCT(D173:D185×E173:E185×(G>=mes))` (pólizas con vigencia). Backend itera `polizas_usuario[]`. | Baja | Equivalente mecanismo | Nivel 1 |
| **GAP-CT-STRUCT** | Costos Totales | Consolidador puro (Σ A+B+C por canal). Backend `CostosTotalesCalculator` replica. | Ninguna | Completo | Nivel 1 |

---

## MIGRABILIDAD A PYTHON

| Fórmula/Bloque | Nivel | Estado actual | Acción requerida |
|---|---|---|---|
| No payroll: OPEX override | **1 (migrada)** | `NoPayrollCalculator` con override | — |
| No payroll: Inversiones override | **1** | Post-fix: `inversiones_mensual` | — |
| No payroll: Costos Fijos override | **1** | Post-fix: `costos_fijos_mensual` | — |
| No payroll: OPEX paramétrico | **1** | `_costo_opex_ti(estaciones)` | — |
| No payroll: Infra paramétrica | **1** | `_costo_infraestructura(estaciones)` | — |
| Costo Fijo: OPEX B | **2** | `CadenaBCalculator._costo_opex_fijo()` | Desglosar ítems |
| Costo Fijo: Inversiones B | **2** | `CadenaBCalculator._costo_inversiones()` | Desglosar |
| Costo Variable: Tarifas | **1** | Input `tarifa_unitaria` | — |
| Costo Variable: Escalamiento | **2** | `_costo_escalamiento()` simplificado | Verificar fórmula |
| Costo Variable: HITL | **1** | `_costo_hitl()` | — |
| Cadena C: Tarifa proveedor | **1** | Input `tarifa_proveedor` × volumen | — |
| Cadena C: Integración | **2** | `_costo_opex_fijo + _costo_amortizacion` | Desglosar dedicación |
| Cadena C: Variable/Escalamiento | **2** | `_costo_escalamiento + _costo_hitl` | Verificar |
| Costos Totales: consolidación | **1** | `CostosTotalesCalculator` | — |
| Pólizas: ICA per-cadena | **1** | `_calcular_ica(base, pol, fin, fm)` | — |
| Pólizas: GMF per-cadena | **1** | `_calcular_gmf(base, pol, fin)` | — |
| Pólizas: puras (LET/vigencia) | **1** | `polizas_usuario[]` iteración | — |
| Pólizas: ComAdm | **3** | `_calcular_comision_administracion` | GAP-PYG-04 (fórmula difiere) |
| Pólizas: Financiación | **1** | `_calcular_financiacion` | — |

**Resumen:** 12 de 19 bloques en **Nivel 1** (ya migrados), 5 en **Nivel 2** (migrable con desglose),
2 en **Nivel 3** (requiere parametrización nueva o rediseño).

---

## PLAN DE ELIMINACIÓN DE DEPENDENCIA EXCEL

| Bloque | Estado actual | Estado objetivo | Riesgo | Prioridad |
|---|---|---|---|---|
| No payroll (3 componentes) | Override + paramétrico | Python nativo (override cuando input) | Bajo | ✅ Ya migrado |
| Costo Fijo B | Input suma | Desglosar ítems si se requiere auditoría | Bajo | P3 |
| Costo Variable B | Input tarifa + escalamiento | Verificar fórmula escalamiento | Medio | P2 |
| Cadena C | Input tarifa + estructura | Desglosar integración + verificar | Medio | P2 (B/C en construcción) |
| Costos Totales | CostosTotalesCalculator | Python nativo | Bajo | ✅ Ya migrado |
| Pólizas | CostosFinancierosCalculator | Python nativo (excepto ComAdm) | Medio (ComAdm) | P1 (GAP-PYG-04) |

**Próximo paso:** las hojas de Cadena B y C están "en construcción" (fuera de alcance de paridad Cadena A).
El bloqueo principal para Cadena A es **GAP-PYG-04** (Comisión Administración) y **GAP-NL-EXAM** (base FTE exámenes).
Para ambos, la fórmula Excel está documentada; la corrección backend es de Nivel 2-3.
