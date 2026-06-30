# CAPÍTULO 8: MATRIZ DE TRAZABILIDAD (Excel ↔ Backend ↔ API ↔ Fórmula)

**Versión**: V2-7 | **Actualización**: 2026-05-31 | **Estado**: Completado

---

## 8.1 Overview & Metodología

### Propósito

Este capítulo documenta la **trazabilidad bidireccional completa** del NEXA Pricing Engine, desde los inputs del usuario en Excel hasta los outputs visuales en las Visiones de Negocio. Cada cálculo, cada parámetro y cada resultado es rastreable a través de cinco capas:

1. **Fuente Excel**: Celda específica (Sheet!Row:Col)
2. **Modelo Backend**: Clase y campo Python (ClassName.field_name)
3. **Fórmula de Cálculo**: Expresión matemática e implementación en código
4. **Objeto Resultado**: Clase de dominio con el valor calculado
5. **Respuesta API**: DTO serializado en JSON (VisionV1, KpisV1, etc.)
6. **Visualización**: Renderizado final en Excel (Vision Tarifas, Vision P&G, etc.)

### Niveles de Trazabilidad

La trazabilidad se estructura en 6 niveles enlazados:

```
┌─────────────────────────────────────────────────────────────────┐
│ NIVEL 1: FUENTE EXCEL                                           │
│ Panel de Control!C9: margen = 20%                               │
└────────────────┬────────────────────────────────────────────────┘
                 │ [INPUT PARSING]
┌────────────────▼────────────────────────────────────────────────┐
│ NIVEL 2: MODELO BACKEND INPUT                                   │
│ PanelDeControlInput.margen = 0.20                               │
│ → PanelDeControl.margen = 0.20 (après context_builder)          │
└────────────────┬────────────────────────────────────────────────┘
                 │ [VALIDATION & STORAGE]
┌────────────────▼────────────────────────────────────────────────┐
│ NIVEL 3: CÁLCULO & FÓRMULA                                       │
│ factor_margen = (1 - margen) × (1 - op_cont) × ...             │
│ @ PyGCalculator.calcular_ingresos() línea 145                   │
└────────────────┬────────────────────────────────────────────────┘
                 │ [FORMULA EVALUATION]
┌────────────────▼────────────────────────────────────────────────┐
│ NIVEL 4: OBJETO RESULTADO                                        │
│ PyGMensual.ingreso_bruto_a: 500,000 COP                         │
│ PyGMensual.ingreso_neto: 410,000 COP                            │
└────────────────┬────────────────────────────────────────────────┘
                 │ [SERIALIZATION]
┌────────────────▼────────────────────────────────────────────────┐
│ NIVEL 5: RESPUESTA API                                           │
│ VisionPyGV1 { filas[2] { valores: [410000, ...] } }             │
│ KpisV1 { ingreso_mensual: 410000 }                              │
└────────────────┬────────────────────────────────────────────────┘
                 │ [FRONTEND RENDERING]
┌────────────────▼────────────────────────────────────────────────┐
│ NIVEL 6: VISUALIZACIÓN FINAL                                     │
│ Vision P&G → Fila "Ingreso Neto" → Columna "Mes 1" → 410,000   │
└─────────────────────────────────────────────────────────────────┘
```

### Garantías de Precisión

Cada paso mantiene las garantías siguientes:

- **Precisión monetaria**: Valores en COP, redondeo HALF_UP a centavos
- **Consistencia de tipos**: Excel float → Python Decimal → JSON float preserva exactitud
- **Documentación de conversión**: Conversiones Excel↔Python documentadas donde existen
- **Reversibilidad**: Cada campo es re-calculable desde sus inputs originales
- **Auditoría**: Trace completo disponible en `audit_trace` de PricingResult

---

## 8.2 Trazabilidad del Panel de Control

### Panel de Control General (Excel Sheet)

El Panel de Control General es la fuente única de todos los parámetros maestros del deal. Cada celda mapea a:

1. Un campo en `PanelDeControlInput` (desde API)
2. Un campo en `PanelDeControl` (dominio)
3. Uno o más calculadores que lo consumen
4. Uno o más campos de resultado que genera

#### Tabla: Mapeo Panel → Backend → Fórmulas → Outputs

