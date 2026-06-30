# BUSINESS_RULES: Catálogo Completo de Reglas Funcionales

**Versión**: V2-7 (engine-v2 refactor)  
**Fecha**: 2026-05-31  
**Clasificación**: Referencia para Analistas de Negocio

---

## Convenciones

- **Categoría**: Staffing | Channels | Pricing | Risk | Payroll | Financial | FTE | Cadena C
- **Condición**: Cuándo se aplica la regla (siempre, condicional, opcional)
- **Implementación**: Ubicación exacta en código
- **Escenario**: Caso de uso real que ilustra la regla

---

# STAFFING & ROLES

## BR-001: HR-Ratios Override Special Roles

**Categoría**: Staffing

**Descripción**: Los ratios de staffing determinan automáticamente cuánto personal de soporte se requiere por cada tipo de rol.

**Condición**: Se aplica siempre que haya agentes base en Cadena A.

**Impacto**:
- Si `FTE_agentes = 10` y `ratio_supervisor = 10`, entonces `FTE_supervisor = 1`
- Si no hay agentes, no hay soporte (FTE_support = 0)

**Fórmula**:
```
FTE_soporte_tipo = FTE_agentes / ratio_tipo
```

**Implementación**:
- Archivo: `input/context_builder.py`
- Método: `_construir_perfiles_a()`

**Escenario**:
- Input: 20 agentes, ratio_supervisor=10, ratio_trainer=15
- Output: 2 supervisores, 1.33 capacitadores

---

## BR-002: Support Staff No FTE Billable

**Categoría**: Staffing

**Descripción**: Personal de soporte (`es_soporte=True`) no ocupa FTE de Cadena A y no se factura directamente por posición.

**Condición**: Siempre que `es_soporte=True`.

**Impacto**:
- Supervisores, capacitadores, validadores: no incluyen en K50 (denominador FTE)
- Sus salarios sí se incluyen en numerador (costo total)
- Se facturan como overhead en el margen, no por FTE

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Línea: 190
- Filtro: `if not p.es_soporte`

**Escenario**:
- 10 agentes + 1 supervisor
- K50 incluye solo 10 (agentes), no 1 (supervisor)
- Costo incluye salario del supervisor (es parte del costo total)

---

## BR-003: SENA Exclusion Rule

**Categoría**: Staffing

**Descripción**: Cuatro tipos de cargo se excluyen del cómputo base para cálculo de aprendices SENA.

**Roles Excluidos**:
- VALIDADOR: personal QA
- ESPECIALISTA: expertos en proyectos
- APRENDIZ: los propios SENA no se cuentan nuevamente
- INCLUSION: personas inclusión laboral

**Condición**: Siempre que se calcule FTE_SENA.

**Impacto**:
```
Caso 1: 100 agentes + 10 supervisores (OPERATIVO) → FTE_SENA = (100 + 10) / ratio
Caso 2: 100 agentes + 10 validadores (VALIDADOR) → FTE_SENA = 100 / ratio (validadores excluidos)
```

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `CargoClassifier`
- Método: `es_excluido_sena_base(rol: str) → bool` (línea 89)

---

## BR-004: Inclusion Base Rule

**Categoría**: Staffing

**Descripción**: Cuatro tipos de cargo se incluyen en el base FTE de inclusión laboral.

**Roles Incluidos**:
- AGENTE: operadores directos
- OPERATIVO: personal operativo
- ADMINISTRATIVO: administración
- APRENDIZ: aprendices SENA

**Condición**: Siempre que se calcule FTE_Inclusion.

**Impacto**:
```
FTE_Inclusion = (FTE_agentes + FTE_soporte_total + FTE_SENA) / ratio_inclusion
```

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `CargoClassifier`
- Método: `es_incluido_inclusion_base(rol: str) → bool` (línea 99)

---

## BR-005: Especialista Volumetric FTE

**Categoría**: Staffing

**Descripción**: El FTE del Especialista varía proporcionalmente con el total de agentes y validadores.

**Condición**: Cuando hay Especialista de Proyectos en la nómina.

