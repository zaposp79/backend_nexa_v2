# FORMULAS: Referencia Técnica Completa

**Versión**: V2-7 (engine-v2 refactor)  
**Fecha**: 2026-05-31  
**Clasificación**: Referencia para Desarrolladores

---

## Convenciones

- **Implementación**: Ubicación exacta en código (archivo, líneas, clase)
- **Variables**: Tipo, rango, unidades, fuente de parametrización
- **Ejemplo**: Valores numéricos reales con trazabilidad
- **Excel**: Equivalente en hoja de cálculo (si aplica)

---

# LAYER 2: NÓMINA (PAYROLL)

## 1. Salario Fijo (Componente de Nómina Base)

**Propósito**: Costo mensual de salarios fijos para todos los agentes y staff de Cadena A.

**Fórmula**:
```
salario_fijo = (salario_cargado × FTE × factor_indexacion) − comisiones
```

**Variables**:
- `salario_cargado` (float, COP): Costo completo cargado incluyendo beneficios y cargas sociales
  - Rango: 1M - 50M COP/mes
  - Fuente: HR-Nomina (parametrización)
- `FTE` (float): Equivalentes a tiempo completo del perfil
  - Rango: 0.1 - 100.0
  - Fuente: User input (cadena_a.perfiles[].fte)
- `factor_indexacion` (float): Ajuste salarial por antigüedad
  - Rango: 1.0 - 1.5 (típicamente)
  - Fuente: Calculado de pct_aumento + mes_aplicacion
- `comisiones` (float, COP): Componente variable (si existe)
  - Rango: 0 - salario_cargado × 20%
  - Fuente: Calculado (ver Fórmula 2)

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 146-182
- Clase: `NominaCalculator`
- Método: `_salario_fijo(perfil: PerfilCadenaA, mes: int) → float`

**Ejemplo Numérico**:
- Input:
  - salario_cargado = 5,000,000 COP
  - FTE = 10.0
  - factor_indexacion = 1.05 (5% anual)
  - comisiones = 250,000 COP (mes actual)
- Cálculo:
  - total_cargado = 5M × 10 × 1.05 = 52,500,000 COP
  - salario_fijo = 52,500,000 − 250,000 = 52,250,000 COP
- Output: 52,250,000 COP

**Excel Equivalente**:
- Hoja: "Nomina Loaded" (Excel V2-7)
- Celda: C38:C43 (por mes)
- Fórmula: `=(salario_cargado × FTE × factor_indexacion) − comisiones`

---

## 2. Comisiones (Componente Variable)

**Propósito**: Costo variable de incentivos de ventas/desempeño.

**Fórmula**:
```
comisiones = salario_base × FTE × comision_pct × pct_cumplimiento × factor_indexacion
```

**Variables**:
- `salario_base` (float, COP): Salario base sin beneficios
  - Rango: 0.5M - 10M COP
  - Fuente: HR-Nomina
- `FTE` (float): Headcount
  - Rango: 0.1 - 100.0
- `comision_pct` (float): Tasa de comisión
  - Rango: 0.0 - 0.5 (0% a 50%)
  - Fuente: PerfilCadenaA.comision_pct o HR-Nomina
- `pct_cumplimiento` (float): Factor de cumplimiento de meta
  - Rango: 0.0 - 1.5 (0% a 150%)
  - Fuente: ParametrosCalculo.pct_cumplimiento_variable (default 85%)
- `factor_indexacion` (float): Ajuste salarial anual

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 183-211
- Método: `_comisiones(perfil, mes) → float`

**Ejemplo Numérico**:
- Input:
  - salario_base = 2,500,000 COP
  - FTE = 5.0
  - comision_pct = 0.10 (10%)
  - pct_cumplimiento = 0.85
  - factor_indexacion = 1.05
- Cálculo:
  - comisiones = 2.5M × 5 × 0.10 × 0.85 × 1.05
  - comisiones = 1,109,375 COP
- Output: 1,109,375 COP

**Regla de Aplicación**: Solo se calcula si `comision_pct > 0`. Si es 0, retorna 0 (no hay comisiones).

---

## 3. Capacitación Inicial (Arranque One-Time Amortizado)

**Propósito**: Costo inicial de ramp-up distribuido en todo el contrato.