| Excel Sheet | Cell | Campo | Rango | Backend Model | Calculador | Fórmula | Output DTO | Vision |
|---|---|---|---|---|---|---|---|---|
| **Panel!C5** | Cliente | cliente | string | PanelDeControl.cliente | (entrada) | identity | EntryDataV1 | ResumenEjecutivoPyG.cliente |
| **Panel!C9** | Margen | margen | 0.00–0.50 | PanelDeControl.margen | PyGCalculator | factor_margen = (1-margen) | VisionPyG | Vision Tarifas C25 |
| **Panel!C10** | Contingencia Operativa | op_cont | 0.00–0.10 | PanelDeControl.op_cont | PyGCalculator | contingen_op = op_cont × ingreso_bruto_a | PyGMensual.contingencia_op | VisionPyG I12 |
| **Panel!C11** | Contingencia Comercial | com_cont | 0.00–0.05 | PanelDeControl.com_cont | PyGCalculator | contingen_com = com_cont × ingreso_bruto | PyGMensual.contingencia_com | VisionPyG I13 |
| **Panel!C12** | Markup | markup | -1.00–10.00 | PanelDeControl.markup | PyGCalculator | markup_ing = markup × ingreso_bruto | PyGMensual.markup_ingreso | VisionPyG I14 |
| **Panel!C13** | Descuento | descuento | 0.00–1.00 | PanelDeControl.descuento | PyGCalculator | descuento_ing = descuento × ingreso_bruto | PyGMensual.descuento_ingreso | VisionPyG I15 |
| **Panel!C14** | Imprevistos (V2-5) | imprevistos | 0.00–0.20 | PanelDeControl.imprevistos | PyGCalculator | imprevistos = imprevistos × ingreso_bruto | PyGMensual.imprevistos_ingreso | VisionPyG I16 |
| **Panel!C15** | Meses Contrato | meses_contrato | 1–120 | PanelDeControl.meses_contrato | (múltiples) | divisor en amortizaciones | VisionPyG | Resumen ejecutivo |
| **Panel!C16** | % Rotación | pct_rotacion | 0.00–1.00 | PanelDeControl.pct_rotacion | NominaCalculator | capacitacion_rot = fte × pct_rot × dias | ResultadoNomina.capacitacion_rotacion | DesgloseCTSCadenaA |
| **Panel!C17** | Período Pago (días) | periodo_pago_dias | 0–365 | PanelDeControl.periodo_pago_dias | CostosFinancierosCalculator | factor_fin = periodo_dias / 30 | PyGMensual.financiacion | VisionPyG F19 |
| **Panel!C18** | Activa Financiación | activa_financiacion | true\|false | PanelDeControl.activa_financiacion | CostosFinancierosCalculator | if not activa: fin=0 | PyGMensual.financiacion | VisionPyG F19 |
| **Panel!C19** | Tasa ICA | tasa_ica | 0.0001–0.0100 | PanelDeControl.tasa_ica | CostosFinancierosCalculator | ICA = base_gross_up × tasa_ica | PyGMensual.ica | VisionPyG F17 |
| **Panel!C20** | Tasa GMF | tasa_gmf | 0.0001–0.0050 | PanelDeControl.tasa_gmf | CostosFinancierosCalculator | GMF = base × tasa_gmf | PyGMensual.gmf | VisionPyG F18 |
| **Panel!C21** | Tasa Mensual Financ | tasa_mensual_financ | 0.0001–0.1000 | PanelDeControl.tasa_mensual_financ | CostosFinancierosCalculator | fin = costo × tasa_mens × factor_periodo | PyGMensual.financiacion | VisionPyG F19 |
| **Panel!C22** | ICA Override (V2-7) | tasa_ica | 0–0.01 | PanelDeControl.tasa_ica | CostosFinancierosCalculator | same as C19 | PyGMensual.ica | VisionPyG F17 |
| **Panel!D5** | % Aumento Salarial | pct_aumento_salarial | 0.00–0.30 | PanelDeControl.pct_aumento_salarial | PayrollCalculator | factor_aumento = (1+pct)^años_transcurridos | (propagates to all salarios) | VisionPyG A34-A40 |
| **Panel!D7** | Margen Cadena B (V2-7) | margen_b | 0.00–0.50 | PanelDeControl.margen_b | CadenaBCalculator | factor_billing_b = (1-margen_b) | ResultadoCadenaB.total | VisionPyG B58 |
| **Panel!D8** | Margen Cadena C (V2-7) | margen_c | 0.00–0.50 | PanelDeControl.margen_c | CadenaCCalculator | factor_billing_c = (1-margen_c) | ResultadoCadenaC.total | VisionPyG B59 |

#### Ejemplo de Cálculo Completo: Margen

**Contexto**: Deal con margen=0.20 (20%), op_cont=0.03, meses_contrato=24

**Flujo**:

1. **Excel**: Panel!C9 = 0.20 (usuario ingresa)
2. **Backend Input**: `PanelDeControlInput(margen=0.20)`
3. **Context Builder**: `PanelDeControl.margen = 0.20`
4. **PyGCalculator**: 
   ```python
   factor_margen = (1 - panel.margen) × (1 - panel.op_cont) × ...
   factor_margen = (1 - 0.20) × (1 - 0.03) = 0.80 × 0.97 = 0.776
   ```
