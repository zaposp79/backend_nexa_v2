# CAPÍTULO 6: Reglas de Negocio Completas

**Versión**: V2-7 (engine-v2 refactor)  
**Fecha**: 2026-05-31  
**Clasificación**: Documentación de Referencia Técnica

---

## Índice

1. **Reglas de Staffing & Roles** (6.1)
2. **Reglas de Canales & Cadenas** (6.2)
3. **Reglas de Billing & Precios** (6.3)
4. **Reglas de Riesgo** (6.4)
5. **Reglas de Nómina** (6.5)
6. **Reglas de Costos Financieros** (6.6)
7. **Reglas de FTE Volumétrico** (6.7)
8. **Reglas de Rampup** (6.8)
9. **Reglas de Márgenes & Contribución** (6.9)
10. **Reglas de Cadena C P&G vs. Financiero** (6.10)

---

## 6.1 Reglas de Staffing & Roles (2-3 páginas)

### 6.1.1 HR-Ratios: Proporciones de Personal

**Definición**: Los ratios de staffing definen la relación numérica entre agentes base y personal de apoyo especializado (supervisores, capacitadores, validadores).

**Estructura**:
- Cada rol de soporte está asociado a un ratio que expresa cuántos agentes requieren una unidad de ese rol.
- Ejemplos: 
  - Supervisor: 1 por cada 10 agentes (ratio = 10)
  - Capacitador: 1 por cada 15 agentes (ratio = 15)
  - Validador: 1 por cada 20 agentes (ratio = 20)

**Fuente**: HR-Ratios en parametrización (storage/parametrization/hr/)

**Implementación**:
- Archivo: `input/context_builder.py`, método `_construir_perfiles_a()`
- Lectura: `IParametrizationProvider.get_ratios_staff()`
- Cálculo FTE soporte: `FTE_soporte_tipo = FTE_agentes / ratio`

---

### 6.1.2 Exclusión de Roles SENA: VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION

**Regla**: Cuatro tipos de roles se excluyen del cómputo base FTE para la contribución de aprendices SENA.

**Roles Excluidos**:
- VALIDADOR: personal de control de calidad
- ESPECIALISTA: expertos en proyectos (no son agentes estándar)
- APRENDIZ: los propios aprendices SENA no se cuentan nuevamente
- INCLUSION: personal de inclusión laboral (pool separado)

**Fórmula de Aprendiz SENA**:
```
FTE_SENA = (FTE_agentes + Σ(soporte sin {VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION})) / ratio_sena
```

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `CargoClassifier.es_excluido_sena_base(rol: str) → bool`
- Método: `SENACalculator.calcular_fte()`
- Líneas: 240-280

---

### 6.1.3 Inclusión en Base de Inclusión: AGENTE, OPERATIVO, ADMINISTRATIVO, APRENDIZ

**Regla**: Cuatro tipos de roles (operativos) se incluyen en la base FTE para el cálculo de Inclusión laboral.

**Roles Incluidos**:
- AGENTE: operadores de contact center
- OPERATIVO: personal operativo general
- ADMINISTRATIVO: personal administrativo en operaciones
- APRENDIZ: aprendices SENA (incluidos en el pool de inclusión)

**Fórmula de Inclusión**:
```
FTE_Inclusion = (FTE_agentes + FTE_soporte_total + FTE_SENA) / ratio_inclusion
```

**Nota**: A diferencia de SENA, no hay exclusiones adicionales en el soporte total para Inclusión.

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `CargoClassifier.es_incluido_inclusion_base(rol: str) → bool`
- Método: `InclusionCalculator.calcular_fte()`
- Líneas: 344-381

---

### 6.1.4 Soporte vs. Agentes: Flag es_soporte

**Regla**: Personal con `es_soporte=True` no ocupa estaciones de trabajo y no se factura directamente al cliente en base FTE.