**Fórmula**:
```
FTE_Especialista_canal = (FTE_agentes_canal + FTE_validador_canal) 
                          / (Σ FTE_agentes + Σ FTE_validador)
```

**Impacto**:
- Especialista NO es un FTE fijo
- Se distribuye proporcionalmente entre canales
- Su salario se calcula como: `(sal_cargado × ratio × 3 × complejidad) / meses`

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `EspecialistaCalculator`
- Método: `calcular_fte()` (línea 204)

**Escenario**:
- Canal Voz: 30 agentes, 0 validadores → ratio = 30/50 = 60% especialista
- Canal Email: 20 agentes, 0 validadores → ratio = 20/50 = 40% especialista
- Total FTE_Especialista = 1.0 (distribuido 60/40)

---

## BR-006: Aprendiz SENA Separate Pool

**Categoría**: Staffing

**Descripción**: Los aprendices SENA forman un pool separado, determinado por división entre un ratio fijo.

**Condición**: Cuando hay aprendices SENA en la estructura.

**Fórmula**:
```
FTE_SENA = (FTE_agentes + Σ(soporte_no_excluido)) / ratio_sena
```

**Impacto**:
- No afecta FTE de agentes directamente
- Es un pool adicional calculado por separado
- Su costo es parte del overhead de nómina

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `SENACalculator`
- Método: `calcular_fte()` (línea 252)

---

## BR-007: Rotation Training Monthly

**Categoría**: Staffing

**Descripción**: La capacitación por rotación (nuevos ingresos) se aplica mensualmente a todo el contrato.

**Condición**: Siempre, mientras `pct_rotacion > 0`.

**Fórmula**:
```
cap_rotacion_mes = dias × tarifa × (FTE × pct_rotacion) × factor_idx
```

**Impacto**:
- Si `pct_rotacion = 8.5%` y FTE=10, entonces cada mes se capacita ~0.85 personas nuevas
- Costo recurrente, no amortizado

**Implementación**:
- Archivo: `calculators/nomina.py`
- Método: `_cap_rotacion()` (línea 227)

**Escenario**:
- FTE=20, dias_cap=5, tarifa=200K, pct_rotacion=8.5%
- Mes 1: 5 × 200K × (20 × 0.085) = 170K COP
- Mes 2-12: ídem

---

## BR-008: CargoClassifier: Deterministic Role Mapping

**Categoría**: Staffing

**Descripción**: Los nombres de cargo se clasifican automáticamente mediante tabla de parametrización (no por string matching).

**Condición**: Siempre que se evalue un rol.

**Tipos**:
- AGENTE, OPERATIVO, ADMINISTRATIVO (operacionales)
- VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION (especiales)
- DESCONOCIDO (no clasificado)

**Impacto**:
- Elimina ambigüedad de nombre
- Permite cambios en nombres sin afectar lógica
- Normalización: NFD + lowercase + sin acentos

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `CargoClassifier` (línea 55)
- Método: `clasificar(rol: str) → CargoTipo` (línea 74)

---

# CHANNELS & CADENAS

## BR-009: Cadena A Always Active

**Categoría**: Channels

**Descripción**: Cadena A es obligatoria y siempre está activa.

**Condición**: Siempre.

**Impacto**:
- Input debe tener al menos 1 perfil de Cadena A
- No se puede desactivar
- Genera siempre costos de payroll + no_payroll

**Implementación**:
- Archivo: `input/context_builder.py`
- Validación: Implícita (si no hay perfiles A, error en simulación)

---

## BR-010: Cadena B Optional with Zero-Out

**Categoría**: Channels

**Descripción**: Cadena B es opcional. Si no hay canales o todos están vacíos, se anula automáticamente.

**Condición**: Cuando Cadena B está ausente o tiene volumen=0.

**Impacto**:
- Si `cadena_b.canales = []` → todo Cadena B = 0 COP
- Si `todos los canales.volumen = 0` → costo variable = 0, pero OPEX fijo permanece
- Backward-compat: Si Cadena B ausente → se asume no activa