5. **Resultado**: `factor_billing_a = 0.776` (invierte factor de ingreso)
   ```python
   ingreso_a = costo_a / factor_margen = 1,000,000 / 0.776 = 1,288,659 COP
   ```
6. **API**: `VisionPyGV1.filas[0].valores[m] = 1288659`
7. **Vision**: Vision P&G, fila "Ingreso Bruto A", mes 1 = 1,288,659

---

## 8.3 Trazabilidad de Nómina Cargada (Payroll)

### Componentes de Costo de Nómina

Cada perfil de Cadena A genera un `ResultadoNomina` con 7 componentes. El cálculo sigue estas reglas:

#### Tabla: Nómina Cargada → Componentes → Fórmulas

| Componente | Excel Fuente | Input | Calculador | Fórmula | Resultado | Vision |
|---|---|---|---|---|---|---|
| **Salario Fijo** | Nomina Loaded!B + Parámetros HR | salario_base, fte, factor_indexacion | NominaCalculator.salario_fijo() | salario_base × fte × factor_indexacion | ResultadoNomina.salario_fijo | VisionPyG I34 |
| **Comisiones** | Condiciones Cadena A!D | comision_pct | NominaCalculator.comisiones() | salario_base × fte × comision_pct × factor_indexacion | ResultadoNomina.comisiones | VisionPyG I35 |
| **Capacitación Inicial** | HR Parámetros (tarifa días) | dias_cap_inicial, tarifa_dia_cap | NominaCalculator.capacitacion_inicial() | (dias × tarifa × fte / meses_contrato) × factor | ResultadoNomina.capacitacion_inicial | VisionPyG I36 |
| **Capacitación Rotación** | HR Parámetros + Panel C16 | dias_cap_rot, pct_rotacion | NominaCalculator.capacitacion_rotacion() | dias × tarifa × (fte × pct_rot) × factor | ResultadoNomina.capacitacion_rotacion | VisionPyG I37 |
| **Exámenes Médicos** | HR Parámetros (3-part formula) | costo_examen, fte_examenes | NominaCalculator.examenes() | costo × (1/meses + pct_rot + pct_anual/12) × fte_eff × factor | ResultadoNomina.examenes | VisionPyG I38 |
| **Estudios Seguridad** | HR Parámetros (costo unitario) | costo_estudio, fte | NominaCalculator.seguridad() | costo × fte × factor | ResultadoNomina.seguridad | VisionPyG I39 |
| **Crucero** | Panel!C17 (V2-7) | tarifa_crucero, fte | NominaCalculator.crucero() | tarifa_crucero × fte × factor | ResultadoNomina.crucero | VisionPyG I40 |
| **TOTAL NÓMINA** | (suma de arriba) | todos | (aggregación) | sum(all 7 components) | ResultadoNomina.total | VisionPyG B48 |

#### Factor de Indexación Salarial

Cada mes aplica un factor que ajusta salarios según inflación y aumento del deal:

```
factor_indexacion[mes] = factor_base_año × factor_aumento[mes]

donde:
  factor_base_año      = lookup en ParametrosNomina.factor_indexacion (ej. 1.08 para 2026)
  factor_aumento[mes]  = (1 + pct_aumento_salarial) ^ (años_desde_inicio)
```

**Ejemplo**: Contrato comienza enero 2026, pct_aumento_salarial = 8% anual, mes 13

```
factor_indexacion[13] = 1.08 (2026) × (1.08)^1 = 1.08 × 1.08 = 1.1664
salario_mes_13 = salario_base × 1.1664
```

#### FTE Efectivo para Exámenes

Los exámenes se aplican no solo a los agentes, sino también a los supervisores, formadores y monitores que ingresan nuevo.

```
fte_examenes = fte_agentes + fte_supervisor + fte_formador + fte_monitor
             = fte_agentes × (1 + ratio_supervisor + ratio_formador + ratio_monitor)
```

Esta agregación se realiza en `special_roles_calculator.py`:

```python
def calcular_fte_efectivo(perfil_cadena_a, ratios_staff):
    base = perfil_cadena_a.fte
    supervisores = base / ratios_staff['supervisor']
    formadores = base / ratios_staff['formador']
    monitores = base / ratios_staff['monitor']
    return base + supervisores + formadores + monitores
```

---

## 8.4 Trazabilidad de Ratios & Staffing

### Cálculo de FTE de Roles de Soporte

El cálculo del personal de soporte (supervisores, formadores, monitores, etc.) es determinístico:

#### Tabla: Staffing Ratios