**Aplicación**:
- Supervisores, capacitadores, validadores, especialistas son soporte
- No se incluyen en el K50 (denominador Cadena A)
- Sus costos se incluyen en el numerador (costo payroll total)
- Sus salarios usan factor_personal (ajuste anual de salarios)

**Campos Asociados**:
- `PerfilCadenaA.es_soporte: bool`
- `PerfilCadenaA.tipo_carga: str` (ej. "EQUIPO_SOPORTE_MANTENIMIENTO")

**Implementación**:
- Archivo: `calculators/nomina.py`, línea 161
- Se valida en K50 computation: `cost_to_serve.py`, línea 190

---

### 6.1.5 CargoClassifier: Mapeo Determinístico Rol → Tipo

**Regla**: Los cargos se clasifican automáticamente en 8 tipos mediante tabla de parametrización, no por comparación de strings.

**Tipos de Cargo**:
1. AGENTE: operadores directo de servicios
2. OPERATIVO: personal operativo general
3. ADMINISTRATIVO: administración operativa
4. VALIDADOR: QA / control de calidad
5. ESPECIALISTA: expertos en proyectos
6. APRENDIZ: aprendices SENA
7. INCLUSION: personas con inclusión laboral
8. DESCONOCIDO: no clasificado

**Normalización**: Los nombres se normalizan (NFD, sin acentos, lowercase) para lookup case/accent-insensitive.

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `CargoClassifier` (líneas 55-107)
- Método: `clasificar(rol: str) → CargoTipo`

---

### 6.1.6 Especialista: FTE Volumétrico por Complejidad

**Regla**: El Especialista de Proyectos tiene FTE proporcional a la complejidad del servicio (BAJA/MEDIA/ALTA) y a la cantidad de agentes y validadores.

**Fórmula FTE**:
```
FTE_Especialista_i = (FTE_agentes_i + FTE_validador_i) / (Σ FTE_agentes + Σ FTE_validador)
```

**Fórmula Salario**:
```
Salario_Especialista = (sal_cargado × ratio × 3 × complejidad) / meses_contrato
```

Donde:
- `sal_cargado`: salario cargado base del Especialista
- `ratio`: FTE ratio desde HR-Ratios
- `complejidad`: multiplicador (BAJA=0.20, MEDIA=0.50, ALTA=0.50)
- `meses_contrato`: duración del contrato

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `EspecialistaCalculator` (líneas 113-203)
- Métodos: `calcular_fte()`, `calcular_salario()`

---

### 6.1.7 Aprendiz SENA: Pool Separado con Exclusiones

**Regla**: Los aprendices SENA se excluyen del cómputo base FTE y se calculan en un pool separado.

**Contribuyentes a FTE_SENA**:
- Todos los agentes (FTE_agentes)
- Soporte sin {VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION}

**Fórmula**:
```
FTE_SENA = (FTE_agentes + Σ(soporte_elegible)) / ratio_sena
```

**Implementación**:
- Archivo: `domain/services/special_roles_calculator.py`
- Clase: `SENACalculator` (líneas 240-280)
- Método: `calcular_fte()`

---

### 6.1.8 Rotación & Turnover: Pct_rotacion en Capacitación

**Regla**: El porcentaje de rotación mensual afecta el cálculo de capacitación de nuevos ingresos (rotación) y exámenes médicos.

**Aplicación**:
- **Capacitación rotación**: `días × tarifa × (FTE × pct_rotación)`
- **Exámenes componente 2**: `costo × FTE × pct_rotación`

**Fuente**: ParametrosCalculo.pct_rotacion (default desde HR-rotacion_ausentismo)

**Implementación**:
- Archivo: `calculators/nomina.py`
- Métodos: `_cap_rotacion()` (línea 227), `_examenes()` (línea 242)

---

### 6.1.9 Nuevos Ingresos: Amortización dias_cap_inicial

**Regla**: El costo de capacitación inicial (arranque del contrato) se amortiza en todos los meses del contrato.

