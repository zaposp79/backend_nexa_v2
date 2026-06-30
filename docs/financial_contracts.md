# Contratos Financieros — NEXA Pricing Engine

> **IMPORTANTE**: Las fórmulas de este documento están congeladas y validadas contra
> el Excel V2-4 con delta 0.00000%. **NO modificar ninguna fórmula sin actualizar el
> baseline oficial** (`reports/baseline_oficial.json`) y sin ejecutar `make all`.

---

## 1. Factor de Márgenes

**Archivo**: `calculators/utils.py → calcular_factor_margenes()`

```
factor_margenes = (1 - margen)
                × (1 - op_cont)
                × (1 - com_cont)
                × (1 - markup)
                × (1 + descuento)
```

- **Base**: `PanelDeControl`
- **Uso**: convierte costo base en precio de venta neto (denominador del gross-up)
- **Restricción**: todos los parámetros son porcentajes del `PanelDeControl`. No hay calibraciones.

---

## 2. Factor de Indexación Salarial

**Archivo**: `calculators/nomina.py → _factor_indexacion()`

```
factor_indexacion(mes) = factor_indexacion_base
                       × (1 + pct_aumento_salarial) ^ años_completos

donde:
  años_completos = max(0, (mes - mes_aplicacion_aumento) // 12 + 1)
                   si mes >= mes_aplicacion_aumento, else 0
```

- **Base**: `ParametrosNomina`
- **`factor_indexacion_base`**: = 1.0 para el año de inicio del contrato (base siempre es el año actual)
- **Restricción**: `factor_indexacion_base = 1.0` es la convención acordada. El factor acumulado de IPC
  se refleja en los salarios ya parametrizados, no en el factor base.

---

## 3. Nómina Cargada por FTE

**Archivo**: `domain/services/nomina_cargada.py`

### 3.1 Empleado estándar (`calcular()`)

```
T.Imponible = salario_base × (1 + comision_pct × pct_cumplimiento_variable)
T.Haberes   = T.Imponible + aux_transporte  [si T.Imponible < 2 × SMMLV]

# Aportes patronales (Ley 1819 aplica cuando aplica_ley_1819=True):
salud     = 0  [exonerado si T.Imponible < 10×SMMLV y aplica_ley_1819=True]
            T.Imponible × 8.5%  [si aplica_ley_1819=False o alto salario]
pension   = T.Imponible × 12%
arl       = T.Imponible × 0.522%
caja      = T.Imponible × 4%
icbf_sena = 0  [exonerado si T.Imponible < 10×SMMLV y aplica_ley_1819=True]
            T.Imponible × 4%  [si aplica_ley_1819=False o alto salario]

# Para alto salario (T.Imponible > 10 × SMMLV):
  Todos los aportes se multiplican por factor_corrector = 0.70
  Prestaciones (cesantías, primas, int_ces, vacaciones) = 0

# Prestaciones (si T.Haberes ≤ umbral):
cesantias  = T.Haberes × 8.33%
primas     = T.Haberes × 8.33%
int_ces    = cesantias × 12%
vacaciones = T.Imponible × 4.17%

# Beneficios:
dotaciones = dotaciones_mensual  [si T.Imponible < 2 × SMMLV]

Costo_total = T.Haberes + seg_social + parafiscales + prestaciones + dotaciones
```

### 3.2 Equipo S&M (`calcular_sm()`)

Diferencias respecto al estándar:
- Sin Caja (4%) como parafiscal
- ARL se incluye tanto en `seg_social` como en `parafiscales`
- Prestaciones se calculan sobre `pension` (no sobre T.Haberes)

### 3.3 Contrato de aprendizaje (`calcular_aprendiz()`)

- Sin pensión, ARL, ICBF+SENA
- Solo Caja (4%)
- Prestaciones sobre T.Haberes normales
- Sin dotaciones

---

## 4. Financiación

**Archivo**: `calculators/costos_financieros.py → _calcular_financiacion()`

```
financiacion(mes) = factor_periodo × tasa_mensual_financ × costo_op(mes - 1)

donde:
  factor_periodo = periodo_pago_dias / 30   [entero]
  costo_op(0) = 0   [convención Excel V2-4: mes 1 no tiene mes anterior]
```

- **Gross-up**: NO
- **Timing**: usa el costo del **mes anterior** (convención Excel V2-4)
- **Restricción**: `activa_financiacion=False` devuelve 0 independientemente de las tasas

---

## 5. Pólizas de Seguros

**Archivo**: `calculators/costos_financieros.py → _calcular_polizas()`

```
polizas(mes) = tasa_polizas_efectiva(mes) × (costo_op + financiacion) / factor_margenes

donde:
  tasa_polizas_efectiva = Σ(tasa_i × atribucion_i) para polizas con mes_inicio ≤ mes
```