**Fórmula**:
```
capacitacion_inicial = (dias_cap_inicial × tarifa_dia_cap × FTE × factor_indexacion) / meses_contrato
```

**Variables**:
- `dias_cap_inicial` (int, días): Duración del programa inicial
  - Rango: 1 - 60 días
  - Fuente: PerfilCadenaA.dias_cap_inicial
- `tarifa_dia_cap` (float, COP/día): Costo de capacitación por día
  - Rango: 50,000 - 500,000 COP/día
  - Fuente: Panel.tarifa_diaria_capacitacion
- `FTE` (float): Headcount
- `factor_indexacion` (float): Ajuste salarial
- `meses_contrato` (int): Duración total del contrato
  - Rango: 1 - 60 meses
  - Fuente: Panel.meses_contrato

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 212-226
- Método: `_cap_inicial(perfil, mes) → float`

**Ejemplo Numérico**:
- Input:
  - dias_cap_inicial = 10 días
  - tarifa_dia_cap = 200,000 COP/día
  - FTE = 3.0
  - factor_indexacion = 1.0 (primer mes)
  - meses_contrato = 12
- Cálculo:
  - numerador = 10 × 200,000 × 3.0 × 1.0 = 6,000,000
  - capacitacion_inicial = 6,000,000 / 12 = 500,000 COP/mes
- Output: 500,000 COP (igual cada mes del contrato)

**Nota**: Este es un costo de arranque, no recurrente. Se amortiza a lo largo de toda la duración.

---

## 4. Capacitación Rotación (Nuevos Ingresos Mensual)

**Propósito**: Costo mensual de capacitación para personas nuevas por rotación.

**Fórmula**:
```
capacitacion_rotacion = dias_cap_rotacion × tarifa_dia_cap × (FTE × pct_rotacion) × factor_indexacion
```

**Variables**:
- `dias_cap_rotacion` (int, días): Duración del programa de rotación
  - Rango: 1 - 30 días
  - Fuente: PerfilCadenaA.dias_cap_rotacion
- `pct_rotacion` (float): Porcentaje de staff que rota mensualmente
  - Rango: 0.0 - 0.3 (0% a 30%)
  - Fuente: ParametrosCalculo.pct_rotacion o Panel.pct_rotacion (default desde HR)
- Otros: ídem fórmula anterior

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 227-241
- Método: `_cap_rotacion(perfil, mes) → float`

**Ejemplo Numérico**:
- Input:
  - dias_cap_rotacion = 5 días
  - tarifa_dia_cap = 200,000 COP/día
  - FTE = 3.0
  - pct_rotacion = 0.085 (8.5% mensual)
  - factor_indexacion = 1.05
- Cálculo:
  - personas_nuevas = 3.0 × 0.085 = 0.255
  - capacitacion_rotacion = 5 × 200,000 × 0.255 × 1.05 = 267,750 COP
- Output: 267,750 COP

---

## 5. Exámenes Médicos (Tres Componentes)

**Propósito**: Costo mensual de exámenes ocupacionales (ingreso + rotación + periódico).

**Fórmula**:
```
fraccion = (1 / meses_contrato) + pct_rotacion + (pct_examen_anual / 12)
examenes = costo_examen × FTE_efectivo × fraccion × factor_indexacion
```

**Variables**:
- `costo_examen` (float, COP): Costo por examen individual
  - Rango: 100,000 - 500,000 COP
  - Fuente: ParametrizationProvider.get_examen_medico(ciudad)
- `FTE_efectivo` (float): FTE que incluye fracción de supervisores/capacitadores
  - Rango: 1.1 - 1.5 × FTE_base
  - Fuente: PerfilCadenaA.fte_examenes (si > 0) sino PerfilCadenaA.fte
- `fraccion` (float): Suma de tres componentes
  - Componente 1: 1/meses (ingreso inicial, amortizado)
  - Componente 2: pct_rotacion (nuevos ingresos mensual)
  - Componente 3: pct_examen_anual/12 (periódico)
- Otros: ídem

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 242-273
- Método: `_examenes(perfil, mes) → float`
- Puro: `domain/payroll/calculators.py`, línea 62 (`calcular_examenes_fraccion`)

