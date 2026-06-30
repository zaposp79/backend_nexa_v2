# MAPEO EXCEL → BACKEND — V2-7

> Comparación directa entre hojas/celdas del Excel y módulos del backend.

---

## 1. Mapa de Correspondencias

### Panel de Control General → `domain/user_inputs.py` + `simulation/request_dto.py`

| Excel (Panel!celda) | Campo backend | Tipo | Estado |
|---------------------|---------------|------|--------|
| C5 — Servicio | `linea_negocio` | str | ✅ Presente |
| C6 — Nombre cliente actual | `cliente` | str | ✅ Presente |
| D6 — Nombre cliente nuevo | — | str | ⚠️ No hay campo separado; usar cliente |
| C7 — Antigüedad | `antiguedad_cliente` | str | ✅ Presente |
| C8 — Tipo de cliente | `tipo_cliente` | str | ✅ Presente |
| C9 — Período de pago (días) | `periodo_pago_dias` | int | ✅ Presente |
| C10 — Fecha Inicio | `fecha_inicio` | str | ✅ Presente |
| C11 — Duración meses | `meses_contrato` | int | ✅ Presente |
| C12 — Ciudad | `ciudad` | str | ✅ Presente |
| C13 — Sede | `sede` | str | ✅ Presente |
| C19 — % Ausentismo | `pct_ausentismo` | float | ✅ Presente |
| C20 — % Rotación | `pct_rotacion` | float | ✅ Presente |
| C21 — Costo financiación | `activa_financiacion` | bool | ✅ Presente |
| L6 — Componente Humano (indexación) | `componente_indexacion_humano` | str | ✅ Presente |
| L7 — Componente Tecnológico | `componente_indexacion_tecnologico` | str | ✅ Presente |
| L9 — Mes de Ajuste | — | int | ❌ FALTANTE en request_dto |
| L10 — Tasa interés mensual | `tasa_mensual_financ` | float | ✅ Presente |
| C63 — Margen objetivo A | `margen` | float | ✅ Presente |
| D63 — Margen objetivo B | — | float | ❌ FALTANTE: solo existe `margen` (cadena A) |
| E63 — Margen objetivo C | — | float | ❌ FALTANTE: no existe `margen_c` |
| C67 — Contingencia Operativa | `op_cont` | float | ✅ Presente |
| C68 — Contingencia Comercial | `com_cont` | float | ✅ Presente |
| C69 — Mark up | `markup` | float | ✅ Presente |
| C70 — Descuento volumen | `descuento` | float | ✅ Presente |
| C73 — Imprevistos | — | float | ❌ FALTANTE: no existe campo imprevistos |
| Pólizas activas C33:F55 | `polizas[]` (PolizaInput) | list | ✅ Parcialmente presente |
| M17/M30 — Cadena A activa | `cadenas_activas.cadena_a` | bool | ✅ Presente |
| N17/N30 — Cadena B activa | `cadenas_activas.cadena_b` | bool | ✅ Presente |
| O17/O30 — Cadena C activa | `cadenas_activas.cadena_c` | bool | ✅ Presente |

---

### Condiciones Cadena A → `simulation/chain_a/` + `domain/user_inputs.py`

| Excel | Campo backend | Estado |
|-------|---------------|--------|
| E14:S14 — Modalidad por perfil | `modalidad` en PerfilCadenaAInput | ✅ |
| E15:S15 — Canal por perfil | `canal` | ✅ |
| E16:S16 — Nombre perfil | `nombre_perfil` | ✅ |
| E17:S17 — FTE por perfil | `fte` | ✅ |
| E18:S18 — % Presencial | `pct_presencial` | ✅ |
| E21:S21 — % Comisiones | `comision_pct` | ✅ |
| E25:S48 — Ratio staffing staff | Calculado desde `Inputs de Nomina` | ✅ Via parametrización |
| W25:AK48 — Ratio (FTE agente / FTE staff) | `ratio_staffing` | ✅ Via parametrización HR |

---

### Inputs de Nomina → `repositories/payroll_parametrization_repository.py`