**Fórmula**:
```
Capacitación_Inicial_mes = (días × tarifa × FTE × factor_indexación) / meses_contrato
```

**Interpretación**: Es un costo one-time al inicio, distribuido uniformemente a lo largo de toda la duración del deal.

**Implementación**:
- Archivo: `calculators/nomina.py`
- Método: `_cap_inicial()` (línea 212)

---

## 6.2 Reglas de Canales & Cadenas Activation (2 páginas)

### 6.2.1 Cadena A: Siempre Activa (Requerida)

**Regla**: Cadena A es obligatoria. Siempre está activa y no puede ser deshabilitada.

**Responsabilidad**: Procesos de contact center (voice, chat, email, back-office directo).

**Validación**: El input debe contener al menos un perfil de Cadena A con FTE > 0.

**Implementación**: `input/context_builder.py`, método `_construir_cadenas_activas()`

---

### 6.2.2 Cadena B: Opcional con Autocero

**Regla**: Cadena B es opcional. Si no hay canales configurados o todos tienen volumen=0, la cadena se anula automáticamente (costo=0).

**Responsabilidad**: Plataforma digital (automatización, APIs, integraciones).

**Autocero**:
- Si `cadena_b.canales` está vacía → no hay costos B
- Si todos los canales B tienen `volumen_mensual=0` → costo_variable = 0, pero OPEX fijo y inversiones se cobran

**Backwards Compat**: Si Cadena B está ausente del input → se asume no activa

**Implementación**: `calculators/cadena_b.py`, método `_costo_sm()` (línea 148)

---

### 6.2.3 Cadena B S&M: Autocero si No Hay Volumen

**Regla**: El equipo de Soporte y Mantenimiento (S&M) se carga a cero si no hay operación activa en ninguna modalidad.

**Condición**:
```
if (volumen_inbound + volumen_outbound) == 0:
    soporte_mantenimiento = 0
```

**Campos Evaluados**:
- Inbound: suma de `volumen_mensual` para canales con `modalidad="Inbound"`
- Outbound: suma de `volumen_mensual` para canales con `modalidad="Outbound"`

**Implementación**: `calculators/cadena_b.py`, método `_costo_sm()` (línea 148)

---

### 6.2.4 Cadena B HITL: Autocero si Volumen Total = 0

**Regla**: El equipo HITL (Human-in-the-Loop) se anula si no hay transacciones activas.

**Condición**:
```
if (volumen_inbound + volumen_outbound) == 0:
    hitl = 0
```

**Implementación**: `calculators/cadena_b.py`, método `_costo_hitl()` (línea 175)

---

### 6.2.5 Cadena C: Opcional con Autocero

**Regla**: Cadena C es opcional. Si no hay canales o volumen=0, se anula automáticamente.

**Responsabilidad**: Integración IA y servicios de terceros.

**Autocero**:
- Si `cadena_c.canales` vacía → no hay costos C
- Si todos los canales C tienen `volumen_mensual=0` → se anulan `equipo_integ` e `hitl`

**Implementación**: `calculators/cadena_c.py`, métodos `_costo_equipo()` (línea 164), `_costo_hitl()` (línea 188)

---

### 6.2.6 Cadena C Equipo: Autocero si Volumen = 0

**Regla**: El equipo de integración IA se anula si no hay volumen activo en ningún canal.

**Condición**:
```
if volumen_total == 0:
    equipo_integ = 0
```

**Implementación**: `calculators/cadena_c.py`, método `_costo_equipo()` (línea 164)

---

### 6.2.7 Cadena C HITL: Autocero si Volumen = 0

**Regla**: HITL de Cadena C se anula si no hay volumen.

**Condición**: Idéntica a equipo_integ.

**Implementación**: `calculators/cadena_c.py`, método `_costo_hitl()` (línea 188)

---

### 6.2.8 Per-Canal Activation: Flag activo

