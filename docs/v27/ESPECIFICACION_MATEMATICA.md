# ESPECIFICACIÓN MATEMÁTICA FORMAL — V2-7

> Todas las fórmulas con equivalente Python. Variables en snake_case.

---

## MÓDULO 1: NOMINA LOADED (Costo Laboral)

### 1.1 Estructura de Salario

```python
# Inputs base (Inputs de Nomina)
smmlv = 1_750_905          # COP/mes 2026
auxilio_transporte = 249_095  # COP/mes 2026
horas_mes = 220            # hardcode

# Por cargo:
salario_base_cargo = {
    "Director de cuentas":        18_505_000 * (1 + 0.23),   # IPC 23%
    "Director de Performance":    13_000_000 * (1 + IPC),
    "Jefe Comercial Regional":    5_260_000 * (1 + IPC),
    "Analista profesional AFAC":  2_987_680 * (1 + IPC),
    # ... (todos los cargos de Inputs de Nomina filas 16-48)
}
```

### 1.2 Fórmula de Salario Variable (Comisiones)

```python
salario_variable = pct_comision_cargo * salario_base * pct_cumplimiento_variable
# pct_cumplimiento_variable = 0.70 (Panel de Control General C6)
```

### 1.3 T. Imponible y Haberes

```python
imponible = salario_base + salario_variable

# Auxilio de transporte (solo si imponible < 2 × SMMLV)
aux_transporte = auxilio_transporte if (0 < imponible < 2 * smmlv) else 0

# Recargos (antes de T.Haberes)
recargo_festivo   = (salario_base / 220) * n_horas_festivo * 0.90
recargo_dominical = (salario_base / 220) * n_horas_dominical * 0.90
recargo_nocturno  = (salario_base / 220) * n_horas_nocturno * 0.35
recargo_fest_noc  = (salario_base / 220) * n_horas_fest_noc * (1 + 0.15)
recargo_dom_noc   = (salario_base / 220) * n_horas_dom_noc * (1 + 0.15)
recargo_extra_dia = (salario_base / 220) * n_horas_extra_dia * (1 + 0.25)
recargo_extra_noc = (salario_base / 220) * n_horas_extra_noc * (1 + 0.75)
total_recargos = sum(todos_los_recargos)

t_haberes = imponible + aux_transporte + total_recargos
```

### 1.4 Seguridad Social (Empresa)

```python
base_ss = t_haberes - aux_transporte  # base para SS = T.Haberes - auxilio

# Topes (Ley 1819: empleados > 10 SMMLV tienen base reducida al 70%)
tope = 10 * smmlv
base_reducida = base_ss * 0.70 if base_ss > tope else base_ss

# Salud (empleador): solo aplica si salario <= 10 SMMLV
salud_empresa = base_reducida * 0.085 if imponible > tope else 0

# Pensión (empleador)
pension_empresa = base_reducida * 0.12

# ARL (diferenciado agentes vs staff)
arl_agentes = base_reducida * 0.00522
arl_staff   = base_reducida * 0.00522  # mismo valor en V2-7

# Seguridad social empleado total (columna M)
ss_empleado = t_haberes + salud_empresa + pension_empresa + arl_agentes  # o arl_staff
```

### 1.5 Parafiscales (Empresa)

```python
# Caja de Compensación
caja = base_reducida * 0.04 if base_ss > tope else base_ss * 0.04

# ICBF + Sena: solo aplica si imponible <= 10 SMMLV
icbf_sena = imponible * 0.04 if imponible <= tope else 0

parafiscales = caja + icbf_sena  # columna P
```

### 1.6 Prestaciones Sociales