**Ejemplo Numérico**:
- Input:
  - costo_examen = 250,000 COP
  - FTE_efectivo = 3.3 (FTE=3.0 + 10% supervisores)
  - meses_contrato = 12
  - pct_rotacion = 0.085
  - pct_examen_anual = 0.10 (10% de staff requiere examen periódico)
  - factor_indexacion = 1.05
- Cálculo:
  - fraccion = (1/12) + 0.085 + (0.10/12) = 0.0833 + 0.085 + 0.0083 = 0.1766
  - examenes = 250,000 × 3.3 × 0.1766 × 1.05 = 152,145 COP
- Output: 152,145 COP

---

## 6. Seguridad (Antecedentes, Visitas Domiciliarias)

**Propósito**: Costo de estudios de seguridad (background checks, domicile visits).

**Fórmula**:
```
seguridad = costo_estudio_seg × FTE × factor_indexacion
```

**Variables**:
- `costo_estudio_seg` (float, COP): Costo unitario por estudio
  - Rango: 50,000 - 200,000 COP
  - Fuente: ParametrizationProvider.get_seguridad() (default 0.0 si no configurado)
- Otros: ídem

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 274-279
- Método: `_seguridad(perfil, mes) → float`

**Ejemplo Numérico**:
- Input:
  - costo_estudio_seg = 100,000 COP
  - FTE = 10.0
  - factor_indexacion = 1.05
- Cálculo:
  - seguridad = 100,000 × 10 × 1.05 = 1,050,000 COP
- Output: 1,050,000 COP

---

## 7. Crucero (Idle Time)

**Propósito**: Tarifa por agente en tiempo de descanso (crucero entre campaña).

**Fórmula**:
```
crucero = tarifa_crucero × FTE × factor_indexacion
```

**Variables**:
- `tarifa_crucero` (float, COP): Tarifa mensual por FTE ocioso
  - Rango: 0 - 2M COP
  - Fuente: Panel.tarifa_crucero (default 0.0)
- Otros: ídem

**Implementación**:
- Archivo: `calculators/nomina.py`
- Líneas: 280-292
- Método: `_crucero(perfil, mes) → float`

**Ejemplo Numérico**:
- Input:
  - tarifa_crucero = 500,000 COP/mes
  - FTE = 5.0
  - factor_indexacion = 1.05
- Cálculo:
  - crucero = 500,000 × 5 × 1.05 = 2,625,000 COP
- Output: 2,625,000 COP

---

## 8. Factor Aumento (Indexación Salarial)

**Propósito**: Multiplicador de ajuste salarial anual.

**Fórmula**:
```
años_completos = (mes - mes_aplicacion) // 12 + 1
factor_aumento = (1 + pct_aumento) ^ años_completos   si mes >= mes_aplicacion
factor_aumento = 1.0                                  si mes < mes_aplicacion
```

**Variables**:
- `mes` (int): Mes del contrato (1-based)
  - Rango: 1 - 60
- `pct_aumento` (float): Tasa de aumento anual
  - Rango: 0.0 - 0.2 (0% a 20%)
  - Fuente: Panel.pct_aumento o ParametrizationProvider
- `mes_aplicacion` (int): Primer mes en que se aplica el aumento
  - Típicamente 1 o 13
  - Fuente: Panel.mes_ajuste_indexacion

**Implementación**:
- Archivo: `domain/payroll/calculators.py`
- Líneas: 29-44
- Método: `PayrollCalculator.calcular_factor_aumento(mes, pct_aumento, mes_aplicacion) → float`

**Ejemplo Numérico**:
- Input:
  - mes = 25
  - pct_aumento = 0.05 (5% anual)
  - mes_aplicacion = 13
- Cálculo:
  - años_completos = (25 - 13) // 12 + 1 = 12 // 12 + 1 = 2
  - factor = (1 + 0.05)² = 1.1025
- Output: 1.1025

---

## 9. Salario Cargado (Nómina Cargada con Beneficios)

**Propósito**: Costo total incluyendo beneficios, cargas sociales y contribuciones.

**Fórmula** (simplificada):
```
salario_cargado = salario_base × (1 + tasa_salud + tasa_icbf + tasa_sena + tasa_arl)
```

Donde:
- `tasa_salud`: Aporte a Salud (8% empleador + 4% empleado)
- `tasa_icbf`: Aporte a ICBF (3%)
- `tasa_sena`: Aporte a SENA (0.5%)
- `tasa_arl`: Aporte a Riesgos Laborales (0.5-5% según riesgo)

