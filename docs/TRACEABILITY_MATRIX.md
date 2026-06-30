# TRACEABILITY_MATRIX.md — Machine-Readable Reference

**Purpose**: Self-contained lookup reference for tool automation, test generation, audit tracing, and formula verification.

**Status**: Updated 2026-05-31 | **Version**: V2-7

---

## 1. PANEL DE CONTROL INPUTS

### 1.1 Cliente & Contexto

```
FIELD: cliente
  Excel Source: Panel!C5
  Backend Model: PanelDeControl.cliente
  Type: str
  Validation: non-empty, max 255 chars
  Formula: identity (no calculation)
  Calculator: (input only)
  Result Field: (none)
  Vision Output: ResumenEjecutivoPyG.cliente
  API Field: VisionPyGV1.resumen.cliente
  Example: cliente="Bancamía" → Vision P&G header = "Bancamía"
  Notes: Metadata only; no impact on calculations
  Status: Core | Version: V1.0
```

### 1.2 Márgenes de Ingreso

```
FIELD: margen
  Excel Source: Panel!C9
  Backend Model: PanelDeControl.margen
  Type: float | Range: 0.00–0.50
  Unit: ratio (0=0%, 1=100%)
  Validation: 0.0 <= margen <= 0.50
  Formula: factor_margen = (1 - margen) × (1 - op_cont) × (1 - com_cont)
           ingreso_a = costo_a / factor_margen
  Calculator: PyGCalculator.calcular_ingresos()
  Result Field: PyGMensual.ingreso_bruto_a (+ _b, _c for each cadena)
  Vision Output: Vision Tarifas C25 (factor display)
  API Field: VisionPyGV1.filas[0].valores[m] (Ingreso Bruto A)
  Example: margen=0.20, op_cont=0.03, costo_a=1M 
           → factor = 0.80 × 0.97 = 0.776
           → ingreso_a = 1M / 0.776 = 1.288M COP
  Numerical Example (12-month):
    mes 1: margen=0.20 → ingreso_bruto=1,288,659 COP
    mes 12: margen=0.20 → ingreso_bruto=1,288,659 COP (same, no indexación)
  Notes: User-configurable margin. Inverts to calculate required revenue.
         Drives all income calculations for Cadena A.
         Critical for profitability analysis.
  Status: Core | Version: V1.0 | New in V2-5: (no change)
```

```
FIELD: margen_b [NEW V2-7]
  Excel Source: Panel!D7
  Backend Model: PanelDeControl.margen_b
  Type: float | Range: 0.00–0.50
  Unit: ratio
  Validation: 0.0 <= margen_b <= 0.50
  Default: lookup from v2_7_defaults if None
  Formula: factor_billing_b = (1 - margen_b)
           ingreso_b = costo_b / factor_billing_b
  Calculator: CadenaBCalculator.calcular_ingresos()
  Result Field: PyGMensual.ingreso_bruto_b
  Vision Output: Vision Tarifas (Cadena B section)
  API Field: VisionPyGV1.filas[1].valores[m]
  Example: margen_b=0.25, costo_b=500k
           → factor_b = 0.75
           → ingreso_b = 500k / 0.75 = 666.67k COP
  Status: Core | Version: V2-7 | New in V2-7: YES
```

```
FIELD: margen_c [NEW V2-7]
  Excel Source: Panel!D8
  Backend Model: PanelDeControl.margen_c
  Type: float | Range: 0.00–0.50
  Unit: ratio
  Validation: 0.0 <= margen_c <= 0.50
  Default: lookup from v2_7_defaults if None
  Formula: factor_billing_c = (1 - margen_c)
           ingreso_c = costo_c / factor_billing_c
  Calculator: CadenaCCalculator.calcular_ingresos()
  Result Field: PyGMensual.ingreso_bruto_c
  Vision Output: Vision Tarifas (Cadena C section)
  API Field: VisionPyGV1.filas[2].valores[m]
  Example: margen_c=0.15, costo_c=300k
           → factor_c = 0.85
           → ingreso_c = 300k / 0.85 = 352.94k COP
  Status: Core | Version: V2-7 | New in V2-7: YES
```

### 1.3 Contingencias & Ajustes

```
FIELD: op_cont
  Excel Source: Panel!C10
  Backend Model: PanelDeControl.op_cont
  Type: float | Range: 0.00–0.10
  Unit: ratio
  Validation: 0.0 <= op_cont <= 0.10
  Formula: contingencia_op = op_cont × ingreso_bruto
           (also affects margen inverse: factor_margen *= (1 - op_cont))
  Calculator: PyGCalculator.calcular_contingencias()
  Result Field: PyGMensual.contingencia_op
  Vision Output: Vision P&G I12
  API Field: VisionPyGV1.filas[3].valores[m]
  Example: op_cont=0.03, ingreso_bruto=1,288,659
           → contingencia_op = 0.03 × 1,288,659 = 38,659 COP
  Notes: Operational contingency buffer (3% typical)
  Status: Core | Version: V1.0
```

```
FIELD: com_cont
  Excel Source: Panel!C11
  Backend Model: PanelDeControl.com_cont
  Type: float | Range: 0.00–0.05
  Unit: ratio
  Validation: 0.0 <= com_cont <= 0.05
  Formula: contingencia_com = com_cont × ingreso_bruto
  Calculator: PyGCalculator.calcular_contingencias()
  Result Field: PyGMensual.contingencia_com
  Vision Output: Vision P&G I13
  API Field: VisionPyGV1.filas[4].valores[m]
  Example: com_cont=0.02, ingreso_bruto=1,288,659
           → contingencia_com = 0.02 × 1,288,659 = 25,773 COP
  Notes: Commercial contingency for discounts, SLAs
  Status: Core | Version: V1.0
```