```python
# Topes: si T.Haberes > 10×SMMLV → base = T.Haberes (sin reducción en prestaciones)
base_prest = t_haberes  # no tiene el recorte del 70% aquí

cesantias        = base_prest * 0.0833   # columna Q
primas           = base_prest * 0.0833   # columna R
interes_cesantia = cesantias * 0.12      # columna S = 12% de cesantías
vacaciones       = base_reducida * 0.0417  # columna T: usa base reducida

# Nota: si T.Haberes > 10×SMMLV → cesantias = primas = interes = vacaciones = 0
# Implementación Excel:
cesantias_excel  = 0 if t_haberes > tope else t_haberes * 0.0833
primas_excel     = 0 if t_haberes > tope else t_haberes * 0.0833
vacaciones_excel = ((base_reducida * 0.70) * 0.0417) if base_reducida >= tope else base_reducida * 0.0417

prestaciones = cesantias_excel + primas_excel + interes_cesantia + vacaciones_excel
```

### 1.7 Dotaciones

```python
dotacion_anual   = (50_000 / 4) * 12 * (1 + 0.23)  # hardcode: 184,500 COP/año
dotacion_mensual = dotacion_anual / 12

dotacion = dotacion_mensual if (0 < (imponible - aux_transporte) < 2 * smmlv) else 0
```

### 1.8 Carga Prestacional Total (Empresa)

```python
carga_prestacional = ss_empleado + parafiscales + prestaciones + dotacion
# columna W = M + P + U + V
```

### 1.9 Costo Empresa Total

```python
costo_empresa = carga_prestacional  # columna AM = W para la mayoría
# Excepción: Director de Cuentas = 29,031,301 COP (hardcodeado)
```

### 1.10 Proyección Mensual con Indexación

```python
def factor_indexacion(mes_numero, tipo_componente, mes_ajuste):
    """
    mes_numero: posición en el contrato (1..60)
    tipo_componente: "80% SMMLV 20% IPC", "20% SMMLV 80% IPC", etc.
    mes_ajuste: mes del año en que se aplica el ajuste (ej: 6 = junio)
    """
    # El factor es 1.0 hasta que llega el primer aniversario/ajuste
    # Luego aplica el acumulado según la fórmula elegida
    tablas_acumulados = {
        "80% SMMLV 20% IPC": tabla_14_tasas,   # row 14 de Tasas
        "20% SMMLV 80% IPC": tabla_15_tasas,   # row 15
        "50% SMMLV 50% IPC": tabla_13_tasas,   # row 13
        "IPC":                tabla_8_tasas,    # row 8
        "SMLV":               tabla_9_tasas,    # row 9
        "Tarifas definidas":  tabla_12_tasas,   # row 12 = siempre 1.0
    }
    return tablas_acumulados[tipo_componente][año_del_mes]

costo_mes_n = costo_empresa * ratio_staffing * factor_indexacion(n, tipo, mes_ajuste)
```

---

## MÓDULO 2: NO PAYROLL (Costos Tecnológicos)

### 2.1 OPEX Fijo

```python
opex_fijo_mensual = valor_rubro × cantidad_unidades × factor_indexacion_tec
# factor_indexacion_tec usa "Componente Tecnológico" (20% SMMLV 80% IPC)
```

### 2.2 Inversiones (CAPEX diferido)

```python
valor_total_inversion = precio_unitario × cantidad
cuota_mensual = (valor_total / meses_diferir) × (1 + tasa_interes_mensual)
# tasa_interes_mensual = Panel de Control General!$L$10 = 0.0153
```

### 2.3 Costos Fijos por Estación de Trabajo

```python
costo_estacion_mensual = tarifa_estacion × n_estaciones_presenciales
n_estaciones_presenciales = FTE × pct_presencial  # pct_presencial ≈ 0.60
```

---

## MÓDULO 3: STAFFING (Condiciones Cadena A)

### 3.1 FTE por Perfil Operativo

```python
# Input directo del usuario en Panel de Control General (por canal/modalidad)
fte_agentes = {
    ("Inbound", "Voz"): 25,
    ("Inbound", "WhatsApp"): 15,
    # etc.
}
```

### 3.2 Ratio de Staffing

```python
def ratio_staffing(cargo, fte_agentes, fte_staff_cargo, es_rol_rotacion):
    if es_rol_rotacion:
        return (fte_agentes / fte_staff_cargo) * pct_rotacion
    else:
        return fte_agentes / fte_staff_cargo

# Roles de rotación: Reclutamiento, Capacitación
# pct_rotacion = Panel de Control General!$C$20 = 0.085
```