**Nota**: La fórmula exacta varía según Ley 1819 y configuración. El backend usa NominaCargadaService que calcula esto de forma precisa.

**Implementación**:
- Archivo: `domain/services/nomina_cargada.py`
- Clase: `NominaCargadaService`
- Método: `calcular(salario_base: float) → float`

---

# LAYER 3-5: INFRAESTRUCTURA Y CADENAS

## 10. OPEX TI (Tecnología)

**Propósito**: Costo mensual de infraestructura tecnológica.

**Fórmula**:
```
opex_ti = Σ(costo_concepto_ti)
```

Donde cada concepto TI puede ser:
- Internet dedicado: costo fijo/mes
- Licencias software: costo fijo/mes × estaciones
- Plataforma CRM: costo fijo/mes
- Soporte técnico: costo fijo/mes

**Implementación**:
- Archivo: `input/context_builder.py`
- Líneas: 808-852
- Método: `_calcular_opex_ti_total(perfiles_a) → float`

**Ejemplo Numérico**:
- Input:
  - Internet: 2M COP/mes (fijo)
  - Licencias: 500K × 10 estaciones = 5M COP/mes
  - CRM: 3M COP/mes
- Cálculo:
  - opex_ti = 2M + 5M + 3M = 10M COP
- Output: 10,000,000 COP

---

## 11. CAPEX (Capital Amortizado)

**Propósito**: Amortización mensual de inversiones en equipamiento.

**Fórmula**:
```
capex_mes = Σ(precio_mensual × cantidad × factor_financiero)
```

Donde:
- `precio_mensual = precio_total / meses_amortizacion`
- `cantidad`: número de estaciones que requieren el ítem
- `factor_financiero = 1 + tasa_mensual_financ`

**Implementación**:
- Archivo: `input/context_builder.py`
- Líneas: 854-887
- Método: `_calcular_inversiones_amortizables(perfiles_a, factor) → List[dict]`

**Ejemplo Numérico**:
- Input:
  - Laptop: precio=3M, cantidad=10, meses=36
  - Monitor: precio=0.5M, cantidad=10, meses=24
  - tasa_financiacion = 0.002/mes
- Cálculo:
  - capex_laptop_mes = (3M / 36) × 10 × 1.002 = 834,500 COP
  - capex_monitor_mes = (0.5M / 24) × 10 × 1.002 = 208,750 COP
  - capex_mes = 834,500 + 208,750 = 1,043,250 COP
- Output: 1,043,250 COP

---

## 12. Costos Fijos (Facility)

**Propósito**: Arriendo, servicios (agua, luz), mantenimiento del sitio.

**Fórmula**:
```
costos_fijos = arriendo + servicios + mantenimiento
```

**Implementación**:
- Archivo: `calculators/no_payroll.py`
- Método: `_costo_fijo_operativo()`

---

## 13-19: Cadena B (Plataforma Digital)

### 13. OPEX Fijo Cadena B

**Propósito**: Costo fijo de operación de plataforma digital.

**Fórmula**:
```
opex_fijo_b = Σ(opex_fijo_canal)
```

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Líneas: 130-133
- Método: `_costo_opex_fijo() → float`

---

### 14. Soporte & Mantenimiento (S&M)

**Propósito**: Costo del equipo que da soporte a la plataforma.

**Fórmula**:
```
soporte_mantenimiento = (costo_personal_sm × factor_personal) + opex_herramientas_sm
                        (solo si volumen_total > 0)
```

**Variables**:
- `costo_personal_sm` (float, COP): Salario del equipo S&M
  - Rango: 0 - 50M COP
- `factor_personal` (float): Ajuste salarial
  - Fórmula: `factor_aumento(mes, pct_aumento_personal, mes_aplicacion)`
- `opex_herramientas_sm` (float, COP): Costo de herramientas
  - Rango: 0 - 5M COP

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Líneas: 138-153
- Método: `_costo_sm(vol_inbound, vol_outbound, factor_personal) → float`

**Ejemplo Numérico**:
- Input:
  - costo_personal_sm = 20M COP
  - factor_personal = 1.05
  - opex_herramientas_sm = 2M COP
  - volumen_total = 3000 transacciones