**Regla**: Cada canal individual tiene un flag `activo: bool` que controla si se incluye en cálculos.

**Aplicación**: Aunque no filtramos en código por este flag (legacy), el sistema lo respeta en auditoría.

**Campos**:
- `CanalCadenaB.activo: bool`
- `CanalCadenaC.activo: bool`

---

## 6.3 Reglas de Billing & Pricing (2 páginas)

### 6.3.1 ModeloCobroLiteral: 6 Opciones

**Regla**: El modelo de cobro define cómo se estructura el ingreso mensual.

**Opciones**:
1. **Fijo FTE**: Tarifa mensual fija por FTE (más común)
   - Ejemplo: 2,000,000 COP/mes por FTE
2. **Híbrido**: Porcentaje fijo + porcentaje variable
   - Ejemplo: 30% FTE fijo + 70% transaccional
3. **Variable**: Puro transaccional
   - Ejemplo: 500 COP por transacción
4. **Transaccional**: Variable solamente (alias de Variable)
5. **Comisión**: Basado en comisiones de ventas
   - Ejemplo: 5% de ingresos del cliente
6. **Resultados**: Outcome-based (raro)
   - Ejemplo: Por meta alcanzada

**Implementación**: `domain/models.py`, enum `ModeloCobroLiteral`

---

### 6.3.2 Tariff Calculation: Fórmula Fundamental

**Fórmula**:
```
tarifa = (costo_atribuido + fin_atribuido) / factor_margen / volume_denominator
```

Donde:
- `costo_atribuido`: costo operativo de la cadena (payroll + no-payroll + OPEX)
- `fin_atribuido`: costo financiero atribuido (ICA + GMF + polizas + financiación)
- `factor_margen`: factor de márgenes que incorpora contingencias (ver 6.9)
- `volume_denominator`: K50 (cadena A), L50 (cadena B), M50 (cadena C)

**Interpretación**: La tarifa refleja el costo total (incluyendo burdens financieros) distribuido sobre el volumen/FTE de operación.

**Implementación**: `domain/profitability/calculators.py`
- Método: `ProfitabilityCalculator.calcular_ingreso_desde_costo()`

---

### 6.3.3 Factor Margen: Composite de 5 Variables

**Fórmula**:
```
factor_margen = (1 - margen) × (1 - op_cont) × (1 - com_cont) × (1 - markup) × (1 + descuento)
```

Donde:
- `margen`: margen objetivo (típicamente 15-30%)
- `op_cont`: contingencia operativa (típicamente 5-10%)
- `com_cont`: contingencia comercial (típicamente 5-10%)
- `markup`: overhead corporativo (típicamente 0-10%)
- `descuento`: descuento por volumen (típicamente 0-5%, suma con signo +)

**Interpretación**: Cada factor reduce el ingreso requerido (excepto descuento que lo aumenta).

**Ejemplo**:
```
Margen=20%, OpCont=5%, ComCont=5%, Markup=0%, Descuento=0%
factor = 0.8 × 0.95 × 0.95 × 1.0 × 1.0 = 0.722
```

**Implementación**: `domain/profitability/calculators.py`
- Método: `ProfitabilityCalculator.calcular_factor_billing()`

---

### 6.3.4 Rampup Curve: Activación Gradual

**Regla**: Los contratos nuevos generan menos ingresos en los primeros meses (ramp-up de capacidad y operación).

**Factor Rampup**: Varía según línea de negocio (service line) y mes.

**Ejemplo típico (Contact Center)**:
```
Mes:  1    2    3    4    5+
Ramp: 0.2, 0.25, 0.3, 0.35, 1.0
```

**Fórmula de Ingreso**:
```
ingreso_mes = ingreso_base × factor_rampup
```

**Fuente**: OP-RampUp parametrización (Excel OP!E:F)

**Implementación**: `calculators/pyg.py`, método `_ingreso_bruto_cadena()`

---