### 3.3 TMO → FTE (Conversión)

```python
tmo_segundos = 522.2  # hardcode en Condiciones Cadena A!E8
tmo_horas = tmo_segundos / 3600

# Productividad (horas productivas / hora total)
horas_semanales = 42
semanas_mes = 4.33
horas_programadas_mes = horas_semanales * semanas_mes  # = 181.86 h

# Deducciones de tiempo improductivo
breaks_dia     = 30 / 60  # 0.5 horas
capacitacion   = ((8/4)/6) * 60 / 60  # horas formación / 4 semanas / 6 días
deslogueos_dia = 5 / 60
coaching_dia   = 5 / 60
pausa_activa   = 5 / 60

min_improductivos_dia = 30 + 5 + 5 + 5  # más capacitación variable
pct_improductivo = min_improductivos_dia / ((42/6) * 60)  # sobre jornada diaria

# Horas logueadas = programadas × (1 - breaks - deslogueos - capacitación)
# Horas productivas = logueadas × (1 - coaching - pausa_activa)
```

---

## MÓDULO 4: REGLAS DE NEGOCIO (Markup y Márgenes)

### 4.1 Estructura de Margen

```python
reglas = {
    "contingencia_operativa":  cont_op,    # Panel!C67
    "contingencia_comercial":  cont_com,   # Panel!C68
    "markup_complejidad":      markup,     # Panel!C69
    "descuento_volumen":       descuento,  # Panel!C70
    "imprevistos":             imprev,     # Panel!C73
}

porcentaje_total = cont_op + cont_com + markup - descuento
```

### 4.2 Margen Objetivo por Cadena

```python
# Cadena A: viene de tabla Rot,Ausent!C28:C34 por servicio
margenes_objetivo_a = {
    "Cobranzas":         0.18,
    "SAC":               0.18,
    "Ventas Multicanal": 0.18,
    "SACO":              0.105,
    "Plataformas":       0.15,
    "Captura de Datos":  0.3292,
}
margen_efectivo_a = margenes_objetivo_a[servicio] + porcentaje_total

# Cadena B: hardcode 0.30
margen_b = 0.30 + porcentaje_total

# Cadena C: hardcode 0.20
margen_c = 0.20 + porcentaje_total
```

### 4.3 Fórmula de Pricing (Ingreso desde Costos)

```python
def ingreso_desde_costo(costo_directo, margen, cont_op, cont_com, markup, descuento):
    """
    Excel: =costo / ((1-margen)*(1-cont_op)*(1-cont_com)*(1-markup)*(1+descuento))
    """
    return costo_directo / (
        (1 - margen) * (1 - cont_op) * (1 - cont_com) * (1 - markup) * (1 + descuento)
    )
```

---

## MÓDULO 5: TARIFAS (Vision Tarifas / Hoja Maestra)

### 5.1 Tarifa por FTE (Componente Fijo = FTE)

```python
def tarifa_fte(ingreso_componente_fijo, fte_total, duracion_meses):
    """
    Excel: =G19/C13/'Panel de Control General'!C11
    """
    return ingreso_componente_fijo / fte_total / duracion_meses
```

### 5.2 Tarifa por Hora Logueada (Componente Fijo = Tiempo)

```python
def tarifa_hora_logueada(ingreso_fijo, minutos_logueados_total, duracion_meses):
    """
    Excel: =G19/L26/'Panel de Control General'!C11
    L26 = minutos logueados totales
    """
    return ingreso_fijo / minutos_logueados_total / duracion_meses
```

### 5.3 Tarifa por Transacción (Componente Variable)

```python
def tarifa_transaccion(costo_total_cadenas, proporcion_variable, volumen_total):
    """
    Excel: =(SUM(costos_A,B,C) * prop_variable) / G31
    donde G31 = tarifa por transacción (referencia circular resuelta con CHOOSE/MATCH)
    """
    # La tarifa se obtiene directamente de la Hoja Maestra
    # por lookup del escenario actual
    pass
```