| Excel | Campo backend | Estado |
|-------|---------------|--------|
| C4 — SMMLV | `smmlv` en ParametrosNomina | ✅ |
| C5 — Auxilio Transporte | `auxilio_transporte` | ✅ |
| C6 — % Cumplimiento Variable | `pct_cumplimiento_variable` | ✅ |
| C7:C8 — Dotación anual/mensual | `costo_dotacion_mensual` | ✅ |
| I13:T13 — Tasas prestaciones | Tasas en ParametrosNomina | ✅ |
| C110:H133 — Ratios staffing | `ratios_staff` | ✅ |
| B16:B48 — Cargos | `nombre_cargo` en RolNomina | ✅ |
| C16:C48 — Salario base | `salario_base` | ✅ |
| AM16:AM48 — Costo empresa | `costo_empresa_mensual` | ✅ |

---

### Tasas, TRM, Polizas → `repositories/infrastructure_parametrization_repository.py`

| Excel | Campo backend | Estado |
|-------|---------------|--------|
| B4:G4 — IPC por año | `ipc_por_año` | ✅ |
| B5:G5 — SMLV por año | `smlv_por_año` | ✅ |
| B8:G9 — Factores acumulados | `factores_acumulados` | ✅ |
| B14:G16 — Factores por tipo indexación | `tabla_indexacion` | ✅ |
| B21:B28 — Pólizas base | `polizas_base` | ✅ |
| B29 — ICA (base) | `ica_base` | ✅ |
| B30 — GMF | `gmf` | ✅ |
| B34:F52 — ICA por municipio | `ica_por_municipio` | ✅ |

---

### Rot, Ausent y Rentabilidad → `repositories/parametrization_provider.py`

| Excel | Campo backend | Estado |
|-------|---------------|--------|
| B7:F12 — Ausentismo por servicio | `ausentismo_promedio` | ✅ |
| B18:F23 — Rotación por servicio | `rotacion_promedio` | ✅ |
| B29:C34 — Márgenes objetivo | `margen_minimo`, `margen_objetivo` | ✅ |
| B38:BI43 — Tabla ramp-up | `ramp_up_table` | ✅ |

---

## 2. Gaps Críticos Identificados

### GAP-1: Margen Independiente por Cadena B y C

**Excel:** `Panel!C63` (Cadena A), `Panel!D63` (Cadena B = 0.30 hardcode), `Panel!E63` (Cadena C = 0.20 hardcode)

**Backend actual:** Solo existe `margen` (un solo valor, corresponde a Cadena A)

**Impacto:** El pricing de Cadena B y C usa márgenes incorrectos.

**Corrección necesaria:**
```python
# En PanelDeControlRequest:
margen: float = 0.0           # Cadena A
margen_b: float = 0.30        # Cadena B (default Excel)
margen_c: float = 0.20        # Cadena C (default Excel)
```

---

### GAP-2: Mes de Ajuste de Indexación

**Excel:** `Panel!L9` — mes del año en que se aplica el ajuste anual (ej: 6 = junio)

**Backend actual:** No existe este campo en `PanelDeControlRequest`

**Impacto:** La indexación aplica en el mes incorrecto del ciclo anual.

**Corrección necesaria:**
```python
mes_ajuste_indexacion: int = 6  # default: mes 6
```

---

### GAP-3: Imprevistos

**Excel:** `Panel!C73` — porcentaje de imprevistos aplicado sobre ingreso bruto (resta del ingreso neto)

**Backend actual:** No existe en `PanelDeControlRequest`

**Impacto:** El ingreso neto del P&G no incluye la reducción por imprevistos.

**Corrección necesaria:**
```python
imprevistos: float = 0.0
```

---

### GAP-4: Visión Tarifas con Escenarios Múltiples

**Excel:** Hasta 5 escenarios comerciales con tarifas individuales por escenario

**Backend actual:** `EscenarioComercialInput` existe pero la lógica de calcular tarifa por escenario necesita verificación.

**Hoja Maestra Escenarios** repite bloque completo de cálculo por escenario. Cada escenario filtra FTE por canal+modalidad propio.

---

### GAP-5: Anomalía de Margen C en Vision Tarifas

**Excel:** `Vision Tarifas!C67` usa `$G$35` (margen Cadena A) para Cadena C  
**Backend:** El `VisionTarifasCalculator` debe replicar este comportamiento exacto (usar margen_a también para cadena_c en pricing, no margen_c).