### 6.3.5 Contingency Application: Op_cont y Com_cont

**Regla**: Las contingencias operativa y comercial reducen el ingreso objetivo.

**Op_cont (Operativa)**:
- Buffer para variabilidad operativa (ausentismo, cambios en volumen)
- Reduce el ingreso en factor_margen

**Com_cont (Comercial)**:
- Buffer para riesgo comercial (retrasos en pago, cambios en scope)
- Reduce el ingreso en factor_margen

**Aplicación**: Se aplican multiplicativamente en el factor_margen.

---

### 6.3.6 Markup & Discount: Margin Adjustments

**Markup**:
- Asignación de overhead corporativo
- Reduce ingreso requerido (multiplicador < 1.0)
- Típicamente 0-10%

**Descuento**:
- Descuento por volumen commitment
- Incrementa ingreso requerido (multiplicador > 1.0)
- Típicamente 0-5%
- Se suma (descuento positivo = factor > 1.0)

---

### 6.3.7 Imprevistos: NEW V2-5

**Regla**: Presupuesto de contingencia aplicado como línea separada en el P&G.

**Fórmula**:
```
Imprevistos = (costo_operativo + costos_financieros) × pct_imprevistos
```

**Uso**: Buffer adicional para riesgos no previstos.

**Fuente**: Panel.pct_imprevistos (típicamente 2-5%)

---

## 6.4 Reglas de Riesgo (2 páginas)

### 6.4.1 Scoring: 10 Criterios en 2 Categorías

**Estructura**:
- **CLIENTE** (40% peso total):
  1. Clasificación oportunidad (30%)
  2. Tipo cliente (25%)
  3. Período pago (25%)
  4. Experiencia cliente (10%)
  5. Presupuesto imprevistos (10%)

- **OPERATIVO** (60% peso total):
  6. Alertas activadas (30%)
  7. Complejidad (20%)
  8. Capacitaciones (20%)
  9. Rotación (20%)
  10. Dependencia terceros (10%)

**Escala**: Cada criterio se califica como 1 (Bajo), 2 (Medio), 3 (Alto).

**Fórmula Score**:
```
score_cliente = SUMPRODUCT(puntaje_i × peso_i) para criterios cliente
score_operativo = SUMPRODUCT(puntaje_i × peso_i) para criterios operativo
score_total = score_cliente × 0.4 + score_operativo × 0.6
```

**Implementación**: `calculators/riesgo.py`, clase `RiesgoCalculator`

---

### 6.4.2 Clasificación Score: 3 Niveles

**Regla**:
- **Bajo**: score_total < 1.5
- **Medio**: 1.5 ≤ score_total < 2.5
- **Alto**: score_total ≥ 2.5

**Implicación**: Determina el nivel de aprobación y auditoría requerido.

**Implementación**: `calculators/riesgo.py`, método `_clasificar()`

---

### 6.4.3 Approval Threshold: SMMLV × 1000

**Regla**: Los deals con valor total ≥ (SMMLV × 1000) requieren aprobación ejecutiva.

**Valores**:
- SMMLV = 1,423,500 COP (2026)
- Umbral = 1,423,500 × 1000 = 1.4235 mil millones COP

**Implementación**: `calculators/riesgo.py`, línea 213

---

### 6.4.4 Alerts: Condiciones Disparo

**Alertas** se disparan cuando:
- `pct_rotacion > 10%` → Rotación Alta
- `período_pago > 60 días` → Período Pago Alto
- `op_cont < 5%` o `com_cont < 4%` → Contingencias bajas

**Efecto**: Incrementan el score de riesgo.

---

## 6.5 Reglas de Nómina (1 página)

### 6.5.1 Salary Indexation: Piecewise Constant

**Regla**: El salario se ajusta anualmente a partir del mes configurado, no mensualmente.