**Implementación**:
- Archivo: `input/context_builder.py`
- Método: `_construir_cadena_b()`

---

## BR-011: Cadena B S&M Zero-Out Rule

**Categoría**: Channels

**Descripción**: Equipo de Soporte & Mantenimiento (S&M) de Cadena B se anula si no hay operación.

**Condición**: Cuando `(volumen_inbound + volumen_outbound) == 0`.

**Impacto**:
```
if volumen_total == 0:
    soporte_mantenimiento = 0
else:
    soporte_mantenimiento = (costo_personal × factor) + opex_herramientas
```

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Método: `_costo_sm()` (línea 148)

---

## BR-012: Cadena B HITL Zero-Out Rule

**Categoría**: Channels

**Descripción**: HITL de Cadena B se anula si no hay volumen.

**Condición**: Cuando `(volumen_inbound + volumen_outbound) == 0`.

**Impacto**: Igual a BR-011, pero para HITL.

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Método: `_costo_hitl()` (línea 175)

---

## BR-013: Cadena C Optional with Zero-Out

**Categoría**: Channels

**Descripción**: Cadena C es opcional. Si no hay canales, se anula.

**Condición**: Cuando Cadena C está ausente o todos los canales tienen volumen=0.

**Impacto**:
- Si `cadena_c.canales = []` → todo Cadena C = 0 COP
- Si `volumen_total = 0` → equipo_integ e hitl se anulan

**Implementación**:
- Archivo: `input/context_builder.py`
- Método: `_construir_cadena_c()`

---

## BR-014: Cadena C Equipo Zero-Out Rule

**Categoría**: Channels

**Descripción**: Equipo de integración de Cadena C se anula si no hay volumen.

**Condición**: Cuando `volumen_total == 0`.

**Impacto**:
```
if volumen_total == 0:
    equipo_integ = 0
else:
    equipo_integ = (costo_personal + opex_herramientas) × factor_ajuste
```

**Implementación**:
- Archivo: `calculators/cadena_c.py`
- Método: `_costo_equipo()` (línea 164)

---

## BR-015: Cadena C HITL Zero-Out Rule

**Categoría**: Channels

**Descripción**: HITL de Cadena C se anula si no hay volumen.

**Condición**: Cuando `volumen_total == 0`.

**Impacto**: Igual a BR-014.

**Implementación**:
- Archivo: `calculators/cadena_c.py`
- Método: `_costo_hitl()` (línea 188)

---

## BR-016: Per-Canal Activation Flag

**Categoría**: Channels

**Descripción**: Cada canal tiene flag `activo: bool` que indica si se incluye en cálculos.

**Condición**: Siempre.

**Impacto**:
- Permite desactivar canales sin eliminar input
- Flag respetado en auditoría, aunque no filtramos explícitamente en código actual (legacy)

**Implementación**:
- Archivo: `domain/models.py`
- Campos: `CanalCadenaB.activo`, `CanalCadenaC.activo`

---

# PRICING & MARGINS

## BR-017: Factor Billing Calculation (5-Part Composite)

**Categoría**: Pricing

**Descripción**: El factor de facturación es un producto de 5 variables que determina el ingreso requerido.

**Condición**: Siempre.

**Fórmula**:
```
factor = (1-m)(1-op)(1-com)(1-mk)(1+d)
```

Donde:
- m = margen objetivo
- op = contingencia operativa
- com = contingencia comercial
- mk = markup overhead
- d = descuento volumen

**Impacto**:
- factor bajo = ingreso requerido alto
- factor alto = ingreso requerido bajo
- `ingreso = costo / factor`

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Método: `ProfitabilityCalculator.calcular_factor_billing()` (línea 34)

---

## BR-018: Rampup Curve Application

**Categoría**: Pricing

**Descripción**: Los ingresos se reducen en los primeros meses por rampup de operación.

**Condición**: Siempre (aunque factor_rampup=1.0 en meses plenos).

**Fórmula**:
```
ingreso_mes = (costo / factor_billing) × factor_rampup(mes, linea)
```