| Rol Soporte | Ratio Estándar | Fórmula en Backend | Resultado | Uso en Vision |
|---|---|---|---|---|
| Supervisor | 1:8 (ratio_supervisor = 8) | fte_agentes / 8 | fte_supervisor | Staffing dataset + KPIs |
| Formador | 1:20 | fte_agentes / 20 | fte_formador | Staffing dataset + K50 CTS |
| Monitor QA | 1:25 | fte_agentes / 25 | fte_monitor | Staffing dataset + examenes |
| Especialista Proyectos | 1:25 | fte_agentes / 25 | fte_especialista | Staffing dataset |

**Normalización de Nombres de Roles**

Los roles en Excel usan nombres libres (ej. "Gestor Bancamía", "Specialist XYZ"), pero el backend necesita un nombre canónico para buscar salarios. La normalización se hace en `special_roles_calculator.py`:

```python
def _normalize_rol(rol_name: str) -> str:
    """
    Normaliza nombres de rol para lookup en ParametrosNomina.
    Ejemplos:
      "Agente Telefónico"      → "agente_telefonica"
      "Supervisor Inbound"     → "supervisor_inbound"
      "Especialista Proyectos" → "especialista_proyectos"
    """
    return rol_name.lower().replace(" ", "_")
```

---

## 8.5 Trazabilidad de Vision Tarifas

### Jerarquía de Vision Tarifas

La Vision Tarifas es una vista jerárquica compleja que condensa:

- Encabezados del deal (cliente, FTE, volumen)
- Tarifas por canal (fixed, variable, blended)
- Escenarios comerciales (up to 5 scenarios per deal)
- Componentes de costo (detalle de fixed/variable cost)
- Denominadores de CTS (K50, L50, M50)

#### Tabla: Excel Vision Tarifas → Backend → API

| Sección Excel | Filas Excel | Componente | Input | Calculador | Output | API Field |
|---|---|---|---|---|---|---|
| **ENCABEZADOS** | 1–15 | Metadata | Panel + Perfiles | VisionTarifasCalculator | TarifasEncabezado | VisionTarifasV1.encabezado |
| **FACTORES MÁRGENES** | C63–E70 | Margin adjust | margen, op_cont, com_cont, markup, descuento | PyGCalculator | factor_margen (×5 campos) | VisionTarifasV1.factores |
| **COMPONENTES FIJOS** | 117–128 | Fixed component | salario+cap+examen+seguro+crucero | NominaCalculator | (aggregado) | VisionTarifasV1.componente_fijo_detalle |
| **COMISIONES** | 130–143 | Variable component | comision_pct × salario | (directo) | (aggregado) | VisionTarifasV1.componente_variable_detalle |
| **DENOMINADORES CTS** | K50, L50, M50 (ref) | Volume by cadena | vol_cadena_a + vol_cadena_b + vol_cadena_c | CostToServeCalculator | K50_fte, L50_vol, M50_vol | VisionTarifasV1.ctus_denominadores |
| **ESCENARIOS** | 81–113 | Commercial scenarios | escenarios_input[] | EscenarioComercialV1 | EscenarioTarifas[] | VisionTarifasV1.escenarios_detalle |
| **FINANCIERO** | (ref rows) | Financial attribution | ICA, GMF, pólizas, fin | CostosFinancierosCalculator | costo_financiero_vt_cadena_a | VisionTarifasV1.desglose_fin |

#### Denominadores de CTS (K50, L50, M50)

Los denominadores son críticos para el cálculo de tarifa por transacción o por minuto:

**K50** (Volumen Cadena A):
- Inbound: = J_inbound × N_inbound (transacciones del mes)
- Outbound: = FTE × supuesto 500 transacciones/FTE (valor estándar)

```python
def calcular_k50(perfil_cadena_a, es_inbound):
    if es_inbound:
        return perfil_cadena_a.vol_cadena_a_mensual  # J×N de Excel
    else:
        return perfil_cadena_a.fte × 500  # convención outbound
```

**L50** (Volumen Cadena B):
- = suma de volúmenes por canal en CondicionesCadenaBInput

**M50** (Volumen Cadena C):
- = volumen mensual del proveedor

---

## 8.6 Trazabilidad del Estado P&G

### Estructura de Vision P&G

La Vision P&G es una tabla de ingresos, costos y resultados por mes. Cada fila mapea a:

1. Una fuente en Excel (Sheet row)
2. Un componente de cálculo (calculador específico)
3. Un campo en PyGMensual
4. Una fila en VisionPyGV1

#### Tabla: Estado P&G Completo (Filas Principales)