**Fórmula**:
```
factor_aumento(mes) = (1 + pct_aumento) ^ ((mes - mes_aplicacion) // 12 + 1)

si mes < mes_aplicacion: factor = 1.0
si mes_aplicacion ≤ mes < mes_aplicacion+12: factor = (1 + pct_aumento)
si mes_aplicacion+12 ≤ mes < mes_aplicacion+24: factor = (1 + pct_aumento)²
```

**Ejemplo**:
- `mes_aplicacion = 13`, `pct_aumento = 5%`
- Mes 1-12: factor = 1.0 (sin ajuste)
- Mes 13-24: factor = 1.05 (ajuste +5%)
- Mes 25-36: factor = 1.1025 (ajuste +5% acumulado)

**Default**: `mes_aplicacion = 1` (ajuste desde inicio), `pct_aumento = 5%` anual

**Implementación**: `domain/payroll/calculators.py`
- Método: `PayrollCalculator.calcular_factor_aumento()`

---

### 6.5.2 Commission Rules: Condicionales

**Regla**: Comisiones se aplican solo si `comision_pct > 0`.

**Fórmula**:
```
comisiones = salario_base × FTE × comision_pct × pct_cumplimiento_variable × factor_indexacion
```

**Restricción**: No se combinan `salario_fijo` y `comisiones` en el mismo perfil (uno u otro).

**Implementación**: `calculators/nomina.py`, método `_comisiones()` (línea 183)

---

### 6.5.3 Training Amortization: Initial vs. Rotation

**Regla**: La capacitación inicial es un costo one-time amortizado; la rotación es mensual.

**Capacitación Inicial** (one-time):
```
cap_inicial_mes = (días × tarifa × FTE × factor) / meses_contrato
```
Se divide entre todos los meses.

**Capacitación Rotación** (monthly):
```
cap_rotacion_mes = días × tarifa × (FTE × pct_rotacion) × factor
```
Se calcula cada mes por personas nuevas.

**Implementación**: `calculators/nomina.py`
- `_cap_inicial()` (línea 212)
- `_cap_rotacion()` (línea 227)

---

### 6.5.4 Exam Three-Component Formula

**Regla**: Exámenes médicos tienen tres componentes que se suman.

**Componente 1 — Ingreso inicial** (amortizado):
```
comp1 = costo × FTE × (1 / meses_contrato)
```

**Componente 2 — Rotación mensual**:
```
comp2 = costo × FTE × pct_rotacion
```

**Componente 3 — Examen anual periódico**:
```
comp3 = costo × FTE × (pct_examen_anual / 12)
```

**Total**:
```
examenes = costo × FTE_efectivo × (1/meses + pct_rotacion + pct_anual/12) × factor_indexacion
```

**FTE Efectivo**: Incluye fracción proporcional de supervisores y capacitadores que también se examinan.

**Implementación**: `calculators/nomina.py`, método `_examenes()` (línea 242)

---

## 6.6 Reglas de Costos Financieros (2 páginas)

### 6.6.1 Financiación: Capital de Trabajo

**Regla**: El costo de financiación representa el interés sobre el float de capital durante el período de crédito.

**Fórmula**:
```
financiacion = costo_mes_anterior × tasa_mensual × (periodo_pago_dias / 30)
```

Donde:
- `costo_mes_anterior`: costo operativo del mes anterior (si aplica V2-4 convention)
- `tasa_mensual`: tasa mensual de financiación (ej. 0.2% = 0.002)
- `periodo_pago_dias`: período de crédito al cliente (ej. 90 días)

**Activación**: Solo si `panel.activa_financiacion = True`.

**Implementación**: `calculators/costos_financieros.py`, método `_calcular_financiacion()` (línea 267)

---

### 6.6.2 ICA: Gross-up con Grossup

**Regla**: El ICA es un impuesto sobre ingresos, por lo que se calcula con gross-up.

**Fórmula**:
```
base_ingreso_neto = (costo / factor_margen) + polizas + financiacion
ICA = base_ingreso_neto × tasa_ica
```