**Impacto**:
- Mes 1-4 (típico): factor=0.2-0.35 → ingreso = 20-35% del base
- Mes 5+: factor=1.0 → ingreso = 100% del base

**Implementación**:
- Archivo: `calculators/pyg.py`
- Método: `_ingreso_bruto_cadena()`

---

## BR-019: Contingency Op Application

**Categoría**: Pricing

**Descripción**: Contingencia operativa reduce el ingreso en el factor de margen.

**Condición**: Siempre que `op_cont > 0`.

**Impacto**:
- `op_cont=5%` → factor se multiplica por 0.95
- Refleja buffer para variabilidad operativa

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Línea: 56

---

## BR-020: Contingency Com Application

**Categoría**: Pricing

**Descripción**: Contingencia comercial reduce el ingreso en el factor de margen.

**Condición**: Siempre que `com_cont > 0`.

**Impacto**: Idéntica a BR-019.

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Línea: 57

---

## BR-021: Markup Application

**Categoría**: Pricing

**Descripción**: Markup de overhead corporativo reduce el ingreso requerido.

**Condición**: Siempre que `markup > 0`.

**Fórmula**:
```
factor_billing = ... × (1 - markup)
```

**Impacto**:
- `markup=5%` → factor se multiplica por 0.95
- Asigna overhead corporativo al deal

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Línea: 58

---

## BR-022: Discount Application

**Categoría**: Pricing

**Descripción**: Descuento por volumen incrementa el ingreso requerido (ineficiencia de margen).

**Condición**: Siempre que `descuento > 0`.

**Fórmula**:
```
factor_billing = ... × (1 + descuento)
```

**Impacto**:
- `descuento=5%` → factor se multiplica por 1.05
- Requiere más ingresos para lograr mismo margen

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Línea: 59

---

## BR-023: Imprevistos Application (NEW V2-5)

**Categoría**: Pricing

**Descripción**: Presupuesto de contingencia aplicado como línea separada en P&G.

**Condición**: Siempre que `pct_imprevistos > 0`.

**Fórmula**:
```
Imprevistos = (costo + costos_financieros) × pct_imprevistos
```

**Impacto**:
- Buffer adicional para riesgos no previstos
- Típicamente 2-5% del costo base

**Implementación**:
- Archivo: `calculators/pyg.py`
- Método: `_calcular_pyg_mes()`

---

## BR-024: Tariff Denominator

**Categoría**: Pricing

**Descripción**: La tarificación se divide por factor_billing como denominador de márgenes.

**Condición**: Siempre.

**Fórmula**:
```
tarifa = (costo + financiero) / factor_billing / denominador_volumen
```

**Impacto**:
- Tarifa refleja todos los costos (operativos + financieros) distribuidos por volumen
- Asegura margen mínimo configurado

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Método: `calcular_ingreso_desde_costo()`

---

# RISK

## BR-025: Risk Scoring (10 Criteria, 2 Categories)

**Categoría**: Risk

**Descripción**: El riesgo se evalúa en 10 criterios divididos en 2 categorías ponderadas.

**Estructura**:
- CLIENTE (40% peso): 5 criterios
- OPERATIVO (60% peso): 5 criterios

**Condición**: Siempre.

**Impacto**:
- score < 1.5 → Bajo riesgo
- 1.5 ≤ score < 2.5 → Medio
- score ≥ 2.5 → Alto riesgo

**Implementación**:
- Archivo: `calculators/riesgo.py`
- Clase: `RiesgoCalculator`
- Método: `calcular()` (línea 177)

---

## BR-026: Risk Classification (Bajo/Medio/Alto)

**Categoría**: Risk

**Descripción**: El score total se clasifica en 3 niveles.

**Condición**: Siempre.

**Regla**:
- Bajo: score_total < 1.5
- Medio: 1.5 ≤ score_total < 2.5
- Alto: score_total ≥ 2.5

**Implementación**:
- Archivo: `calculators/riesgo.py`
- Método: `_clasificar(score: float) → str` (línea 405)

---

## BR-027: Approval Threshold

**Categoría**: Risk