```
FIELD: markup
  Excel Source: Panel!C12
  Backend Model: PanelDeControl.markup
  Type: float | Range: -1.00–10.00
  Unit: ratio
  Validation: markup >= -1.0
  Formula: markup_ingreso = markup × ingreso_bruto (if markup > 0)
  Calculator: PyGCalculator.calcular_markup()
  Result Field: PyGMensual.markup_ingreso
  Vision Output: Vision P&G I14
  API Field: VisionPyGV1.filas[5].valores[m]
  Example: markup=0.10, ingreso_bruto=1,288,659
           → markup_ingreso = 0.10 × 1,288,659 = 128,866 COP
  Notes: Additional surcharge (quality, complexity premium)
  Status: Core | Version: V1.0
```

```
FIELD: descuento
  Excel Source: Panel!C13
  Backend Model: PanelDeControl.descuento
  Type: float | Range: 0.00–1.00
  Unit: ratio
  Validation: 0.0 <= descuento <= 1.0
  Formula: descuento_ingreso = descuento × ingreso_bruto (subtracted from revenue)
  Calculator: PyGCalculator.calcular_descuentos()
  Result Field: PyGMensual.descuento_ingreso
  Vision Output: Vision P&G I15 (sign = "-")
  API Field: VisionPyGV1.filas[6].valores[m]
  Example: descuento=0.05, ingreso_bruto=1,288,659
           → descuento_ingreso = 0.05 × 1,288,659 = 64,433 COP (RESTADO)
  Notes: Volume discount, SLA penalty pass-through
  Status: Core | Version: V1.0
```

```
FIELD: imprevistos [NEW V2-5]
  Excel Source: Panel!C14
  Backend Model: PanelDeControl.imprevistos
  Type: float | Range: 0.00–0.20
  Unit: ratio
  Validation: 0.0 <= imprevistos <= 0.20
  Formula: imprevistos_ingreso = imprevistos × ingreso_bruto (subtracted)
  Calculator: PyGCalculator.calcular_imprevistos()
  Result Field: PyGMensual.imprevistos_ingreso
  Vision Output: Vision P&G I16
  API Field: VisionPyGV1.filas[7].valores[m]
  Example: imprevistos=0.05, ingreso_bruto=1,288,659
           → imprevistos = 0.05 × 1,288,659 = 64,433 COP (RESTADO)
  Notes: Contingency for unforeseen operational costs.
         NEW V2-5: Previously assumed 0.
  Status: Core | Version: V2-5 | New in V2-5: YES
```

### 1.4 Parámetros de Financiación

```
FIELD: periodo_pago_dias
  Excel Source: Panel!C17
  Backend Model: PanelDeControl.periodo_pago_dias
  Type: int | Range: 0–365
  Unit: days
  Validation: 0 <= periodo_pago_dias <= 365
  Formula: factor_periodo = periodo_pago_dias / 30
           financiacion = costo_anterior × tasa_mensual_financ × factor_periodo
  Calculator: CostosFinancierosCalculator.calcular_financiacion()
  Result Field: CostosFinancierosMes.financiacion → PyGMensual.financiacion
  Vision Output: Vision P&G F19
  API Field: VisionPyGV1.filas[24].valores[m]
  Example: periodo_pago_dias=90, tasa_mensual_financ=0.02, costo_anterior=1M
           → factor = 90/30 = 3
           → financiacion = 1M × 0.02 × 3 = 60,000 COP
  Notes: Client payment terms (90 days typical for corporates)
  Status: Core | Version: V1.0
```

```
FIELD: activa_financiacion
  Excel Source: Panel!C18
  Backend Model: PanelDeControl.activa_financiacion
  Type: bool
  Validation: true | false
  Formula: if not activa_financiacion: financiacion = 0
  Calculator: CostosFinancierosCalculator.calcular_financiacion()
  Result Field: CostosFinancierosMes.financiacion
  Vision Output: Vision P&G F19 (0 if false)
  API Field: VisionPyGV1.filas[24].valores[m]
  Example: activa_financiacion=false
           → financiacion = 0 COP (regardless of tasa/período)
  Notes: Toggle for whether client advance financing is available
  Status: Core | Version: V1.0
```

```
FIELD: tasa_mensual_financ
  Excel Source: Panel!C21
  Backend Model: PanelDeControl.tasa_mensual_financ
  Type: float | Range: 0.0001–0.1000
  Unit: ratio (monthly rate)
  Validation: 0.0 <= tasa_mensual_financ <= 0.10
  Default: lookup from parametrization if None
  Formula: financiacion = costo_anterior × tasa_mensual_financ × (periodo_pago_dias / 30)
  Calculator: CostosFinancierosCalculator.calcular_financiacion()
  Result Field: CostosFinancierosMes.financiacion
  Vision Output: Vision P&G F19
  API Field: VisionPyGV1.filas[24].valores[m]
  Example: tasa_mensual_financ=0.02 (2% per month), periodo_pago_dias=90
           → effective quarterly rate = 0.02 × 3 = 6%
  Notes: Monthly financing rate (2% typical, ~24% annualized)
  Status: Core | Version: V1.0
```

### 1.5 Tasas Fiscales

```
FIELD: tasa_ica
  Excel Source: Panel!C19 (override), or lookup by city
  Backend Model: PanelDeControl.tasa_ica
  Type: float | Range: 0.0001–0.0100
  Unit: ratio (annual rate)
  Validation: 0.0001 <= tasa_ica <= 0.01
  Default: lookup by ciudad if None (ParametrizationProvider.get_tasa_ica(ciudad))
  Formula: base_ica = (costo_a + costo_b + costo_c_fin + poliza + financiacion) / factor_margen
           ica = base_ica × tasa_ica
  Calculator: CostosFinancierosCalculator.calcular_ica()
  Result Field: CostosFinancierosMes.ica (+ ica_a, ica_c for cadena attribution)
  Vision Output: Vision P&G F17
  API Field: VisionPyGV1.filas[21].valores[m]
  Example: tasa_ica=0.0033 (0.33%), base_ica=1.5M
           → ica = 1.5M × 0.0033 = 4,950 COP
  Cadena Attribution (V2-5+):
    - ica_a: atribuible a Cadena A (base = costo_a / factor_margen)
    - ica_c: atribuible a Cadena C (base = costo_c_fin / factor_margen)
  Notes: Industry tax; Ciudad-specific (Bogotá=0.33%, Medellín=0.32%, etc.)
         Uses gross-up (divide by factor_margen) due to tax-on-revenue structure
  Status: Core | Version: V1.0 | Updated V2-5: Added cadena attribution
```