### 5.4 Volumen Mínimo de Transacción

```python
def volumen_minimo(costos_totales, prop_variable, tarifa_transaccion):
    """
    Excel: =(SUM(C16,C26,C36)*D11)/G31
    """
    return (costos_totales * prop_variable) / tarifa_transaccion
```

### 5.5 Facturación Total del Deal

```python
facturacion_total = ingreso_a + ingreso_b + ingreso_c

# Con descomposición componente fijo/variable:
ingreso_fijo    = facturacion_total * prop_fija
ingreso_variable = facturacion_total * prop_variable
```

---

## MÓDULO 6: FINANCIERO (ICA, GMF, Pólizas)

### 6.1 ICA (Impuesto de Industria y Comercio)

```python
tasas_ica = {
    "Armenia":        0.006,
    "Barranquilla":   0.0125 + 0.03,   # 0.0425 con S. Bomberil
    "Bogota":         0.00966 + 0.01,  # 0.01966 con S. Bomberil
    "Bucaramanga":    0.009 + 0.10,    # 0.109 con S. Bomberil
    "Cali":           0.01,
    "Cartagena":      0.008 + 0.07,    # 0.078
    "Manizales":      0.0045 + 0.05,   # 0.0545
    "Medellin":       0.01 + 0.01,     # 0.02
    # ...
}

def calcular_ica(costo_canal_mes, margen_a, cont_op, cont_com, markup, descuento, ciudad):
    ingreso_bruto = ingreso_desde_costo(costo_canal_mes, margen_a, cont_op, cont_com, markup, descuento)
    return ingreso_bruto * tasas_ica[ciudad]
```

### 6.2 GMF

```python
GMF_RATE = 0.004  # 4×1000

def calcular_gmf(facturacion_mensual):
    return facturacion_mensual * GMF_RATE
```

### 6.3 Comisión de Administración

```python
COMISION_ADM_RATE = 0.0118  # 1.18% (habilitada por defecto en Panel)

def comision_adm(ingreso_bruto):
    return ingreso_bruto * COMISION_ADM_RATE
```

### 6.4 Costo de Financiación (por período de pago)

```python
def costo_financiacion(costo_mensual, periodo_pago_dias, tasa_interes_mensual):
    """
    Se activa solo si Panel!C21 = "Sí"
    periodo_pago: 30, 45, 60, 90 días
    tasa_mensual = Panel!L10 = 0.0153
    """
    if periodo_pago_dias <= 30:
        return 0
    meses_financiacion = (periodo_pago_dias - 30) / 30
    return costo_mensual * tasa_interes_mensual * meses_financiacion
```

### 6.5 Pólizas (Cálculo)

```python
def costo_poliza(ingreso_bruto, pct_prima, pct_atribuible, meses_extension, duracion_total):
    """
    Valor prima sobre ingreso atribuible, distribuido en meses de extensión
    """
    valor_prima_anual = ingreso_bruto * pct_prima * pct_atribuible
    return valor_prima_anual / min(meses_extension, duracion_total)
```

---

## MÓDULO 7: RAMP-UP

```python
# Tabla de Rot, Ausent y Rentabilidad rows 38-43, cols 1-60+
ramp_up_table = {
    "Cobranzas":         {1: 0.85, 2: 0.92, 3: 1.0, ...todos_1_desde_3},
    "SAC":               {1: 0.85, 2: 0.92, 3: 1.0, ...},
    "Ventas Multicanal": {1: 0.85, 2: 0.92, 3: 1.0, ...},
    "SACO":              {1: 0.85, 2: 0.92, 3: 1.0, ...},
    "Plataformas":       {1: 0.0,  ...todos_0},  # no aplica
    "Captura de Datos":  {1: 0.0,  ...todos_0},  # no aplica
}

def factor_ramp_up(servicio, mes_del_contrato):
    return ramp_up_table.get(servicio, {}).get(mes_del_contrato, 1.0)
```

---

## MÓDULO 8: P&G

### 8.1 Ingreso Neto Mensual