**Descripción**: Deals por encima de SMMLV×1000 requieren aprobación ejecutiva.

**Condición**: Siempre que `valor_total_deal >= umbral`.

**Umbral**:
```
umbral = SMMLV × 1000 = 1,423,500 × 1000 = 1.4235B COP
```

**Impacto**:
- `requiere_aprobacion = True` si deal supera umbral
- Activa flujo de aprobación

**Implementación**:
- Archivo: `calculators/riesgo.py`
- Línea: 213

---

## BR-028: Alert Triggers

**Categoría**: Risk

**Descripción**: Condiciones específicas disparan alertas de riesgo.

**Alertas**:
1. `pct_rotacion > 10%` → Rotación Alta
2. `período_pago > 60 días` → Período Pago Alto
3. `op_cont < 5%` → Contingencia Op Baja
4. `com_cont < 4%` → Contingencia Com Baja

**Impacto**: Incrementan score_operativo.

**Implementación**:
- Archivo: `calculators/riesgo.py`
- Método: `_criterio_6_alertas_activadas()` (línea 324)

---

# PAYROLL

## BR-029: Salary Indexation Piecewise Constant

**Categoría**: Payroll

**Descripción**: El salario se ajusta anualmente en chunks, no mensualmente.

**Condición**: Siempre.

**Fórmula**:
```
factor = (1 + pct_aumento) ^ ((mes - mes_aplicacion) // 12 + 1)  si mes >= mes_aplicacion
factor = 1.0  si mes < mes_aplicacion
```

**Impacto**:
- Mes 1-12: sin ajuste
- Mes 13-24: +pct_aumento
- Mes 25-36: +(pct_aumento²)

**Implementación**:
- Archivo: `domain/payroll/calculators.py`
- Método: `calcular_factor_aumento()` (línea 29)

---

## BR-030: Commission Conditional on Comision_pct

**Categoría**: Payroll

**Descripción**: Comisiones solo se aplican si `comision_pct > 0`.

**Condición**: Cuando `comision_pct > 0`.

**Fórmula**:
```
comisiones = salario_base × FTE × comision_pct × pct_cumplimiento × factor_idx
si comision_pct > 0; sino 0
```

**Impacto**:
- No se combinan salario_fijo y comisiones en el mismo perfil
- Si comision_pct=0, solo salario_fijo

**Implementación**:
- Archivo: `calculators/nomina.py`
- Método: `_comisiones()` (línea 183)

---

## BR-031: Training Amortization (Initial vs. Rotation)

**Categoría**: Payroll

**Descripción**: Capacitación inicial es one-time amortizada; rotación es recurrente.

**Condición**: Siempre.

**Capacitación Inicial**:
```
cap_inicial_mes = (días × tarifa × FTE) / meses_contrato
→ Distribuida en todos los meses
```

**Capacitación Rotación**:
```
cap_rotacion_mes = días × tarifa × (FTE × pct_rotacion)
→ Recurrente cada mes
```

**Implementación**:
- Archivo: `calculators/nomina.py`
- Métodos: `_cap_inicial()` (línea 212), `_cap_rotacion()` (línea 227)

---

## BR-032: Exam Three-Component Formula

**Categoría**: Payroll

**Descripción**: Exámenes médicos tienen tres componentes sumados.

**Condición**: Siempre que `incluye_examenes=True`.

**Componentes**:
1. Ingreso inicial: `costo × FTE / meses_contrato`
2. Rotación: `costo × FTE × pct_rotacion`
3. Periódico: `costo × FTE × (pct_examen_anual / 12)`

**Impacto**:
- Costo recurrente cada mes
- FTE efectivo incluye fracción de supervisores

**Implementación**:
- Archivo: `calculators/nomina.py`
- Método: `_examenes()` (línea 242)

---

## BR-033: Exam FTE Includes Overhead

**Categoría**: Payroll

**Descripción**: FTE efectivo para exámenes incluye fracción proporcional de supervisores/capacitadores.

**Condición**: Siempre que `fte_examenes > 0`.

**Fórmula**:
```
fte_efectivo = fte_examenes (si > 0) sino fte_base
```