- **Gross-up**: SÍ (división por `factor_margenes`)
- **Base de cálculo**: `costo_op + financiacion` normalizado al ingreso bruto equivalente
- **Tasa efectiva**: acumulativa — se suman las pólizas que se van activando mes a mes

---

## 6. ICA (Impuesto de Industria y Comercio)

**Archivo**: `calculators/costos_financieros.py → _calcular_ica()`

```
ica = (costo_op / factor_margenes + polizas + financiacion) × tasa_ica
```

- **Gross-up**: SÍ (el término `costo_op / factor_margenes` convierte al ingreso neto)
- **Justificación**: el ICA grava el ingreso, no el costo. La base imponible equivale al
  ingreso neto del período más los costos financieros ya calculados.
- **Tasa ICA**: configurada por ciudad en `OP-ICA` (ej. Bogotá = 0.0097 = 0.97%)

---

## 7. GMF (Gravamen a los Movimientos Financieros / 4×1000)

**Archivo**: `calculators/costos_financieros.py → _calcular_gmf()`

```
gmf = (costo_op + polizas + financiacion) × tasa_gmf
```

- **Gross-up**: NO (aplica sobre el flujo de caja real, no sobre el ingreso)
- **Tasa GMF**: fija en Colombia = 0.004 (4 × 1000)
- **Restricción**: la base NO divide por `factor_margenes`, a diferencia del ICA

---

## 8. Ingreso Bruto (PyG)

**Archivo**: `calculators/pyg.py`

```
ingreso_bruto_a(mes) = costo_a(mes) / factor_margenes × rampup(linea, mes)
ingreso_bruto_b(mes) = costo_b(mes) / factor_margenes × rampup(linea, mes)
ingreso_bruto_c(mes) = costo_c(mes) / factor_margenes × rampup(linea, mes)
```

- **Ramp-up**: factor de escala [0, 1] por línea de negocio y mes (tabla GN-RampUp)
- **Restricción**: el ramp-up NO afecta el costo, solo el ingreso proyectado

---

## 9. Ingreso Neto (PyG)

**Archivo**: `calculators/pyg.py`

```
ingreso_neto = ingreso_bruto_a + ingreso_bruto_b + ingreso_bruto_c
             + contingencia_op_a + contingencia_op_b + contingencia_op_c
             + contingencia_com_a + contingencia_com_b + contingencia_com_c
             + markup_a + markup_b + markup_c
             - descuento_a - descuento_b - descuento_c
```

---

## 10. KPIs del Deal

**Archivo**: `calculators/kpis.py`

```
# Costo promedio mensual (Cadena A, solo meses con costo > 0)
costo_promedio_a = Σ(costo_a_mes_i) / meses_con_costo

# Tarifa mensual (precio que se cobra al cliente)
ingreso_mensual = (costo_promedio_a + costos_financieros_sobre_promedio) / factor_margenes

# Facturación considerando el período de pago
facturacion_mensual = ingreso_mensual / factor_periodo_pago

# Utilidad neta total del contrato
pct_utilidad_neta = Σ(utilidad_neta_i) / Σ(ingreso_neto_i)

# Valor total del deal
valor_total_deal = Σ(ingreso_neto_i)  para i en todos los meses
```

---

## 11. Cost To Serve (CTS)

**Archivo**: `calculators/cost_to_serve.py`

```
# Cadena A
total_fte_agentes = 2 × Σ(fte_i para perfiles agente)   [convención Excel: 2×]
cts_cadena_a      = costo_a_promedio / total_fte_agentes  [COP / FTE / mes]

# Cadena B
total_volumen = Σ(volumen_mensual_canal_j)
cts_cadena_b  = costo_b_promedio / total_volumen   [COP / unidad / mes]

# CTS Ponderado
cts_ponderado = (cts_a × total_fte_agentes + cts_b × total_volumen) / (total_fte_agentes + total_volumen)
```

> **Nota sobre el factor 2×**: en el Excel V2-4, la celda K50 es `2 × FTE_agentes`.
> Esta calibración está documentada en `reports/clasificacion_calibraciones.md`.

---

## Restricciones globales

1. **No modificar ninguna fórmula** sin ejecutar `make all` y verificar que todos los deltas sigan en 0.00000%.
2. Los parámetros de tasas (ICA, GMF, pólizas) se leen exclusivamente de `storage/parametrization/op/`.
3. Los salarios y aportes patronales se leen exclusivamente de `storage/parametrization/hr/`.
4. Los márgenes y ramp-up se leen exclusivamente de `storage/parametrization/gn/`.
5. **Ningún valor de negocio debe estar hardcodeado** en los calculadores o el context_builder.