- Cálculo:
  - total = (20M × 1.05) + 2M = 23M COP
- Output: 23,000,000 COP (si volumen > 0)

---

### 15. Costo Variable (Por Transacción)

**Propósito**: Costo transaccional de Cadena B.

**Fórmula**:
```
costo_variable = Σ(volumen_mensual × tarifa_unitaria)
```

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Líneas: 154-164
- Método: `_costo_variable() → float`

**Ejemplo Numérico**:
- Input:
  - Canal 1 (SMS): volumen=5000, tarifa=50 COP
  - Canal 2 (Email): volumen=8000, tarifa=30 COP
- Cálculo:
  - SMS_costo = 5000 × 50 = 250,000 COP
  - Email_costo = 8000 × 30 = 240,000 COP
  - costo_variable = 490,000 COP
- Output: 490,000 COP

---

### 16. Escalamiento (Peak Capacity)

**Propósito**: Costo de capacidad adicional durante picos.

**Fórmula**:
```
escalamiento = Σ(volumen × pct_escalamiento × costo_escalamiento)
```

**Variables**:
- `pct_escalamiento` (float): Porcentaje de volumen que requiere escala
  - Rango: 0.0 - 1.0 (0% a 100%)
- `costo_escalamiento` (float, COP): Costo unitario de escala
  - Rango: 0 - 1000 COP por unidad

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Líneas: 165-174
- Método: `_costo_escalamiento() → float`

---

### 17. HITL Cadena B (Human-in-the-Loop)

**Propósito**: Costo de personal humano para escalada.

**Fórmula**:
```
hitl = (costo_personal_hitl × factor_personal) + opex_herramientas_hitl
       (solo si volumen_total > 0)
```

**Implementación**:
- Archivo: `calculators/cadena_b.py`
- Líneas: 175-189
- Método: `_costo_hitl(vol_inbound, vol_outbound, factor_personal) → float`

---

## 18-19: Cadena C (Integración IA)

### 18. Tarifa Proveedor Cadena C

**Propósito**: Costo del proveedor de IA.

**Fórmula**:
```
tarifa_proveedor = Σ(volumen × tarifa_proveedor_unitaria × factor_ajuste)
```

**Variables**:
- `factor_ajuste` (float): Ajuste tecnológico anual
  - Fórmula: `factor_aumento(mes, pct_aumento_tecnologico, mes_aplicacion)`

**Implementación**:
- Archivo: `calculators/cadena_c.py`
- Líneas: 130-139
- Método: `_costo_tarifa_proveedor(factor) → float`

---

### 19. OPEX Variable Cadena C

**Propósito**: Costos variables de integración.

**Fórmula**:
```
opex_var_integ = Σ(opex_var_canal × factor_ajuste)
```

**Implementación**:
- Archivo: `calculators/cadena_c.py`
- Líneas: 147-153
- Método: `_costo_opex_variable(factor) → float`

---

# LAYER 7: FINANCIERO

## 20. Financiación (Costo de Capital de Trabajo)

**Propósito**: Costo del interés durante el período de crédito.

**Fórmula**:
```
financiacion = costo_mes_anterior × tasa_mensual_financ × (periodo_pago_dias / 30)
               (si activa_financiacion = True)
```

**Variables**:
- `costo_mes_anterior` (float, COP): Costo operativo del mes anterior
  - Rango: 0 - 1,000M COP
  - Fuente: PyGMensual del mes anterior
- `tasa_mensual_financ` (float): Tasa mensual de financiación
  - Rango: 0.001 - 0.01 (0.1% a 1% mensual)
  - Fuente: Panel.tasa_mensual_financ
- `periodo_pago_dias` (int): Período de crédito
  - Rango: 0 - 120 días
  - Fuente: Panel.periodo_pago_dias

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Líneas: 267-278
- Método: `_calcular_financiacion(costo_operativo, factor_periodo) → float`

**Ejemplo Numérico**:
- Input:
  - costo_mes_anterior = 100M COP
  - tasa_mensual_financ = 0.002 (0.2%)
  - periodo_pago_dias = 90
- Cálculo:
  - financiacion = 100M × 0.002 × (90/30) = 100M × 0.002 × 3 = 600K COP
- Output: 600,000 COP

---

## 21. Pólizas Pura (Prima de Seguros)

**Propósito**: Prima de seguros de responsabilidad civil.