**Impacto**:
- Supervisores también se examinan
- FTE efectivo típicamente 10-30% mayor que FTE base

**Implementación**:
- Archivo: `calculators/nomina.py`
- Línea: 261

---

# FINANCIAL

## BR-034: Financing Only if Enabled

**Categoría**: Financial

**Descripción**: Costo de financiación solo se aplica si `panel.activa_financiacion = True`.

**Condición**: Cuando `activa_financiacion=True`.

**Fórmula**:
```
financiacion = costo × tasa_mensual × (periodo_pago / 30)
```

**Impacto**:
- Si desactiva, financiacion = 0
- Típicamente 0.5-2M COP/mes para grandes deals

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Método: `_calcular_financiacion()` (línea 267)

---

## BR-035: ICA Gross-Up (Income-Equivalent Base)

**Categoría**: Financial

**Descripción**: ICA se calcula con gross-up porque es impuesto sobre ingresos, no costos.

**Condición**: Siempre que `tasa_ica > 0`.

**Fórmula**:
```
base_ingreso = (costo / factor_margen) + polizas + financiacion
ICA = base_ingreso × tasa_ica
```

**Impacto**:
- ICA = ~0.8-1.0% de ingresos equivalentes
- Más alto que GMF porque cubre margin burden

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Método: `_calcular_ica()` (línea 293)

---

## BR-036: GMF No Gross-Up (Actual Cash Base)

**Categoría**: Financial

**Descripción**: GMF se calcula sin gross-up porque es impuesto sobre flujo de caja.

**Condición**: Siempre que `tasa_gmf > 0`.

**Fórmula**:
```
GMF = (costo + polizas + financiacion) × tasa_gmf
```

**Impacto**:
- GMF = ~0.4% de costo total
- No se multiplica por factor_margen

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Método: `_calcular_gmf()` (línea 309)

---

## BR-037: Pólizas Per-Cadena Breakdown

**Categoría**: Financial

**Descripción**: Pólizas de seguros se distribuyen por cadena según proporción de costo.

**Condición**: Siempre que hay pólizas activas.

**Fórmula**:
```
poliza_X = tasa_pura_X × (costo_X + fin_X) / factor_margen_X
```

**Impacto**:
- Cada cadena tiene su propia póliza
- Se suman para total en línea H69 (Excel)

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Línea: 169-172

---

## BR-038: ComAdm = PurePremium × 1.42 (V2-4) or Custom (V2-5)

**Categoría**: Financial

**Descripción**: Comisión de administración es un múltiplo de la prima pura (legacy) o custom desde PolizaContractual.

**Condición**: Siempre que hay pólizas.

**Legacy V2-4**:
```
comAdm = poliza_pura × 1.42
```

**V2-5+**:
```
comAdm = (costo + fin) / factor_margen × tasa_comAdm
```

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Línea: 176-179

---

## BR-039: Costo Financiero VT Per Cadena A (NEW V2-7)

**Categoría**: Financial

**Descripción**: Para Vision Tarifas, costo financiero de Cadena A incluye solo ICA+GMF+pólizas puras (sin comAdm).

**Condición**: Cuando se calcula tariff de Cadena A.

**Fórmula**:
```
costo_financiero_vt_a = ICA_A + GMF_A + polizas_pura_A
```

**Impacto**:
- Comisión de administración se factura por separado (línea aparte)
- Tarifa de Cadena A refleja costo genuino sin admin fee

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Línea: 203

---

# CADENA C (NEW V2-7)

## BR-040: P&G Display Excludes HITL & Opex_var

**Categoría**: Cadena C

**Descripción**: Display P&G contable excluye HITL y opex variable (discretionary).

**Condición**: Siempre en visión P&G.

**Componentes Incluidos**:
- tarifa_proveedor
- opex_fijo_integ
- inversiones
- equipo_integ
- escalamiento

**Componentes Excluidos**:
- hitl (escalada manual)
- opex_var (ajuste fino)

**Impacto**:
- P&G muestra costo "operativo real" sin discrecionales
- Más conservador para reporting