```
FIELD: tasa_gmf
  Excel Source: Panel!C20 (override), or parametrization
  Backend Model: PanelDeControl.tasa_gmf
  Type: float | Range: 0.0001–0.0050
  Unit: ratio (annual rate)
  Validation: 0.0001 <= tasa_gmf <= 0.005
  Default: lookup from parametrization if None
  Formula: gmf = (costo_a + costo_b + costo_c_fin + poliza + financiacion) × tasa_gmf
  Calculator: CostosFinancierosCalculator.calcular_gmf()
  Result Field: CostosFinancierosMes.gmf (+ gmf_a, gmf_c for cadena attribution)
  Vision Output: Vision P&G F18
  API Field: VisionPyGV1.filas[22].valores[m]
  Example: tasa_gmf=0.004 (0.4%), base_gmf=1.5M
           → gmf = 1.5M × 0.004 = 6,000 COP
  Notes: Financial transaction tax (~0.4% typical, varies by period)
         No gross-up (tax on cost, not revenue)
  Status: Core | Version: V1.0
```

### 1.6 Parámetros Operativos

```
FIELD: pct_rotacion
  Excel Source: Panel!C16 (override), or lookup by línea_negocio
  Backend Model: PanelDeControl.pct_rotacion
  Type: float | Range: 0.00–1.00
  Unit: ratio (monthly turnover)
  Validation: 0.0 <= pct_rotacion <= 1.0
  Default: lookup from parametrization if None (e.g., "Cobranzas" = 0.15)
  Formula: capacitacion_rotacion = dias_cap × tarifa_dia × (fte × pct_rotacion) × factor_indexacion
           fte_examenes_rotacion = fte_examenes × pct_rotacion
  Calculator: NominaCalculator.capacitacion_rotacion(), examenes()
  Result Field: ResultadoNomina.capacitacion_rotacion, examenes
  Vision Output: Vision P&G I37 (Capacitación Rotación)
  API Field: VisionPyGV1.filas[10].valores[m]
  Example: pct_rotacion=0.15 (15% monthly), fte=100, dias_cap=3, tarifa=50k
           → capacitacion_rot = 3 × 50k × (100 × 0.15) = 225,000 COP/mes
  Notes: Turnover affects both training and exam costs
  Status: Core | Version: V1.0
```

```
FIELD: pct_ausentismo
  Excel Source: Panel (advanced), or lookup by línea_negocio
  Backend Model: PanelDeControl.pct_ausentismo
  Type: float | Range: 0.00–0.50
  Unit: ratio (monthly absence)
  Validation: 0.0 <= pct_ausentismo <= 0.50
  Default: lookup from parametrization if None (e.g., "Cobranzas" = 0.05)
  Formula: (currently not used in V2-7 core calculations; reserved for future)
  Calculator: (none; reserved)
  Result Field: (none; reserved)
  Vision Output: (none; reserved)
  API Field: (none; reserved)
  Notes: Future use for absenteeism-based FTE adjustments
  Status: Reserved | Version: V2-7
```

---

## 2. COMPONENTES DE NÓMINA

```
FIELD: salario_fijo (ResultadoNomina)
  Excel Source: HR Parámetros (salario_base) × Panel (pct_aumento) × factor_indexacion
  Backend Model: ResultadoNomina.salario_fijo
  Type: float (COP)
  Unit: monthly cost
  Formula: salario_fijo = salario_base × fte × factor_indexacion(mes)
           where factor_indexacion = factor_base_año × (1 + pct_aumento)^(años_transcurridos)
  Calculator: NominaCalculator.salario_fijo()
  Source Fields: ParametrosNomina.salario_base, PerfPerfilCadenaA.fte, pct_aumento_salarial
  Vision Output: Vision P&G I34
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: salario_base=2M, fte=50, factor_indexacion[mes12]=1.08
           → salario_fijo = 2M × 50 × 1.08 = 108M COP
  Dependency Chain: Panel(pct_aumento) → ParametrosNomina → NominaCalculator → ResultadoNomina
  Status: Core | Version: V1.0
```

```
FIELD: capacitacion_inicial (ResultadoNomina)
  Excel Source: HR Parámetros (days × tarifa)
  Backend Model: ResultadoNomina.capacitacion_inicial
  Type: float (COP)
  Unit: monthly amortized cost
  Formula: capacitacion_inicial = (dias_cap_inicial × tarifa_dia_cap × fte / meses_contrato) × factor_indexacion
  Calculator: NominaCalculator.capacitacion_inicial()
  Source Fields: ParametrosNomina.dias_cap_inicial, tarifa_diaria_capacitacion, PerfPerfilCadenaA.fte, Panel.meses_contrato
  Vision Output: Vision P&G I36
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: dias=10, tarifa=80k, fte=50, meses=24
           → capacitacion_inicial = (10 × 80k × 50 / 24) × 1.08 = 180,000 COP/mes
  Notes: Amortized over contract life (one-time setup cost spread)
  Status: Core | Version: V1.0
```

```
FIELD: capacitacion_rotacion (ResultadoNomina)
  Excel Source: HR Parámetros (days × tarifa) × Panel!C16 (pct_rotacion)
  Backend Model: ResultadoNomina.capacitacion_rotacion
  Type: float (COP)
  Unit: monthly cost
  Formula: capacitacion_rotacion = dias_cap_rotacion × tarifa_dia_cap × (fte × pct_rotacion) × factor_indexacion
  Calculator: NominaCalculator.capacitacion_rotacion()
  Source Fields: ParametrosNomina.dias_cap_rotacion, tarifa_diaria_capacitacion, PerfPerfilCadenaA.fte, 
                 Panel.pct_rotacion, factor_indexacion
  Vision Output: Vision P&G I37
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: dias=3, tarifa=50k, fte=50, pct_rot=0.15
           → capacitacion_rotacion = 3 × 50k × (50 × 0.15) × 1.08 = 121,500 COP/mes
  Notes: Recurring monthly cost for new hires due to turnover
  Status: Core | Version: V1.0
```