| Sección | Fila Excel | Etiqueta | Entrada | Calculador | Fórmula | PyGMensual | API |
|---|---|---|---|---|---|---|---|
| **INGRESOS** |||||||||
| | A41 | Ingreso Bruto A | costo_a, factor_billing | PyGCalculator | ingreso_a = costo_a / factor_margen | ingreso_bruto_a | VisionPyG[0] |
| | A42 | Ingreso Bruto B | costo_b, margen_b | PyGCalculator | ingreso_b = costo_b / (1-margen_b) | ingreso_bruto_b | VisionPyG[1] |
| | A43 | Ingreso Bruto C | costo_c, margen_c | PyGCalculator | ingreso_c = costo_c / (1-margen_c) | ingreso_bruto_c | VisionPyG[2] |
| | A44–A45 | Contingencias | op_cont, com_cont | PyGCalculator | cont = % × ingreso_bruto | contingencia_* | VisionPyG[3–4] |
| | A46 | Markup/Descuento | markup, descuento | PyGCalculator | mk−desc = % × ingreso | markup_ingreso | VisionPyG[5] |
| | A47 | Imprevistos (V2-5) | imprevistos | PyGCalculator | imprevistos = % × ingreso | imprevistos_ingreso | VisionPyG[6] |
| | A48 | **Ingreso Neto** | (suma de arriba) | (agregación) | = A41+A42+A43+A44–A45–A47 | ingreso_neto (property) | VisionPyG[7] |
| **COSTOS OP** |||||||||
| | B49–B55 | Nómina A (detalle) | ResultadoNomina.* | NominaCalculator | (per component) | payroll_a | VisionPyG[8–14] |
| | B56–B58 | No-Payroll A | ResultadoNoPayroll.* | NoPayrollCalculator | (per component) | no_payroll_a | VisionPyG[15–17] |
| | B59 | Cadena B | ResultadoCadenaB.total | CadenaBCalculator | (aggregado) | costo_b | VisionPyG[18] |
| | B60 | Cadena C | ResultadoCadenaC.total_pyg | CadenaCCalculator | (aggregado) | costo_c | VisionPyG[19] |
| | B61 | **Costo Operativo** | (suma de arriba) | (agregación) | = B49+B56+B59+B60 | costo_operativo (property) | VisionPyG[20] |
| **COSTOS FIN** |||||||||
| | C62 | ICA | costo_a+costo_b+costo_c_fin, tasa_ica | CostosFinancierosCalculator | ICA = (costo/factor_margen + poliza + fin) × tasa_ica | ica | VisionPyG[21] |
| | C63 | GMF | costo_total, tasa_gmf | CostosFinancierosCalculator | GMF = costo × tasa_gmf | gmf | VisionPyG[22] |
| | C64 | Pólizas | polizas[] (storage) | CostosFinancierosCalculator | POLIZA = (costo + fin) × tasa_poliza | polizas | VisionPyG[23] |
| | C65 | Financiación | costo_mes_anterior, tasa_mensual, periodo | CostosFinancierosCalculator | FIN = costo_anterior × tasa × (dias/30) | financiacion | VisionPyG[24] |
| | C66 | Comisión Adm (V2-5) | polizas + pct_com_adm | CostosFinancierosCalculator | COM_ADM = POLIZA × 1.42 | comision_administracion | VisionPyG[25] |
| | C67 | **Costos Financieros** | (suma de arriba) | (agregación) | = C62+C63+C64+C65+C66 | costos_financieros (property) | VisionPyG[26] |
| **RESULTADOS** |||||||||
| | D68 | Contribución | ingreso_neto − costo_op | (directo) | = A48 − B61 | contribucion (property) | VisionPyG[27] |
| | D69 | **Utilidad Neta** | ingreso_neto − costo_total | (directo) | = A48 − (B61 + C67) | utilidad_neta (property) | VisionPyG[28] |
| | D70 | **% Utilidad** | utilidad_neta / ingreso_neto | (directo) | = D69 / A48 | pct_utilidad_neta (property) | VisionPyG[29] |

### Orden de Cálculo y Dependencias

El orden de cálculo es crítico porque algunos componentes dependen de otros:

```
1. [INDEPENDIENTE] Nómina (Salario + Capacitación + Exámenes) 
   → ResultadoNomina
   
2. [INDEPENDIENTE] No-Payroll (OPEX TI + CAPEX)
   → ResultadoNoPayroll
   
3. [INDEPENDIENTE] Cadena B (OPEX variable + Inversiones + S&M)
   → ResultadoCadenaB
   
4. [INDEPENDIENTE] Cadena C (Tarifa proveedor + OPEX + Inversiones)
   → ResultadoCadenaC
   
5. [DEPENDE DE 1-4] Costos Totales Mes (Costo A + B + C)
   → CostosTotalesMes
   
6. [DEPENDE DE 5] Ingresos P&G (aplicar factor_margen inverso)
   → PyGMensual.ingreso_bruto_*
   
7. [DEPENDE DE 5] Costos Financieros (ICA, GMF, Pólizas, Financiación)
   → CostosFinancierosMes
   
8. [DEPENDE DE 6-7] Estado P&G Completo (Contribución, Utilidad, %)
   → PyGMensual (propiedades calculadas)
   
9. [DEPENDE DE 8] KPIs del Deal (promedios, totales)
   → KPIsDeal
```