**Implementación**:
- Archivo: `vision_pyg.py`
- Método de cálculo de `costo_c`

---

## BR-041: Financial Base Includes All Costs

**Categoría**: Cadena C

**Descripción**: Base financiera (para tarificación) incluye TODOS los costos.

**Condición**: Siempre en cálculos de tarifa.

**Componentes Incluidos**:
- Todos los de P&G display
- hitl (riesgo escalada)
- opex_var (cobertura completa)

**Impacto**:
- Financial base ≥ P&G display
- Tarifa cubre todo, incluso discrecionales

**Implementación**:
- Archivo: `vision_tarifas.py`
- Campo: `costo_c_fin`

---

## BR-042: Split for Visual vs. Financial

**Categoría**: Cadena C

**Descripción**: División es propositiva: P&G para auditoría contable, base financiera para risk/pricing.

**Condición**: Siempre.

**Rationale**:
- Cliente ve P&G (costo contable)
- Empresa valida márgenes con base financiera (costo real)
- Ambas son correctas en su contexto

---

# FTE VOLUMÉTRICO

## BR-043: K50 = Σ(FTE_outbound) + Σ(vol_cadena_a)

**Categoría**: FTE

**Descripción**: Denominador de Cadena A mezcla FTE (outbound) y transacciones (inbound).

**Condición**: Siempre.

**Fórmula**:
```
K50_perfil_outbound = perfil.fte
K50_perfil_inbound = perfil.vol_cadena_a_mensual
K50_total = Σ K50_perfil
```

**Impacto**:
- Permite tarificación uniforme de modalidades diferentes
- Outbound = posiciones = FTE
- Inbound = transacciones/mes

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Método: `_k50_contrib_perfil()` (línea 192)

---

## BR-044: L50 = Σ(volumen + escalamiento) Cadena B

**Categoría**: FTE

**Descripción**: Denominador de Cadena B suma volumen base + escalamiento.

**Condición**: Siempre.

**Fórmula**:
```
L50 = Σ(canal.volumen_mensual + canal.vol_escalamiento)
```

**Impacto**:
- Refleja operación completa incluyendo peaks
- L50 típicamente 5-20% mayor que volumen base

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Método: `_l50()` (línea 213)

---

## BR-045: M50 = Σ(volumen) Cadena C

**Categoría**: FTE

**Descripción**: Denominador de Cadena C es suma simple de volúmenes.

**Condición**: Siempre (NEW V2-5).

**Fórmula**:
```
M50 = Σ(canal.volumen_mensual)
```

**Impacto**:
- Permite tarificación transaccional de Cadena C
- M50=0 → CTS_C no se calcula (ausencia)

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Método: `_m50()` (línea 218)

---

## BR-046: FTE Volumetric NEW V2-5 (Transaction Volume as FTE-Equiv)

**Categoría**: FTE

**Descripción**: Volumen transaccional se trata como FTE-equivalente en K50 (nueva en V2-5).

**Condición**: Cuando se configura `vol_cadena_a_mensual` en perfil inbound.

**Impacto**:
- Permite deals con volumen inbound (ej. 5000 transacciones/mes)
- Tarificación uniforme: K50 mezcla FTE y vol
- Backward-compat: Si vol=0 (default), K50 = FTE_outbound solamente

**Implementación**:
- Archivo: `domain/models.py` (campo PerfilCadenaA)
- Línea: 43

---

# RESUMEN TABULAR