```
FIELD: examenes (ResultadoNomina)
  Excel Source: HR Parámetros (costo_examen) × 3-part formula
  Backend Model: ResultadoNomina.examenes
  Type: float (COP)
  Unit: monthly cost
  Formula: examenes = costo_examen × fte_examenes × (1/meses_contrato + pct_rotacion + pct_examen_anual/12) × factor_indexacion
           where fte_examenes = fte × (1 + supervisor_ratio + formador_ratio + monitor_ratio)
  Calculator: NominaCalculator.examenes()
  Source Fields: ParametrosNomina.costo_examen, ParametrosCalculo.fte_examenes, pct_rotacion, 
                 pct_examen_anual, special_roles_calculator output
  Vision Output: Vision P&G I38
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  3-Part Breakdown:
    1. Initial exams (ingreso inicial): fte_examenes / meses_contrato
    2. Rotation exams (rotación mensual): fte_examenes × pct_rotacion
    3. Annual exams (periódico): fte_examenes × pct_examen_anual / 12
  Example: costo=150k, fte=50, ratio_sum=1.5 → fte_eff=125, meses=24, 
           pct_rot=0.15, pct_anual=0.20
           → examenes = 150k × 125 × (1/24 + 0.15 + 0.20/12) = 3,125,000 COP/mes
  Status: Core | Version: V1.0
```

```
FIELD: seguridad (ResultadoNomina)
  Excel Source: HR Parámetros (costo_estudio)
  Backend Model: ResultadoNomina.seguridad
  Type: float (COP)
  Unit: monthly cost
  Formula: seguridad = costo_estudio_seg × fte × factor_indexacion
  Calculator: NominaCalculator.seguridad()
  Source Fields: ParametrosNomina.costo_estudio_seg, PerfPerfilCadenaA.fte
  Vision Output: Vision P&G I39 (Estudios de Seguridad)
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: costo=20k, fte=50
           → seguridad = 20k × 50 = 1,000,000 COP/mes
  Notes: Security studies (background checks, criminal record verification)
  Status: Core | Version: V1.0
```

```
FIELD: crucero (ResultadoNomina) [NEW V2-7]
  Excel Source: Panel!C17 (tarifa_crucero)
  Backend Model: ResultadoNomina.crucero
  Type: float (COP)
  Unit: monthly cost
  Formula: crucero = tarifa_crucero × fte × factor_indexacion
  Calculator: NominaCalculator.crucero()
  Source Fields: Panel.tarifa_crucero, PerfPerfilCadenaA.fte
  Vision Output: Vision P&G I40
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: tarifa_crucero=100k, fte=50
           → crucero = 100k × 50 = 5,000,000 COP/mes
  Notes: Team-building / training travel for Cadena A agents
         NEW V2-7: Previously not included
  Status: Core | Version: V2-7 | New in V2-7: YES
```

---

## 3. COMPONENTES DE INFRAESTRUCTURA (No-Payroll)

```
FIELD: opex_ti (ResultadoNoPayroll)
  Excel Source: No Payroll sheet (OPEX TI per station)
  Backend Model: ResultadoNoPayroll.opex_ti
  Type: float (COP)
  Unit: monthly cost
  Formula: opex_ti = sum(opex_items) per perfil × rampup_factor
  Calculator: NoPayrollCalculator.calcular_opex_ti()
  Source Fields: CondicionesCadenaAInput.opex_fijo, location-based OPEX (seat, phone, license)
  Vision Output: Vision P&G I42 (OPEX Fijo)
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: 50 agentes × 2k OPEX/agente = 100k/mes
  Notes: IT operations, telecom, software licenses, seat costs
  Status: Core | Version: V1.0
```

```
FIELD: capex (ResultadoNoPayroll)
  Excel Source: Inversiones sheet (capex per item × meses_amortizacion)
  Backend Model: ResultadoNoPayroll.capex
  Type: float (COP)
  Unit: monthly amortized cost
  Formula: capex = sum(costo_item / meses_amortizacion) per perfil
  Calculator: NoPayrollCalculator.calcular_capex()
  Source Fields: CondicionesCadenaAInput.inversiones, meses_amortizacion per item
  Vision Output: Vision P&G I43 (Inversiones)
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: computers=10 × 3M = 30M amortized over 24 months
           → capex = 30M / 24 = 1.25M/mes
  Notes: Depreciation of equipment, furniture, infrastructure
  Status: Core | Version: V1.0
```

```
FIELD: costos_fijos (ResultadoNoPayroll)
  Excel Source: (Reserved; currently unused in V2-7)
  Backend Model: ResultadoNoPayroll.costos_fijos
  Type: float (COP)
  Unit: monthly cost
  Formula: costos_fijos = 0 (reserved for future)
  Calculator: NoPayrollCalculator.calcular_costos_fijos()
  Source Fields: (none)
  Vision Output: (none; line present but always 0)
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Notes: Future extension point for real estate, utilities, etc.
  Status: Reserved | Version: V2-7
```

---

## 4. CADENA B COMPONENTES

```
FIELD: opex_fijo_b (ResultadoCadenaB)
  Excel Source: Condiciones Cadena B → Canales (opex_fijo per channel)
  Backend Model: ResultadoCadenaB.opex_fijo
  Type: float (COP)
  Unit: monthly cost
  Formula: opex_fijo_b = sum(channel.opex_fijo) for active channels
  Calculator: CadenaBCalculator.calcular_opex_fijo()
  Source Fields: CondicionesCadenaBInput.canales[].opex_fijo
  Vision Output: Vision P&G B56
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: WhatsApp opex=100k, Token IA opex=50k
           → opex_fijo_b = 150k/mes
  Status: Core | Version: V1.0
```