---

## 8.7 Trazabilidad de Costos Financieros

### Componentes Financieros

Los costos financieros se calculan en orden específico porque tienen dependencias:

#### 1. Financiación

**Base**: Costo operativo del mes anterior (convención: TC adelanta capital)

```python
financiacion = costo_anterior × tasa_mensual_financ × (periodo_pago_dias / 30)
```

**Entrada**: 
- `panel.tasa_mensual_financ` (ej. 0.02 = 2% mensual)
- `panel.periodo_pago_dias` (ej. 90 días)
- `costo_mes_anterior` (ej. 1,000,000 COP)

**Cálculo**:
```
financiacion = 1,000,000 × 0.02 × (90/30) = 1,000,000 × 0.02 × 3 = 60,000 COP
```

#### 2. Pólizas

**Base**: Costo operativo + financiación

Cada póliza se aplica según:
- `pct_poliza`: tasa de prima (ej. 0.0062 = 0.62%)
- `pct_atribuible`: fracción atribuible (ej. 0.20 = 20%)
- `aplica_extension`: extiende a meses específicos si es true
- `per_canal`: aparece en Vision Tarifas por canal si true

```python
poliza_total = (costo_a + costo_b + costo_c_fin + financiacion) × pct_poliza × pct_atribuible
```

#### 3. ICA (Impuesto sobre la Renta)

**Base**: `(costo/factor_margen + poliza + financiacion)` — gross-up

El gross-up refleja que el impuesto recae sobre la renta neta (ingreso menos costo):

```python
base_ica = (costo / factor_margen + poliza + financiacion)
ica = base_ica × tasa_ica
```

#### 4. GMF (Gravamen Movimiento Financiero)

**Base**: `costo + poliza + financiacion` — sin gross-up

```python
gmf = (costo + poliza + financiacion) × tasa_gmf
```

#### 5. Comisión de Administración (V2-5)

**Base**: Pólizas × 1.42 (multiplicador administrativo)

```python
comision_administracion = poliza_total × 1.42
```

---

## 8.8 Trazabilidad de Cadena B

### Componentes de Cadena B

Cadena B incluye canales digitales (WhatsApp, Token IA, WebChat) con sus propios costos:

#### Tabla: Cadena B Componentes

| Componente | Input | Fórmula | Resultado | Vision P&G |
|---|---|---|---|---|
| OPEX Fijo | CondicionesCadenaBInput.canales[].opex_fijo | sum por canal activo | ResultadoCadenaB.opex_fijo | B57 |
| Tarifa Canal Variable | CondicionesCadenaBInput.canales[].tarifa_unitaria × volumen | sum por canal | ResultadoCadenaB.costo_variable | (implicit in total) |
| Consumo Variable (Token IA, WhatsApp min) | CondicionesCadenaBInput.opex_consumo_variable[] | valor_unitario × cantidad | (part of costo_variable) | (implicit) |
| Escalamiento | CondicionesCadenaBInput.canales[].pct_escalamiento × costo_base | sum | ResultadoCadenaB.escalamiento | B61 |
| Inversiones | CondicionesCadenaBInput.canales[].inversiones | sum | ResultadoCadenaB.inversiones | B59 |
| S&M (Sales & Marketing) | CondicionesCadenaBInput.equipo_sm[] | salario_cargado_rol × pct_dedicacion × fte_sm | ResultadoCadenaB.soporte_mantenimiento | B60 |
| HITL (Human-in-the-Loop) | CondicionesCadenaBInput.hitl_equipo[] | same as S&M | ResultadoCadenaB.hitl | (implicit) |
| **TOTAL CADENA B** | (suma de arriba) | = OPEX + Tarifa + Escalamiento + Inv + S&M + HITL | ResultadoCadenaB.total | B58 |

---

## 8.9 Trazabilidad de Cadena C

### Componentes de Cadena C

Cadena C incluye outsourcing a proveedores (BPO partner, cloud service):

#### Tabla: Cadena C Componentes