**Interpretación**: 
- `costo / factor_margen` = ingreso bruto equivalente (retro-calculado del costo)
- Se suma polizas y financiación (también son burdens de ingreso)
- El resultado es el equivalente a un impuesto sobre ventas

**Ejemplo**:
```
costo=100M, factor_margen=0.722, tasa_ica=0.8%
base = (100M / 0.722) + polizas + fin = ~150M
ICA = 150M × 0.008 = 1.2M
```

**Implementación**: `calculators/costos_financieros.py`, método `_calcular_ica()` (línea 293)

---

### 6.6.3 GMF: Sin Gross-up

**Regla**: GMF (4x1000) es un impuesto sobre flujos de caja, no ingresos. No lleva gross-up.

**Fórmula**:
```
GMF = (costo + polizas + financiacion) × tasa_gmf
```

**Nota**: No se divide por factor_margen (impuesto sobre cash flow real, no ingreso equivalente).

**Ejemplo**:
```
costo=100M, polizas=1M, fin=0.5M, tasa_gmf=0.4%
GMF = (100M + 1M + 0.5M) × 0.004 = 406K
```

**Implementación**: `calculators/costos_financieros.py`, método `_calcular_gmf()` (línea 309)

---

### 6.6.4 Insurance Policies: Per-Cadena Breakdown

**Regla**: Las pólizas de seguros se distribuyen por cadena según el costo atribuido.

**Prima Pura** (per-cadena):
```
poliza_X = tasa_pura_X × (costo_X + fin_X) / factor_margen_X
```

**Comisión de Administración**:
- Legacy V2-4: `comAdm = póliza × 1.42`
- V2-5+: Desde tabla PolizaContractual (`comAdm_rate`)

**Fuente Pólizas**:
1. Si usuario proporciona `polizas[]` → usar pólizas del usuario
2. Si vacío (`polizas=[]`) → sin pólizas (costo=0)
3. Si None → usar storage/parametrization (OP-Poliza)

**Implementación**: `calculators/costos_financieros.py`, método `_calcular_polizas()` (línea 279)

---

### 6.6.5 Costo Financiero VT Cadena A: NEW V2-7

**Regla**: Para Vision Tarifas, el costo financiero atribuido a Cadena A incluye solo ICA + GMF + pólizas puras (per-cadena).

**Fórmula**:
```
costo_financiero_vt_cadena_a = ICA_A + GMF_A + polizas_pura_A
```

**Propósito**: Refleja solo la carga financiera de Cadena A, excluyendo comisión de administración que es facturable por separado.

**Implementación**: `calculators/costos_financieros.py`, línea 203

---

## 6.7 Reglas de FTE Volumétrico (1 página)

### 6.7.1 K50: Denominador Cadena A

**Fórmula**:
```
K50 = Σ(FTE_outbound) + Σ(vol_cadena_a_mensual inbound)
```

Donde:
- `FTE_outbound`: para perfiles outbound, se cuenta como transacciones/FTE
- `vol_cadena_a_mensual`: para perfiles inbound, transacciones servidas por Cadena A

**Interpretación**: 
- Outbound = posiciones (FTE)
- Inbound = volumen transaccional (transacciones/mes)
- Ambas unidades se tratan como equivalentes para tarificación

**Nueva en V2-5**: El campo `vol_cadena_a_mensual` permite mezclar modalidades en un solo perfil (ej. 80% inbound, 20% outbound).

**Implementación**: `calculators/cost_to_serve.py`
- Método: `_k50()` (línea 176)
- Sub-método: `_k50_contrib_perfil()` (línea 192)

---

### 6.7.2 L50: Denominador Cadena B

**Fórmula**:
```
L50 = Σ(volumen_mensual + vol_escalamiento) por canal B activo
```

**Nota**: Incluye volumen base + escalamiento para reflejo completo de operación.