```
FIELD: costo_variable_b (ResultadoCadenaB)
  Excel Source: Condiciones Cadena B → Canales (tarifa_unitaria × volume)
  Backend Model: ResultadoCadenaB.costo_variable
  Type: float (COP)
  Unit: monthly cost
  Formula: costo_variable_b = sum(channel.tarifa_unitaria × channel.volumen_mensual) + sum(consumo_variable_items)
  Calculator: CadenaBCalculator.calcular_costo_variable()
  Source Fields: CondicionesCadenaBInput.canales[].tarifa_unitaria, volumen_mensual, 
                 opex_consumo_variable[]
  Vision Output: (implicit in total)
  API Field: VisionPyGV1 (implicit)
  Example: WhatsApp: 500 units × 200 = 100k, Token IA: 1000 × 150 = 150k
           → costo_variable_b = 250k/mes
  Notes: Variable cost per transaction or per minute
  Status: Core | Version: V1.0
```

```
FIELD: soporte_mantenimiento_b (ResultadoCadenaB)
  Excel Source: Condiciones Cadena B → Equipo S&M (salario × pct_dedicacion)
  Backend Model: ResultadoCadenaB.soporte_mantenimiento
  Type: float (COP)
  Unit: monthly cost
  Formula: soporte_mantenimiento_b = sum(salario_cargado_rol × pct_dedicacion × fte_equipo_sm)
           for each S&M team member
  Calculator: CadenaBCalculator.calcular_soporte_mantenimiento()
  Source Fields: CondicionesCadenaBInput.equipo_sm[], ParametrizationProvider.salarios por rol
  Vision Output: Vision P&G B60
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: 2 engineers @ 4M cargado × 0.5 dedicación = 4M/mes
  Notes: Staff dedicated to platform operations
  Status: Core | Version: V1.0
```

```
FIELD: escalamiento_b (ResultadoCadenaB)
  Excel Source: Condiciones Cadena B → Canales (pct_escalamiento × costo_base)
  Backend Model: ResultadoCadenaB.escalamiento
  Type: float (COP)
  Unit: monthly cost
  Formula: escalamiento_b = sum(channel.pct_escalamiento × channel.costo_base)
  Calculator: CadenaBCalculator.calcular_escalamiento()
  Source Fields: CondicionesCadenaBInput.canales[].pct_escalamiento, costo_base
  Vision Output: Vision P&G B61
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: platform upgrade @ 10% of costo_b = 10% × 500k = 50k/mes
  Status: Core | Version: V1.0
```

```
FIELD: inversiones_b (ResultadoCadenaB)
  Excel Source: Condiciones Cadena B → Inversiones (costo × meses_amortizacion)
  Backend Model: ResultadoCadenaB.inversiones
  Type: float (COP)
  Unit: monthly amortized cost
  Formula: inversiones_b = sum(costo_item / meses_amortizacion)
  Calculator: CadenaBCalculator.calcular_inversiones()
  Source Fields: CondicionesCadenaBInput (devices, platform setup, etc.)
  Vision Output: Vision P&G B59
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: platform setup 2M over 12 months = 166.67k/mes
  Status: Core | Version: V1.0
```

```
FIELD: hitl_b (ResultadoCadenaB)
  Excel Source: (Reserved; HITL team costs)
  Backend Model: ResultadoCadenaB.hitl
  Type: float (COP)
  Unit: monthly cost
  Formula: hitl_b = sum(salario_cargado_rol × pct_dedicacion) for HITL team
  Calculator: CadenaBCalculator.calcular_hitl()
  Source Fields: (future; currently 0)
  Vision Output: (not shown in current P&G)
  API Field: (not exposed)
  Notes: Human-in-the-loop oversight; future use
  Status: Reserved | Version: V2-7
```

---

## 5. CADENA C COMPONENTES

```
FIELD: tarifa_proveedor (ResultadoCadenaC)
  Excel Source: Condiciones Cadena C → Tarifa Proveedor Mensual
  Backend Model: ResultadoCadenaC.tarifa_proveedor
  Type: float (COP)
  Unit: monthly cost
  Formula: tarifa_proveedor = direct input (outsourcing fee)
  Calculator: CadenaCCalculator.calcular_tarifa_proveedor()
  Source Fields: CondicionesCadenaC.tarifa_proveedor_mensual
  Vision Output: Vision P&G C59
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: BPO partner @ 1.5M/mes
  Status: Core | Version: V1.0
```

```
FIELD: opex_fijo_integ (ResultadoCadenaC)
  Excel Source: Condiciones Cadena C → OPEX Fijo Integración
  Backend Model: ResultadoCadenaC.opex_fijo_integ
  Type: float (COP)
  Unit: monthly cost
  Formula: opex_fijo_integ = direct input
  Calculator: CadenaCCalculator.calcular_opex_fijo()
  Source Fields: CondicionesCadenaC.opex_fijo_integracion
  Vision Output: (implicit in total)
  API Field: VisionPyGV1 (implicit)
  Example: Integration platform OPEX = 200k/mes
  Status: Core | Version: V1.0
```

```
FIELD: opex_var_integ (ResultadoCadenaC)
  Excel Source: Condiciones Cadena C → OPEX Variable
  Backend Model: ResultadoCadenaC.opex_var_integ
  Type: float (COP)
  Unit: monthly cost
  Formula: opex_var_integ = direct input or volume-based
  Calculator: CadenaCCalculator.calcular_opex_variable()
  Source Fields: CondicionesCadenaC.opex_variable_integ
  Vision Output: NOT in P&G (flows to financial base only)
  API Field: (not exposed; internal)
  Notes: Variable integration costs; included in financial calculations but not P&G
  Status: Core | Version: V1.0
```