**Fórmula**:
```
poliza_pura = tasa_pura × (costo_operativo + financiacion) / factor_margen
```

**Variables**:
- `tasa_pura` (float): Tasa prima anual
  - Rango: 0.002 - 0.02 (0.2% a 2%)
  - Fuente: OP-Poliza parametrización
- `factor_margen` (float): Factor de márgenes (gross-up)

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Líneas: 279-292
- Método: `_calcular_polizas(costo_operativo, financiacion, tasa_polizas, factor_margenes) → float`

**Ejemplo Numérico**:
- Input:
  - costo_operativo = 100M COP
  - financiacion = 0.6M COP
  - tasa_pura = 0.005 (0.5%)
  - factor_margen = 0.722
- Cálculo:
  - poliza_pura = 0.005 × (100M + 0.6M) / 0.722 = 0.005 × 139.06M = 695K COP
- Output: 695,000 COP

---

## 22. Comisión Administración (Admin Fee)

**Propósito**: Comisión de administración sobre pólizas (legacy V2-4) o sobre costo directo (V2-5).

**Fórmula V2-4 (legacy)**:
```
comision_adm = poliza_pura × 1.42
```

**Fórmula V2-5+**:
```
comision_adm = (costo_cadena_a + financiacion_cadena_a) / factor_margen × tasa_comAdm
```

Donde `tasa_comAdm` viene de PolizaContractual.pct_poliza × 1.42

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Líneas: 319-343
- Método: `_calcular_comision_administracion(costo_a, factor_margenes) → float`

---

## 23. ICA (Impuesto Industria y Comercio)

**Propósito**: Impuesto sobre ventas/ingresos.

**Fórmula**:
```
base_ingreso = (costo / factor_margen) + polizas + financiacion
ICA = base_ingreso × tasa_ica
```

**Variables**:
- `tasa_ica` (float): Tasa ICA
  - Rango: 0.004 - 0.012 (0.4% a 1.2%)
  - Fuente: Panel.tasa_ica o ParametrizationProvider.get_ica(ciudad)

**Nota**: Usa GROSS-UP (divide por factor_margen). Refleja que ICA es impuesto sobre ingresos, no costos.

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Líneas: 293-308
- Método: `_calcular_ica(costo_operativo, polizas, financiacion, factor_margenes) → float`

**Ejemplo Numérico**:
- Input:
  - costo_operativo = 100M COP
  - polizas = 0.7M COP
  - financiacion = 0.6M COP
  - factor_margen = 0.722
  - tasa_ica = 0.008 (0.8%)
- Cálculo:
  - base_ingreso = (100M / 0.722) + 0.7M + 0.6M = 139.06M + 1.3M = 140.36M
  - ICA = 140.36M × 0.008 = 1,122,880 COP
- Output: 1,122,880 COP

---

## 24. GMF (Gravamen Movimientos Financieros)

**Propósito**: Impuesto sobre transacciones financieras (4x1000).

**Fórmula**:
```
GMF = (costo + polizas + financiacion) × tasa_gmf
```

**Variables**:
- `tasa_gmf` (float): Tasa GMF (típicamente 0.004 = 4x1000)
  - Rango: 0.004 - 0.005
  - Fuente: Panel.tasa_gmf o ParametrizationProvider.get_gmf()

**Nota**: Sin GROSS-UP. Se aplica a flujo de caja real.

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Líneas: 309-318
- Método: `_calcular_gmf(costo_operativo, polizas, financiacion) → float`

**Ejemplo Numérico**:
- Input:
  - costo_operativo = 100M COP
  - polizas = 0.7M COP
  - financiacion = 0.6M COP
  - tasa_gmf = 0.004
- Cálculo:
  - GMF = (100M + 0.7M + 0.6M) × 0.004 = 101.3M × 0.004 = 405,200 COP
- Output: 405,200 COP

---

## 25. Costo Financiero VT Cadena A (NEW V2-7)

**Propósito**: Costo financiero específico para tarificación Vision Tarifas Cadena A.

**Fórmula**:
```
costo_financiero_vt_cadena_a = ICA_A + GMF_A + polizas_pura_A
```

(Excluye comisión de administración que es facturable por separado)

**Implementación**:
- Archivo: `calculators/costos_financieros.py`
- Línea: 203