```python
def ingreso_neto_mes(mes):
    ingreso_bruto = ingreso_a + ingreso_b + ingreso_c + ingreso_saco_ventas
    
    # Ajustes sobre ingreso bruto
    cont_operativa  = ingreso_bruto * cont_op
    cont_comercial  = ingreso_bruto * cont_com
    markup_val      = ingreso_bruto * markup
    descuento_val   = ingreso_bruto * descuento
    imprevistos_val = ingreso_bruto * imprevistos
    
    return ingreso_bruto + cont_operativa + cont_comercial + markup_val - descuento_val - imprevistos_val
```

### 8.2 Contribución

```python
def contribucion_mes(mes):
    return ingreso_neto_mes(mes) - costo_total_mes(mes)

def pct_contribucion(mes):
    return contribucion_mes(mes) / ingreso_neto_mes(mes)

def valor_total_contrato():
    return sum(ingreso_neto_mes(m) for m in range(1, duracion_meses + 1))
```

---

## MÓDULO 9: SACO/VENTAS (Modelo de Resultados)

```python
# Panel de Control General rows 118-170
def facturacion_variable_saco(mes_nivel):
    """Activo solo si servicio IN ["SACO", "Ventas Multicanal"]"""
    cantidad_asesores   = Panel!C124[mes_nivel]
    ventas_por_asesor   = Panel!C125[mes_nivel]  # TC
    ventas_seguro_p1    = Panel!C127[mes_nivel]
    ventas_seguro_p2    = Panel!C128[mes_nivel]
    ventas_seguro_p3    = Panel!C129[mes_nivel]
    comision_tc         = Panel!C133[mes_nivel]
    comision_seg_1      = Panel!C134[mes_nivel]  # 13,000
    comision_seg_2      = Panel!C135[mes_nivel]  # 15,000
    comision_seg_3      = Panel!C136[mes_nivel]  # 21,000
    
    ingreso_variable_asesor = (
        ventas_por_asesor * comision_tc
        + ventas_seguro_p1 * comision_seg_1
        + ventas_seguro_p2 * comision_seg_2
        + ventas_seguro_p3 * comision_seg_3
    )
    
    carga_prestacional = 0.42  # hardcode Panel!C139
    valor_total = ingreso_variable_asesor * (1 + carga_prestacional)
    
    aiu = Panel!C142[mes_nivel]  # AIU: 9.8%, 11.3%, 15%, 18% según nivel
    
    facturacion = valor_total * (1 + aiu) * cantidad_asesores
    return facturacion
```

---

## ANEXO WAVE 5 — Decisiones intencionales

### A. Asimetría payroll_a vs. ingreso_bruto_a respecto al ramp-up

**Observación WAVE 4 #2**: En `PyGMensual`, los campos `payroll_a` y
`no_payroll_a` se almacenan **sin** multiplicar por `factor_rampup`, mientras
que `ingreso_bruto_a` sí está escalado por ramp-up.

**Estado**: **INTENTIONAL** (diseño confirmado por contraste con Excel V2-7).

**Justificación**:
* El **costo** de nómina y no-nómina se devenga 100% desde el día 1 del
  contrato — la operación contrata todos los FTE plenos aunque el cliente
  pague solo una fracción durante el ramp-up.
* El **ingreso** se factura aplicando la curva de ramp-up porque corresponde
  al volumen real atendido durante la fase de aceleración.
* Esta asimetría es la que genera el déficit operativo característico de los
  primeros meses (`payroll_a` > `ingreso_bruto_a × factor_billing`), reflejado
  fielmente en el Excel V2-7.

**Implicación en pruebas de paridad**:
La ratio `ingreso_a / costo_a` por mes contiene el ramp-up implícito. La
suite `tests/parity/` divide la ratio por `rampup` para extraer el
`factor_billing` y validar la fórmula. Ver `tests/parity/test_parity_bancamia_golden.py`.

**Fuente Excel**: hoja "Visión P&G", filas 14–37 — los costos no se
multiplican por la columna de ramp-up; el ingreso sí.

**Conclusión**: No es bug. No se modifica el motor.