```
FIELD: inversiones_c (ResultadoCadenaC)
  Excel Source: Condiciones Cadena C → Inversiones
  Backend Model: ResultadoCadenaC.inversiones
  Type: float (COP)
  Unit: monthly amortized cost
  Formula: inversiones_c = sum(costo_item / meses_amortizacion)
  Calculator: CadenaCCalculator.calcular_inversiones()
  Source Fields: CondicionesCadenaC.inversiones
  Vision Output: (implicit in total)
  API Field: VisionPyGV1 (implicit)
  Example: Integration infrastructure 6M over 24 months = 250k/mes
  Status: Core | Version: V1.0
```

```
FIELD: escalamiento_c (ResultadoCadenaC)
  Excel Source: Condiciones Cadena C → Escalamiento
  Backend Model: ResultadoCadenaC.escalamiento
  Type: float (COP)
  Unit: monthly cost
  Formula: escalamiento_c = direct input or % of tarifa_proveedor
  Calculator: CadenaCCalculator.calcular_escalamiento()
  Source Fields: CondicionesCadenaC.escalamiento
  Vision Output: Vision P&G C62
  API Field: VisionPyGV1.filas_detalle[*].valores[m]
  Example: Provider price increase 5% = 75k/mes
  Status: Core | Version: V1.0
```

```
FIELD: equipo_integ (ResultadoCadenaC)
  Excel Source: (Reserved; integration team)
  Backend Model: ResultadoCadenaC.equipo_integ
  Type: float (COP)
  Unit: monthly cost
  Formula: equipo_integ = sum(salario_cargado × pct_dedicacion)
  Calculator: CadenaCCalculator.calcular_equipo_integ()
  Source Fields: (future)
  Vision Output: NOT in P&G
  API Field: (not exposed)
  Notes: Integration team salaries; future use
  Status: Reserved | Version: V2-7
```

```
FIELD: hitl_c (ResultadoCadenaC)
  Excel Source: (Reserved; HITL for Cadena C)
  Backend Model: ResultadoCadenaC.hitl
  Type: float (COP)
  Unit: monthly cost
  Formula: hitl_c = sum(salario_cargado × pct_dedicacion)
  Calculator: CadenaCCalculator.calcular_hitl()
  Source Fields: (future)
  Vision Output: NOT in P&G
  API Field: (not exposed)
  Status: Reserved | Version: V2-7
```

---

## 6. COMPONENTES FINANCIEROS

```
FIELD: ica (CostosFinancierosMes)
  Excel Source: Panel!C19 (tasa_ica) + Costo Total
  Backend Model: CostosFinancierosMes.ica, PyGMensual.ica
  Type: float (COP)
  Unit: monthly tax
  Formula: base_ica = (costo_a + costo_b + costo_c_fin + poliza_total + financiacion) / factor_margen
           ica = base_ica × tasa_ica
  Calculator: CostosFinancierosCalculator.calcular_ica()
  Gross-Up: YES (divide by factor_margen)
  Cadena Attribution: ica_a, ica_c (by cost proportion)
  Vision Output: Vision P&G F17
  API Field: VisionPyGV1.filas[21].valores[m]
  Example: base=1.5M, tasa_ica=0.0033
           → ica = 1.5M × 0.0033 = 4,950 COP
  Status: Core | Version: V1.0
```

```
FIELD: gmf (CostosFinancierosMes)
  Excel Source: Panel!C20 (tasa_gmf) + Costo Total
  Backend Model: CostosFinancierosMes.gmf, PyGMensual.gmf
  Type: float (COP)
  Unit: monthly tax
  Formula: gmf = (costo_a + costo_b + costo_c_fin + poliza_total + financiacion) × tasa_gmf
  Calculator: CostosFinancierosCalculator.calcular_gmf()
  Gross-Up: NO (applied directly to cost)
  Cadena Attribution: gmf_a, gmf_c (by cost proportion)
  Vision Output: Vision P&G F18
  API Field: VisionPyGV1.filas[22].valores[m]
  Example: base=1.5M, tasa_gmf=0.004
           → gmf = 1.5M × 0.004 = 6,000 COP
  Status: Core | Version: V1.0
```

```
FIELD: polizas (CostosFinancierosMes)
  Excel Source: Pólizas sheet (by mes and deal config)
  Backend Model: CostosFinancierosMes.polizas (+ polizas_a, polizas_b, polizas_c)
  Type: float (COP)
  Unit: monthly premium
  Formula: poliza_total = (costo_a + costo_b + costo_c_fin + financiacion) × tasa_poliza × pct_atribuible
           (summed across all active pólizas)
  Calculator: CostosFinancierosCalculator.calcular_polizas()
  Cadena Attribution: by pct_atribuible per poliza
  Vision Output: Vision P&G F19
  API Field: VisionPyGV1.filas[23].valores[m]
  Example: 2 polizas: RC @ 0.5% × 20% = 1.5k, Incumpl @ 0.3% × 100% = 4.5k
           → polizas = 6k/mes (on 1.5M base)
  Vision Tarifas: per_canal=true → included in TarifaCanal
  Notes: User can override with entry_data.polizas[]
  Status: Core | Version: V1.0 | Updated V2-5: Added per_canal filtering
```

```
FIELD: financiacion (CostosFinancierosMes)
  Excel Source: Panel!C21 (tasa), Panel!C17 (período), Panel!C18 (activación)
  Backend Model: CostosFinancierosMes.financiacion, PyGMensual.financiacion
  Type: float (COP)
  Unit: monthly financing cost
  Formula: if not panel.activa_financiacion: financiacion = 0
           else: financiacion = costo_anterior × tasa_mensual_financ × (periodo_pago_dias / 30)
  Calculator: CostosFinancierosCalculator.calcular_financiacion()
  Costo Anterior: from previous month (mes - 1)
  Vision Output: Vision P&G F20
  API Field: VisionPyGV1.filas[24].valores[m]
  Example: costo_anterior=1M, tasa=0.02, periodo=90
           → financiacion = 1M × 0.02 × 3 = 60,000 COP
  Notes: Financing on payment terms (client pays in 90 days; TC advances capital)
  Status: Core | Version: V1.0
```