| Componente | Input | Fórmula | Resultado | Vision P&G |
|---|---|---|---|---|
| Tarifa Proveedor | CondicionesCadenaC.tarifa_proveedor_mensual | (directo) | ResultadoCadenaC.tarifa_proveedor | C59 |
| OPEX Fijo Integración | CondicionesCadenaC.opex_fijo_integracion | (directo) | ResultadoCadenaC.opex_fijo_integ | (implicit) |
| OPEX Variable Integración | CondicionesCadenaC.opex_variable_integ | (directo) | ResultadoCadenaC.opex_var_integ | (NOT in P&G, only in CTS) |
| Inversiones | CondicionesCadenaC.inversiones | (directo) | ResultadoCadenaC.inversiones | (implicit) |
| Equipo Integración | CondicionesCadenaC.equipo_integ[] | (same as S&M) | ResultadoCadenaC.equipo_integ | (NOT in P&G) |
| Escalamiento | CondicionesCadenaC.escalamiento | (directo) | ResultadoCadenaC.escalamiento | C62 |
| HITL | CondicionesCadenaC.hitl_equipo[] | (same as S&M) | ResultadoCadenaC.hitl | (NOT in P&G) |
| **TOTAL CADENA C (P&G)** | (suma selectiva) | tarifa + opex_fijo + inv + escalamiento | ResultadoCadenaC.total_pyg | C59 |
| **TOTAL CADENA C (FIN)** | (suma completa) | + opex_var + equipo + hitl (para ICA/GMF) | ResultadoCadenaC.total | (financial base) |

**NOTA**: El campo `total_pyg` excluye `opex_var_integ`, `equipo_integ` y `hitl` porque estos fluyen a la base financiera pero no aparecen en el P&G displayable. Esto mantiene el P&G limpio mientras se contabiliza financieramente el costo completo.

---

## 8.10 Validación Técnica & Garantías

### Precisión de Tipos

La ruta de datos de Excel a API preserva exactitud mediante:

1. **Excel → Backend**: valores de double IEEE 754 (Excel) → Decimal Python (precisión arbitraria)
2. **Cálculo**: todas las operaciones en Decimal para evitar pérdida de precisión
3. **Backend → API**: Decimal → JSON float64 redondeado HALF_UP a centavos

**Ejemplo**: Margen 18.5% en Excel

```
Excel:        0.185 (IEEE 754)
Input:        PanelDeControlInput.margen = 0.185
Model:        PanelDeControl.margen = Decimal('0.185')
Calc:         (1 - 0.185) × ... = Decimal('0.815') × ...
API JSON:     "margen": 0.815 (float64)
Vision:       Vision Tarifas C25 = 81.5%
```

### Auditoría & Trazabilidad

Cada `PricingResult` incluye un campo `audit_trace` que mapea:

```python
audit_trace = {
    "panel": {...},  # valores de entrada exactos
    "costos_mensuales": [
        {
            "mes": 1,
            "costo_a": 1000000,
            "costo_b": 200000,
            "costo_c": 150000,
            "ingreso_a": 1234567,
            "ingreso_neto": 1384567,
            "utilidad": 34567
        },
        ...
    ],
    "kpis": {...},
    "errors": []
}
```

### Conversión de Unidades

| Magnitud | Excel | Backend | API | Nota |
|---|---|---|---|---|
| Dinero (COP) | número con formato | Decimal/float | float | redondeo HALF_UP a centavos |
| Porcentaje | 0–100 (mostrado) | 0.0–1.0 (almacenado) | 0.0–1.0 | ej. 18% Excel = 0.18 backend |
| Meses | 1–120 | int | int | ninguna conversión |
| FTE | 1.5, 2.0, etc. | float | float | decimales permitidos |
| Días | 1–365 | int | int | duraciones estándar |
| Ratio | "1:8" (texto) | 8.0 (float) | 8.0 | "1:8" supervisor → ratio 8 |

### Nulabilidad & Defaults

Cada campo tiene una política definida:

| Campo | Nulo en Input | Default Backend | Uso |
|---|---|---|---|
| `pct_rotacion` | null | lookup por línea_negocio | si null, usar storage |
| `tasa_ica` | null | lookup por ciudad | si null, lookup por ICA actual ciudad |
| `margen_b` | null | lookup en v2_7_defaults | si null, usar default operativo |
| `comision_pct` (perfil) | (never null) | 0.0 | si no provided, 0% |
| `salario_base` (override) | null | lookup por rol | si null, buscar rol en storage |

---

## 8.11 Resumen de Flujos Críticos

### Flujo 1: Desde Margen hasta Tarifa por FTE

```
Panel!C9 (margen=0.20)
  ↓
PanelDeControl.margen
  ↓
PyGCalculator.calcular_margen_inverso()
  → factor_margen = 0.776
  ↓
VisionTarifasCalculator.calcular_tarifa_fijo()
  → tarifa_fijo_fte = costo_a / (factor_margen × k50_fte)
  ↓
VisionTarifasV1.canales[0].tarifa_fijo_fte = 1,289 COP/FTE
  ↓
Vision Tarifas (Excel print) → Tarifa Fijo FTE
```