| ID | Nombre | Categoría | Codificación | Estado |
|----|--------|-----------|--------------|--------|
| BR-001 | HR-Ratios Override | Staffing | input/context_builder.py | V2-7 |
| BR-002 | Support No FTE | Staffing | calc/cost_to_serve.py:190 | V2-7 |
| BR-003 | SENA Exclusion | Staffing | services/special_roles.py:89 | V2-7 |
| BR-004 | Inclusion Base | Staffing | services/special_roles.py:99 | V2-7 |
| BR-005 | Especialista Volumetric | Staffing | services/special_roles.py:204 | V2-6 |
| BR-006 | SENA Separate Pool | Staffing | services/special_roles.py:252 | V2-6 |
| BR-007 | Rotation Training | Staffing | calc/nomina.py:227 | V2-7 |
| BR-008 | CargoClassifier | Staffing | services/special_roles.py:55 | V2-6 |
| BR-009 | Cadena A Always | Channels | (implicit) | V2-7 |
| BR-010 | Cadena B Optional | Channels | input/context_builder.py | V2-7 |
| BR-011 | Cadena B S&M Zero | Channels | calc/cadena_b.py:148 | V2-7 |
| BR-012 | Cadena B HITL Zero | Channels | calc/cadena_b.py:175 | V2-7 |
| BR-013 | Cadena C Optional | Channels | input/context_builder.py | V2-5 |
| BR-014 | Cadena C Equipo Zero | Channels | calc/cadena_c.py:164 | V2-5 |
| BR-015 | Cadena C HITL Zero | Channels | calc/cadena_c.py:188 | V2-5 |
| BR-016 | Per-Canal Activation | Channels | domain/models.py | V2-7 |
| BR-017 | Factor Billing Composite | Pricing | profitability/calc.py:34 | V2-7 |
| BR-018 | Rampup Curve | Pricing | calc/pyg.py | V2-7 |
| BR-019 | Contingency Op | Pricing | profitability/calc.py:56 | V2-7 |
| BR-020 | Contingency Com | Pricing | profitability/calc.py:57 | V2-7 |
| BR-021 | Markup | Pricing | profitability/calc.py:58 | V2-7 |
| BR-022 | Discount | Pricing | profitability/calc.py:59 | V2-7 |
| BR-023 | Imprevistos | Pricing | calc/pyg.py | V2-5 |
| BR-024 | Tariff Denominator | Pricing | profitability/calc.py | V2-7 |
| BR-025 | Risk Scoring | Risk | calc/riesgo.py:177 | V2-7 |
| BR-026 | Risk Classification | Risk | calc/riesgo.py:405 | V2-7 |
| BR-027 | Approval Threshold | Risk | calc/riesgo.py:213 | V2-7 |
| BR-028 | Alert Triggers | Risk | calc/riesgo.py:324 | V2-7 |
| BR-029 | Salary Indexation | Payroll | payroll/calc.py:29 | V2-7 |
| BR-030 | Commission Conditional | Payroll | calc/nomina.py:183 | V2-7 |
| BR-031 | Training Amortization | Payroll | calc/nomina.py:212,227 | V2-7 |
| BR-032 | Exam 3-Component | Payroll | calc/nomina.py:242 | V2-7 |
| BR-033 | Exam FTE Overhead | Payroll | calc/nomina.py:261 | V2-7 |
| BR-034 | Financing Enabled | Financial | costos_fin.py:267 | V2-7 |
| BR-035 | ICA Gross-Up | Financial | costos_fin.py:293 | V2-7 |
| BR-036 | GMF No Gross-Up | Financial | costos_fin.py:309 | V2-7 |
| BR-037 | Pólizas Per-Cadena | Financial | costos_fin.py:169 | V2-7 |
| BR-038 | ComAdm Calculation | Financial | costos_fin.py:176 | V2-5 |
| BR-039 | Costo Fin VT CadenaA | Financial | costos_fin.py:203 | V2-7 |
| BR-040 | P&G Display Excl | Cadena C | vision_pyg.py | V2-7 |
| BR-041 | Financial Base Incl | Cadena C | vision_tarifas.py | V2-7 |
| BR-042 | Split Rationale | Cadena C | (design doc) | V2-7 |
| BR-043 | K50 Mixed Mode | FTE | cost_to_serve.py:192 | V2-5 |
| BR-044 | L50 w/ Escalamiento | FTE | cost_to_serve.py:213 | V2-7 |
| BR-045 | M50 Simple Sum | FTE | cost_to_serve.py:218 | V2-5 |
| BR-046 | FTE Vol Equiv | FTE | domain/models.py:43 | V2-5 |

---

**Fin de BUSINESS_RULES.md**