```
FIELD: comision_administracion (CostosFinancierosMes) [NEW V2-5]
  Excel Source: Panel!G45 (tasa) × Pólizas
  Backend Model: CostosFinancierosMes.comision_administracion, PyGMensual.comision_administracion
  Type: float (COP)
  Unit: monthly commission
  Formula: comision_administracion = poliza_total × 1.42
           (administrative markup on insurance)
  Calculator: CostosFinancierosCalculator.calcular_comision_administracion()
  Cadena Attribution: comision_admin_cadena_a (for Vision Tarifas)
  Vision Output: Vision P&G F21
  API Field: VisionPyGV1.filas[25].valores[m]
  Example: polizas=6k
           → comision_admin = 6k × 1.42 = 8.52k
  Notes: NEW V2-5: Administrative fee on insurance premiums
  Status: Core | Version: V2-5 | New in V2-5: YES
```

---

## 7. AGREGACIONES P&G

```
FIELD: ingreso_neto (PyGMensual property)
  Excel Source: Vision P&G!A47
  Backend Model: PyGMensual.ingreso_neto (property)
  Type: float (COP)
  Unit: monthly revenue
  Formula: ingreso_neto = ingreso_bruto_a + ingreso_bruto_b + ingreso_bruto_c
                         + contingencia_op + contingencia_com
                         + markup_ingreso - descuento_ingreso - imprevistos_ingreso
  Calculator: PyGMensual (property aggregation)
  Vision Output: Vision P&G A48
  API Field: VisionPyGV1.filas[7].valores[m]
  Example: See P&G flujo completo above
  Status: Core | Version: V1.0
```

```
FIELD: costo_operativo (PyGMensual property)
  Excel Source: Vision P&G!B60
  Backend Model: PyGMensual.costo_operativo (property)
  Type: float (COP)
  Unit: monthly cost
  Formula: costo_operativo = payroll_a + no_payroll_a + costo_b + costo_c
  Calculator: PyGMensual (property aggregation)
  Vision Output: Vision P&G B61
  API Field: VisionPyGV1.filas[20].valores[m]
  Status: Core | Version: V1.0
```

```
FIELD: costos_financieros (PyGMensual property)
  Excel Source: Vision P&G!C66
  Backend Model: PyGMensual.costos_financieros (property)
  Type: float (COP)
  Unit: monthly cost
  Formula: costos_financieros = ica + gmf + polizas + financiacion + comision_administracion
  Calculator: PyGMensual (property aggregation)
  Vision Output: Vision P&G C67
  API Field: VisionPyGV1.filas[26].valores[m]
  Status: Core | Version: V1.0
```

```
FIELD: contribucion (PyGMensual property)
  Excel Source: Vision P&G!D67
  Backend Model: PyGMensual.contribucion (property)
  Type: float (COP)
  Unit: monthly contribution (before financials)
  Formula: contribucion = ingreso_neto - costo_operativo
  Calculator: PyGMensual (property aggregation)
  Vision Output: Vision P&G D68
  API Field: VisionPyGV1.filas[27].valores[m]
  Status: Core | Version: V1.0
```

```
FIELD: utilidad_neta (PyGMensual property)
  Excel Source: Vision P&G!D69
  Backend Model: PyGMensual.utilidad_neta (property)
  Type: float (COP)
  Unit: monthly net profit
  Formula: utilidad_neta = ingreso_neto - costo_operativo - costos_financieros
  Calculator: PyGMensual (property aggregation)
  Vision Output: Vision P&G D70
  API Field: VisionPyGV1.filas[28].valores[m]
  Example: ingreso=1,500,000 - costo_op=1,000,000 - costo_fin=50,000
           → utilidad = 450,000 COP
  Status: Core | Version: V1.0
```

```
FIELD: pct_utilidad_neta (PyGMensual property)
  Excel Source: Vision P&G!D71
  Backend Model: PyGMensual.pct_utilidad_neta (property)
  Type: float (ratio)
  Unit: percentage (0.0–1.0)
  Formula: pct_utilidad_neta = utilidad_neta / ingreso_neto if ingreso_neto > 0 else 0.0
  Calculator: PyGMensual (property aggregation)
  Vision Output: Vision P&G D71
  API Field: VisionPyGV1.filas[29].valores[m]
  Example: utilidad=450,000, ingreso=1,500,000
           → pct = 450k / 1.5M = 0.30 (30%)
  Status: Core | Version: V1.0
```

---

## 8. VISION TARIFAS DENOMINADORES (CTS)

```
FIELD: K50 (fte_denominator_cadena_a)
  Excel Source: Vision Tarifas!K50
  Backend Model: CostToServeCalculator.k50_fte
  Type: float
  Unit: FTE or transactions/month
  Formula: if es_inbound: K50 = J_inbound × N_inbound (transactions)
           else:        K50 = fte_total_cadena_a (outbound convention)
  Calculator: CostToServeCalculator.calcular_denominadores()
  Vision Output: Vision Tarifas K50
  API Field: VisionTarifasV1.ctus_denominadores.k50
  Example Inbound: J=500 calls/day, N=1000 calls/agent
           → K50 = 500 × 1000 = 500,000 transacciones/mes
  Example Outbound: FTE=100
           → K50 = 100 FTE
  Notes: Critical for tarifa_fijo_fte and tarifa_variable_transaccion
  Status: Core | Version: V1.0
```

```
FIELD: L50 (volumen_denominator_cadena_b)
  Excel Source: Vision Tarifas!L50
  Backend Model: CostToServeCalculator.l50_volumen
  Type: float
  Unit: transactions/month or count
  Formula: L50 = sum(canal.volumen_mensual) for all Cadena B channels
  Calculator: CostToServeCalculator.calcular_denominadores()
  Vision Output: Vision Tarifas L50
  API Field: VisionTarifasV1.ctus_denominadores.l50
  Example: WhatsApp=10k, Token IA=5k
           → L50 = 15k/mes
  Status: Core | Version: V1.0
```