---

# LAYER 8-9: P&L Y RENTABILIDAD

## 26. Ingreso Bruto (Gross Income)

**Propósito**: Ingreso mensual antes de impuestos y costos operativos.

**Fórmula**:
```
ingreso_bruto = (costo / factor_billing) × factor_rampup
```

**Variables**:
- `costo` (float, COP): Costo operativo total
- `factor_billing` (float): Factor de márgenes (ver Fórmula en 6.9)
- `factor_rampup` (float): Factor de activación gradual

**Implementación**:
- Archivo: `calculators/pyg.py`
- Método: `_ingreso_bruto_cadena()`

**Ejemplo Numérico**:
- Input:
  - costo = 100M COP
  - factor_billing = 0.722 (margen 20%, op_cont 5%, com_cont 5%)
  - factor_rampup = 0.30 (mes 3)
- Cálculo:
  - ingreso_sin_rampup = 100M / 0.722 = 138.5M COP
  - ingreso_bruto = 138.5M × 0.30 = 41.55M COP
- Output: 41,550,000 COP

---

## 27. Factor Rampup (Activation Curve)

**Propósito**: Factor multiplicador de activación gradual.

**Fórmula**:
```
factor_rampup(mes) = tabla[linea_negocio][mes]
                     (si mes not in tabla: 1.0)
```

**Fuente**: OP-RampUp parametrización por línea de negocio

**Implementación**:
- Archivo: `calculators/pyg.py` o `calculators/utils.py`
- Método: `calcular_factor_rampup(mes, linea_negocio, provider) → float`

---

## 28-30: Márgenes & Contribución

### 28. Contingencia Operativa

**Fórmula**:
```
(1 - op_cont) en factor_billing
```

Donde `op_cont` es Panel.op_cont

### 29. Contingencia Comercial

**Fórmula**:
```
(1 - com_cont) en factor_billing
```

Donde `com_cont` es Panel.com_cont

### 30. Factor Billing (Composite)

**Fórmula**:
```
factor_billing = (1 - margen) × (1 - op_cont) × (1 - com_cont) × (1 - markup) × (1 + descuento)
```

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Líneas: 34-61
- Método: `ProfitabilityCalculator.calcular_factor_billing()`

---

## 31. Utilidad Neta (Profit)

**Propósito**: Ganancia después de todos los costos e impuestos.

**Fórmula**:
```
utilidad_neta = ingreso_bruto - costo_operativo - costos_financieros - imprevistos
```

**Componentes**:
- `costo_operativo`: payroll + no_payroll + cadena_b + cadena_c
- `costos_financieros`: ICA + GMF + pólizas + financiación + comAdm
- `imprevistos`: contingencia presupuestaria

**Implementación**:
- Archivo: `calculators/pyg.py`
- Método: `_calcular_pyg_mes()`

---

# LAYER 10: KPIs

## 32. Costo Mensual Promedio

**Propósito**: Promedio de costo operativo a lo largo del contrato.

**Fórmula**:
```
costo_promedio = SUM(costo_mes_i para i=1..n) / n_meses
```

**Implementación**:
- Archivo: `calculators/kpis.py`
- Método: `calcular_costo_promedio(pyg_por_mes) → float`

---

## 33. % Utilidad Neta

**Propósito**: Margen de ganancia sobre ingresos.

**Fórmula**:
```
pct_utilidad = utilidad_neta / ingreso_bruto × 100%
```

**Implementación**:
- Archivo: `calculators/kpis.py`
- Método: `calcular_pct_utilidad(ingreso_bruto, utilidad_neta) → float`

---

## 34. Valor Total Deal (Contract Lifetime Value)

**Propósito**: Suma de ingresos brutos a lo largo de toda la duración del contrato.

**Fórmula**:
```
valor_total_deal = SUM(ingreso_bruto_i para i=1..n_meses)
```

**Implementación**:
- Archivo: `calculators/kpis.py`
- Método: `calcular_valor_total_deal(pyg_por_mes) → float`

**Ejemplo Numérico**:
- Input: PyG de 12 meses con ingresos variad

os
  - Mes 1-4: 40M (rampup)
  - Mes 5-12: 140M (pleno)
- Cálculo:
  - valor_total = (40M × 4) + (140M × 8) = 160M + 1,120M = 1,280M