**Implementación**: `calculators/cost_to_serve.py`, método `_l50()` (línea 213)

---

### 6.7.3 M50: Denominador Cadena C (NEW V2-5)

**Fórmula**:
```
M50 = Σ(volumen_mensual) por canal C activo
```

**Propósito**: Permite tarificación de Cadena C por transacción.

**Implementación**: `calculators/cost_to_serve.py`, método `_m50()` (línea 218)

---

## 6.8 Reglas de Rampup (1 página)

**Regla**: El factor de rampup reduce ingresos en primeros meses mientras la operación se estabiliza.

**Variación**: Por línea de negocio (service line) y mes.

**Ejemplo Rampup**:
```
Contact Center:   Mes 1=0.20, 2=0.25, 3=0.30, 4=0.35, 5+=1.0
BackOffice:       Mes 1=0.30, 2=0.50, 3=0.75, 4+=1.0
Processing:       Mes 1=0.15, 2=0.20, 3=0.35, 4=0.60, 5+=1.0
```

**Aplicación**: `ingreso_bruto = ingreso_base × factor_rampup`

**Fuente**: OP-RampUp parametrización

**Implementación**: `calculators/pyg.py`, método `_ingreso_bruto_cadena()`

---

## 6.9 Reglas de Márgenes & Contribución (1 página)

**Gross Margin** (`panel.margen`): Margen objetivo mínimo (15-30%)

**Operational Contingency** (`panel.op_cont`): Buffer operativo (5-10%)

**Commercial Contingency** (`panel.com_cont`): Buffer comercial (5-10%)

**Markup** (`panel.markup`): Overhead corporativo (0-10%)

**Discount** (`panel.descuento`): Descuento volumen (0-5%)

**Imprevistos** (NEW V2-5): Contingencia presupuestaria (2-5%)

**Factor Billing**:
```
factor = (1-m)(1-op)(1-com)(1-mk)(1+d)
```

**Impacto**: Determina el ingreso requerido a partir del costo operativo:
```
ingreso = costo / factor_billing × factor_rampup
```

**Implementación**: `domain/profitability/calculators.py`
- Método: `ProfitabilityCalculator.calcular_factor_billing()`

---

## 6.10 Cadena C P&G vs. Financiero: NEW V2-7

### 6.10.1 P&G Display (Contable)

**Componentes Incluidos**:
- tarifa_proveedor
- opex_fijo_integ
- opex_var_integ
- inversiones (amortizadas)
- equipo_integ (personal + herramientas)
- escalamiento

**Componentes Excluidos**:
- HITL (considerado discrecional)
- opex_var (opcional, ajuste fino)

**Propósito**: Refleja el costo operativo real, "activo" (que el cliente percibe).

### 6.10.2 Financial Base (Para Cálculos)

**Componentes Incluidos**:
- Todos los de P&G display
- HITL (riesgo de escalada)
- opex_var (cobertura completa)

**Propósito**: Base de cálculo de tarifa y riesgo (cobertura exhaustiva).

### 6.10.3 División Rationale

**Por qué**: P&G muestra lo que el cliente ve contablemente. La base financiera cubre todos los costos para tarificación y validación de márgenes.

**Implementación**: 
- P&G display: `vision_pyg.py`, cálculo de `costo_c`
- Financial base: `vision_tarifas.py`, cálculo de `costo_c_fin` para denominador

---

## Conclusiones

Las reglas de negocio documentadas en este capítulo se codifican explícitamente en los calculadores del motor, no como guías sino como lógica determinística. Cada regla es:

1. **Trazable** a código específico
2. **Testeable** con casos de prueba
3. **Auditable** con trazas estructuradas
4. **Parametrizable** desde storage/parametrization/

El sistema V2-7 mantiene coherencia entre Excel y backend mediante estas reglas, permitiendo que los analistas entiendan exactamente cómo se calcula cada métrica.

---

**Fin del Capítulo 6**