```
FIELD: M50 (volumen_denominator_cadena_c)
  Excel Source: Vision Tarifas!M50
  Backend Model: CostToServeCalculator.m50_volumen
  Type: float
  Unit: transactions/month or count
  Formula: M50 = canal_c.volumen_mensual (from CondicionesCadenaC)
  Calculator: CostToServeCalculator.calcular_denominadores()
  Vision Output: Vision Tarifas M50
  API Field: VisionTarifasV1.ctus_denominadores.m50
  Example: BPO partner handles 50k/mes
           → M50 = 50k/mes
  Status: Core | Version: V1.0
```

---

## 9. KPIs DEL DEAL

```
FIELD: ingreso_mensual (KPIsDeal)
  Excel Source: (aggregation)
  Backend Model: KPIsDeal.ingreso_mensual
  Type: float (COP)
  Unit: monthly average revenue
  Formula: ingreso_mensual = sum(pyg.ingreso_neto) / active_months
  Calculator: KPIsCalculator.calcular_kpis()
  Vision Output: Resumen Ejecutivo
  API Field: KpisV1.ingreso_mensual
  Example: Total revenue 36M over 12 months
           → ingreso_mensual = 36M / 12 = 3M/mes
  Status: Core | Version: V1.0
```

```
FIELD: costo_mensual_promedio (KPIsDeal)
  Excel Source: (aggregation)
  Backend Model: KPIsDeal.costo_mensual_promedio
  Type: float (COP)
  Unit: monthly average cost
  Formula: costo_mensual_promedio = sum(pyg.costo_operativo) / active_months
  Calculator: KPIsCalculator.calcular_kpis()
  Vision Output: Resumen Ejecutivo
  API Field: KpisV1.costo_mensual_promedio
  Status: Core | Version: V1.0
```

```
FIELD: costo_total_contrato (KPIsDeal)
  Excel Source: (aggregation)
  Backend Model: KPIsDeal.costo_total_contrato
  Type: float (COP)
  Unit: total contract cost
  Formula: costo_total_contrato = sum(pyg.costo_operativo) + sum(pyg.costos_financieros)
  Calculator: KPIsCalculator.calcular_kpis()
  Vision Output: Resumen Ejecutivo
  API Field: KpisV1.costo_total_contrato
  Status: Core | Version: V1.0
```

```
FIELD: utilidad_neta_total (KPIsDeal)
  Excel Source: (aggregation)
  Backend Model: KPIsDeal.utilidad_neta_total
  Type: float (COP)
  Unit: total contract profit
  Formula: utilidad_neta_total = sum(pyg.utilidad_neta)
  Calculator: KPIsCalculator.calcular_kpis()
  Vision Output: Resumen Ejecutivo
  API Field: KpisV1.utilidad_neta_total
  Example: Total profit 4M over 12 months
  Status: Core | Version: V1.0
```

```
FIELD: pct_utilidad_neta_total (KPIsDeal)
  Excel Source: (aggregation)
  Backend Model: KPIsDeal.pct_utilidad_neta_total
  Type: float (ratio)
  Unit: percentage (0.0–1.0)
  Formula: pct_utilidad_neta_total = utilidad_neta_total / ingreso_bruto_total
  Calculator: KPIsCalculator.calcular_kpis()
  Vision Output: Resumen Ejecutivo
  API Field: KpisV1.pct_utilidad_neta_total
  Example: 4M profit / 36M revenue = 0.111 (11.1%)
  Status: Core | Version: V1.0
```

---

## 10. REGLAS DE VALIDACIÓN (Criteria)

```
CRITERION: margen_minimo
  Description: Deal margin must exceed operational minimum
  Rule: pct_utilidad_neta >= margen_minimo_requerido
  Margen Requerido: lookup by línea_negocio
    - Cobranzas: 8%
    - SAC: 12%
    - Back Office: 10%
  Result: KPIsDeal.cumple_margen_minimo
  Severity: WARNING (non-blocking but flagged)
  Notes: Used in risk assessment, deal filtering
```

```
CRITERION: viabilidad_financiera
  Description: Deal must have positive cash flow in month 1
  Rule: ingreso_neto_mes_1 > costo_operativo_mes_1
  Result: (boolean)
  Severity: ERROR (blocking)
  Notes: Prevents deals with negative contribution
```

```
CRITERION: rampup_aplicable
  Description: FTE ramp-up factor for gradual staffing
  Rule: mes <= rampup_mes_completo → rampup_factor = mes / rampup_mes_completo
  Result: (applied to all FTE-based costs)
  Default: 1.0 (no rampup; full staff from mes 1)
  Notes: Decreases payroll during staffing phase (e.g., weeks 0-4)
```

---

## 11. MAPPING NOTES (Non-Exhaustive Reference)

### Excel → Backend → API Reference

| Excel Sheet | Excel Cell | Backend Model | Backend Field | Calculator | API Response | Notes |
|---|---|---|---|---|---|---|
| Panel | C9 | PanelDeControl | margen | PyGCalculator | VisionPyGV1.filas[0] | Core margin |
| Panel | C16 | PanelDeControl | pct_rotacion | NominaCalculator | VisionPyGV1.filas[10] | Rotation % |
| Nomina Loaded | B | ResultadoNomina | salario_fijo | NominaCalculator | VisionPyGV1.filas[8] | Fixed salary |
| Condiciones Cadena A | D | PerfilCadenaA | comision_pct | NominaCalculator | (implicit) | Commissions |
| Condiciones Cadena B | (various) | CondicionesCadenaBInput | canales | CadenaBCalculator | VisionPyGV1.filas[18] | Cadena B total |
| Condiciones Cadena C | (various) | CondicionesCadenaC | * | CadenaCCalculator | VisionPyGV1.filas[19] | Cadena C total |

---

**Document Status**: PRODUCTION | Updated: 2026-05-31 | Format: Machine-Readable Reference

**Use Cases**:
- Test automation: grep FIELD to find test cases
- Audit trails: trace Excel cell → API field
- Formula verification: check Calculator.method()
- Data mapping: understand backend ↔ frontend contracts