### Flujo 2: Desde Salario Base hasta Costo Total Nómina

```
HR Parámetros (salario_agente=2,000,000)
  + Panel pct_aumento=0.08
  ↓
ParametrosNomina.salario_base × factor_indexacion
  ↓
NominaCalculator.salario_fijo() → 2,160,000 (mes 2)
  ↓
ResultadoNomina.salario_fijo
  + ResultadoNomina.capacitacion_inicial
  + ResultadoNomina.examenes
  + ... (otros componentes)
  ↓
ResultadoNomina.total = 2,450,000
  ↓
CostosTotalesMes.payroll_a = 2,450,000 × FTE_agentes
  ↓
PyGMensual.payroll_a
  ↓
VisionPyGV1.filas[8].valores[m]
  ↓
Vision P&G → Salario Fijo row, mes 1
```

### Flujo 3: Desde Costo hasta Ingreso (inversión del margen)

```
CostosTotalesMes.costo_a = 1,000,000
  + CostosTotalesMes.costo_b = 200,000
  + CostosTotalesMes.costo_c = 150,000
  ↓
CostosTotalesMes.total = 1,350,000
  ↓
factor_margen = (1 - 0.20) × (1 - 0.03) = 0.776
  ↓
PyGCalculator.calcular_ingreso()
  → ingreso_bruto = 1,350,000 / 0.776 = 1,739,175 COP
  ↓
PyGMensual.ingreso_bruto_a + ingreso_bruto_b + ingreso_bruto_c
  ↓
VisionPyGV1.filas[0].valores[m] = 1,739,175
  ↓
Vision P&G → Ingreso Bruto Total
```

### Flujo 4: Desde Pólizas de Storage hasta ICA

```
ParametrizationProvider.get_polizas(ciudad, linea_negocio, mes)
  → [Poliza("Responsabilidad Civil", 0.005, 0.20), ...]
  ↓
CostosFinancierosCalculator.calcular_polizas()
  → poliza_total = costo_fin × 0.005 × 0.20 = 15,000
  ↓
CostosTotalesMes + financiacion → base_ica
  ↓
CostosFinancierosCalculator.calcular_ica()
  → ICA = base_ica × tasa_ica = base_ica × 0.0033
  ↓
CostosFinancierosMes.ica = 18,500
  ↓
PyGMensual.ica = 18,500
  ↓
VisionPyGV1.filas[21].valores[m] = 18,500
  ↓
Vision P&G → ICA row
```

---

## 8.12 Conclusión

La matriz de trazabilidad presentada en este capítulo establece la **cadena de custodia completa** de datos desde inputs de usuario (Excel) hasta resultados visuales (Vision). Cada campo, cada fórmula y cada componente es rastreable, verificable y auditable.

**Garantías que proporciona esta trazabilidad**:

1. **Exactitud**: Cada valor resultante es reproducible desde los inputs
2. **Auditoría**: Trazas completas disponibles para inspección
3. **Mantenimiento**: Cambios de fórmula documentados y localizables
4. **Testing**: Cada nivel es testeable de forma independiente
5. **Compliance**: Documentación para auditorías financieras y regulatorias

---

## Tabla de Referencias Cruzadas

| Sección | Componentes | Código Relevante | Test |
|---|---|---|---|
| 8.2 Panel | Márgenes, tasas, períodos | `domain/models/panel.py`, `calculators/pyg.py` | `tests/unit/test_panel.py` |
| 8.3 Nómina | Salario, capacitación, exámenes | `calculators/nomina.py`, `domain/services/nomina_cargada.py` | `tests/unit/test_nomina.py` |
| 8.4 Staffing | FTE de soporte, ratios | `domain/services/special_roles_calculator.py` | `tests/unit/test_staffing.py` |
| 8.5 Vision Tarifas | Jerarquía, denominadores | `calculators/vision_tarifas.py` | `tests/integration/test_vision_tarifas.py` |
| 8.6 P&G | Ingresos, costos, resultados | `calculators/vision_pyg.py`, `calculators/pyg.py` | `tests/integration/test_pyg.py` |
| 8.7 Costos Financieros | ICA, GMF, pólizas, financiación | `calculators/costos_financieros.py` | `tests/unit/test_costos_financieros.py` |
| 8.8 Cadena B | Canales digitales, S&M | `calculators/cadena_b.py` | `tests/unit/test_cadena_b.py` |
| 8.9 Cadena C | Outsourcing, integración | `calculators/cadena_c.py` | `tests/unit/test_cadena_c.py` |

---

**Documento preparado para auditoría financiera, verificación de conformidad Excel V2-7 y testing automatizado.**

**Estado**: COMPLETADO | Versión: V2-7 | Fecha: 2026-05-31