- Output: 1,280,000,000 COP

---

# LAYER 11: VISION (COST TO SERVE)

## 35-37. Costo por Unidad Operativa

### 35. CTS_A (Cadena A)

**Propósito**: Costo promedio mensual por FTE de Cadena A.

**Fórmula**:
```
CTS_A = (promedio_payroll_a + promedio_no_payroll_a) / K50
```

Donde K50 = Σ(FTE_outbound) + Σ(vol_cadena_a_inbound)

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Líneas: 126-127

---

### 36. CTS_B (Cadena B)

**Propósito**: Costo promedio mensual por transacción de Cadena B.

**Fórmula**:
```
CTS_B = promedio_costo_b / L50
```

Donde L50 = Σ(volumen_mensual + vol_escalamiento) por canal B

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Línea: 127

---

### 37. CTS_C (Cadena C)

**Propósito**: Costo promedio mensual por transacción de Cadena C.

**Fórmula**:
```
CTS_C = promedio_costo_c / M50
```

Donde M50 = Σ(volumen_mensual) por canal C

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Línea: 129

---

## 38. CTS Ponderado

**Propósito**: Promedio ponderado de todos los CTS.

**Fórmula**:
```
CTS_ponderado = (CTS_A × K50 + CTS_B × L50 + CTS_C × M50) / (K50 + L50 + M50)
```

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Línea: 133-136

---

## 39-41. Tariffs (Per-Unit Pricing)

### 39. Tarifa FTE (Cadena A)

**Propósito**: Tarifa mensual por FTE de Cadena A.

**Fórmula**:
```
tarifa_fte = (costo_a + fin_a) / factor_margen / K50
```

---

### 40. Tarifa Variable (Cadena B)

**Propósito**: Tarifa por transacción de Cadena B.

**Fórmula**:
```
tarifa_variable = (costo_b + fin_b) / factor_margen / L50
```

---

### 41. Tarifa Transaccional (Cadena C)

**Propósito**: Tarifa por transacción de Cadena C.

**Fórmula**:
```
tarifa_cadena_c = (costo_c + fin_c) / factor_margen / M50
```

---

# DENOMINADORES & ESPECIALES

## 42. K50 (Denominador Cadena A)

**Fórmula**:
```
K50 = Σ_outbound(FTE) + Σ_inbound(vol_cadena_a_mensual)
```

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Líneas: 176-212
- Método: `_k50()`, `_k50_contrib_perfil()`

**Ejemplo Numérico**:
- Input:
  - Perfil 1 (Outbound): FTE=10, modalidad="Outbound"
  - Perfil 2 (Inbound): FTE=20, modalidad="Inbound", vol_cadena_a=4534.89
  - Perfil 3 (Soporte): FTE=5, es_soporte=True
- Cálculo:
  - contrib_perf1 = 10.0 (outbound → FTE)
  - contrib_perf2 = 4534.89 (inbound → vol_cadena_a)
  - contrib_perf3 = 0 (soporte excluido de K50)
  - K50 = 10 + 4534.89 = 4544.89
- Output: 4544.89

---

## 43. L50 (Denominador Cadena B)

**Fórmula**:
```
L50 = Σ(volumen_mensual + vol_escalamiento) por canal B
```

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Líneas: 213-217
- Método: `_l50() → float`

**Ejemplo Numérico**:
- Input:
  - Canal 1 (SMS): volumen=2000, vol_escalamiento=500
  - Canal 2 (Email): volumen=1000, vol_escalamiento=0
- Cálculo:
  - L50 = (2000 + 500) + (1000 + 0) = 3500
- Output: 3500.0

---

## 44. M50 (Denominador Cadena C)

**Fórmula**:
```
M50 = Σ(volumen_mensual) por canal C
```

**Implementación**:
- Archivo: `calculators/cost_to_serve.py`
- Líneas: 218-226
- Método: `_m50() → float`

---

## 45. Factor Margen (Composite)

**Fórmula** (repetida para referencia):
```
factor_margen = (1 - margen) × (1 - op_cont) × (1 - com_cont) × (1 - markup) × (1 + descuento)
```

**Implementación**:
- Archivo: `domain/profitability/calculators.py`
- Método: `ProfitabilityCalculator.calcular_factor_billing()`

---

**Fin de FORMULAS.md**