---

### GAP-6: Tarifa FTE con Hardcode de 12 Meses

**Excel:** `Vision Tarifas!G45 = G43/C37/12` (12 hardcodeado)  
**Backend:** Debe usar `panel.meses_contrato` en lugar de 12.

Estado actual: `Hoja Maestra Escenarios!G21` usa `'Panel de Control General'!C11` (correcto). La Vision Tarifas tiene el hardcode.

---

### GAP-7: Cliente Nuevo vs Cliente Antiguo

**Excel:** 
- `Panel!C7 = IF(C6="CLIENTE NUEVO", "Cliente Nuevo", "Cliente Antiguo")` — fórmula
- Las vistas (`Vision Cost To Serve!B11`, `Visión P&G!C5`) muestran el nombre del cliente nuevo (D6) si es cliente nuevo, sino el actual (C6)

**Backend actual:** `antiguedad_cliente` captura la cadena, pero no existe lógica separada para nombre nuevo vs antiguo.

---

### GAP-8: Módulo SACO/Ventas (Comisiones por Resultados)

**Excel:** `Panel!C120:G143` — Facturación Variable SACO con niveles de productividad, comisiones, AIU por nivel

**Backend actual:** No verificado si existe un calculador específico para SACO/Ventas.

**Impacto:** Si el servicio es SACO o Ventas Multicanal, hay un componente de ingreso adicional (facturación variable por resultados) que puede no estar implementado.

---

## 3. Módulos Backend vs Hojas Excel

| Módulo Backend | Hoja Excel equivalente | Estado |
|----------------|----------------------|--------|
| `calculators/nomina.py` (NominaCalculator) | Nomina Loaded | ✅ Implementado |
| `calculators/no_payroll.py` (NoPayrollCalculator) | No payroll | ✅ Implementado |
| `calculators/cadena_b.py` (CadenaBCalculator) | Costo Fijo + Costo Variable | ✅ Implementado |
| `calculators/cadena_c.py` (CadenaCCalculator) | Costo Cadena C | ✅ Implementado |
| `calculators/costos_totales.py` | Costos Totales | ✅ Implementado |
| `calculators/costos_financieros.py` | Pólizas - Costo Financiacion | ✅ Implementado |
| `calculators/pyg.py` (PyGCalculator) | Visión P&G | ✅ Implementado |
| `calculators/vision_tarifas.py` | Vision Tarifas_Modelo_Cobro | ✅ Implementado |
| `calculators/cost_to_serve.py` | Vision Cost To Serve | ✅ Implementado |
| `calculators/riesgo.py` | Riesgo | ✅ Implementado |
| `calculators/kpis.py` | — (no tiene equivalente exacto en Excel) | ✅ Extra |
| — | Hoja Maestra Escenarios | ⚠️ Lógica distribuida en varios calculadores |
| — | Condiciones Cadena A (ratio staffing) | ✅ Via parametrización HR |
| — | Panel de Control General | ✅ Via domain/user_inputs |

---

## 4. Flujo de Datos en el Backend (Correspondencia con Excel)

```
UserInput (PanelDeControlRequest + Cadenas)
    ↓
SimulationContextBuilder → PricingRequest
    ↓
NexaPricingEngine.calcular()
    │
    ├── NominaCalculator         ← Nomina Loaded (costo empresa × ratio × indexación)
    ├── NoPayrollCalculator      ← No payroll (OPEX fijo + inversiones + estación)
    ├── CadenaBCalculator        ← Costo Fijo + Costo Variable (OPEX B, inversiones B, tarifas canal)
    ├── CadenaCCalculator        ← Costo Cadena C (tarifa proveedor + integración + variable)
    ├── CostosTotalesCalculator  ← Costos Totales (suma por canal)
    ├── CostosFinancierosCalculator ← Pólizas - Costo Financiacion (ICA, GMF, comisión adm, pólizas, financiación)
    ├── PyGCalculator            ← Visión P&G (ingresos, costos, margen, utilidad)
    └── VisionTarifasCalculator  ← Vision Tarifas (tarifa FTE, por transacción, por minuto)
```
