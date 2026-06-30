# ARQUITECTURA FUNCIONAL DEL MODELO NEXA — V2-7

> Blueprint completo del modelo de precios. Base para reconstruir el backend con paridad determinística.

---

## 1. Propósito del Modelo

El NEXA Pricing Simulator es una herramienta de pricing para servicios BPO (Business Process Outsourcing) que:

1. Calcula el **costo real de servir** a un cliente (Cost to Serve)
2. Determina la **tarifa comercial** aplicando márgenes sobre los costos
3. Proyecta el **P&G mensual** a 60 meses (5 años)
4. Soporta hasta **5 escenarios comerciales** simultáneos con diferentes modelos de cobro
5. Gestiona **3 cadenas de delivery** (propia, tecnología, proveedor externo)

---

## 2. Arquitectura en Capas

```
┌─────────────────────────────────────────────────────────┐
│  CAPA 0: INPUTS DEL USUARIO                              │
│  ─────────────────────────────────────────────────────── │
│  • Datos del deal: cliente, servicio, ciudad, fechas     │
│  • Volumetría: FTE/volumen por canal y modalidad         │
│  • Configuración de cadenas activas (A/B/C)              │
│  • Escenarios comerciales (hasta 5)                      │
│  • Reglas de negocio: márgenes, contingencias, markup    │
│  • Pólizas activas                                       │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 1: PARAMETRIZACIÓN (desde storage)                 │
│  ─────────────────────────────────────────────────────── │
│  • Salarios y prestaciones sociales (SMMLV, ARL, etc.)   │
│  • Ratios de staffing por cargo y perfil                 │
│  • Tasas: IPC, SMLV, factores acumulados de indexación   │
│  • ICA por municipio, GMF, comisión adm 1.18%            │
│  • Tarifas de pólizas por tipo                           │
│  • Ausentismo y rotación histórica por servicio          │
│  • Márgenes objetivo mínimos por servicio                │
│  • Tabla de ramp-up por servicio y mes                   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 2: CÁLCULO DE COSTOS LABORALES (Cadena A)          │
│  Fuente: Nomina Loaded                                    │
│  ─────────────────────────────────────────────────────── │
│  Para cada perfil operativo (FTE × ratio_staff):         │
│  • Salario fijo = costo_empresa × ratio × factor_indice  │
│  • Comisiones = salario_base × pct_comision × pct_cumpli │
│  • Capacitación inicial = días × tarifa × FTE / meses    │
│  • Capacitación rotación = días × tarifa × FTE × rot%   │
│  • Exámenes médicos = costo × (FTE/meses + FTE×rot + FTE×anual/12) │
│  • Estudios de seguridad = costo × FTE × factor          │
│  • Crucero = tarifa_crucero × FTE × factor               │
│                                                           │
│  Indexación: factor_acumulado(tipo, año) aplicado mes a mes │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 3: CÁLCULO NO PAYROLL (Infraestructura)            │
│  Fuente: No payroll                                       │
│  ─────────────────────────────────────────────────────── │
│  • OPEX Fijo = plataformas propias × factor_tec          │
│  • Inversiones/CAPEX = total / meses × (1 + tasa_int)    │
│  • Costo por estación = tarifa_puesto × FTE × pct_pres   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 4: COSTOS CADENA B (Tecnología Digital)            │
│  Fuente: Costo Fijo + Costo Variable                      │
│  ─────────────────────────────────────────────────────── │
│  Componente Fijo:                                         │
│  • OPEX B = licencias × volumen                          │
│  • Inversiones B = CAPEX / meses × (1 + tasa_int)        │
│  • S&M (Sales & Marketing)                               │
│                                                           │
│  Componente Variable:                                     │
│  • Tarifa canal = precio_sesion × volumen                 │
│  • OPEX variable = costo_var × transacciones             │
│  • Tasa escalamiento = % sobre ingresos                  │
│  • HITL = volumen_escalamientos × costo_agente           │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 5: COSTOS CADENA C (Proveedor Externo)             │
│  Fuente: Costo Cadena C                                   │
│  ─────────────────────────────────────────────────────── │
│  • Tarifa proveedor = suma costos × participación_C       │
│  • OPEX integración = fijo del proyecto                  │
│  • Inversiones integración = CAPEX diferido con interés  │
│  • Equipo integración = recursos proyecto (temporal)     │
│  • OPEX variable C = por volumen                         │
│  • Tasa escalamiento C                                   │
│  • HITL C                                                │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 6: CONSOLIDACIÓN (Costos Totales)                  │
│  Fuente: Costos Totales [HIDDEN]                          │
│  ─────────────────────────────────────────────────────── │
│  Suma Nómina + No Payroll por canal/modalidad            │
│  Visión por canal: SUMIFS(Nomina, canal) + SUMIFS(NoPay) │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 7: COSTOS FINANCIEROS                              │
│  Fuente: Pólizas - Costo Financiacion                     │
│  ─────────────────────────────────────────────────────── │
│  ICA = ingreso_bruto_canal × tasa_ica(ciudad)            │
│  GMF = facturación × 0.004                               │
│  Comisión Adm = ingreso × 0.0118 (si habilitada)         │
│  Pólizas adicionales = ingreso × prima × pct_atribuible  │
│  Financiación = costo × tasa_mensual × meses_financiados │
│                                                           │
│  Aplicación: sobre ingreso bruto (no sobre costo)        │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 8: MOTOR DE ESCENARIOS Y TARIFAS                   │
│  Fuente: Hoja Maestra Escenarios + Vision Tarifas         │
│  ─────────────────────────────────────────────────────── │
│  Por cada escenario (hasta 5):                           │
│    1. FTE filtrado por canal+modalidad del escenario     │
│    2. Costo directo A = Payroll + NoPayroll + Fin         │
│    3. Costo cadena B y C                                 │
│    4. Ingreso = costo / denominador_margenes             │
│    5. Tarifa FTE = ingreso_fijo / FTE / meses            │
│    6. Tarifa transacción = ingreso_variable / volumen    │
│    7. Volumen mínimo transaccional                       │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 9: P&G MENSUAL                                     │
│  Fuente: Visión P&G                                       │
│  ─────────────────────────────────────────────────────── │
│  Por cada mes (1..N):                                    │
│    Ingreso Bruto = (Costo_A/(1-mg_A) + Costo_B/(1-mg_B)  │
│                  + Costo_C/(1-mg_C)) × ramp_up           │
│    Ajustes: + contingencias + markup - descuento - imprev │
│    Ingreso Neto = Ingreso Bruto + ajustes                │
│    Costo Total = Costo_A + Costo_B + Costo_C + Fin       │
│    Contribución = Ingreso Neto - Costo Total             │
│    % Margen = Contribución / Ingreso Neto                │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CAPA 10: VISIONES DE SALIDA                             │
│  ─────────────────────────────────────────────────────── │
│  Vision Cost To Serve: CTS por cadena/canal/componente   │
│  Vision Tarifas: tarifa mensual por escenario            │
│  Vision P&G: estado de resultados                        │
│  Vision Imprimible: resumen ejecutivo                    │
│  KPIs: valor total contrato, margen promedio, etc.       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Fórmulas Fundamentales del Modelo

### F1 — Denominador de Pricing (THE formula)
```
ingreso = costo / ((1-margen) × (1-cont_op) × (1-cont_com) × (1-markup) × (1+descuento))
```

### F2 — Costo Laboral por Perfil
```
costo_mes = costo_empresa_cargo × ratio_staffing × factor_indexacion_mes
```

### F3 — Factor de Indexación
```
factor(tipo, mes) = tabla_acumulada[tipo][año_del_mes]
# Donde año_del_mes depende de fecha_inicio + mes_ajuste
```

### F4 — Ramp-up
```
ingreso_pyg_mes = (costo_cadena / (1 - margen_cadena)) × factor_ramp_up(servicio, mes)
```

### F5 — Tarifa FTE
```
tarifa_fte = ingreso_fijo / fte_total / meses_contrato
```

### F6 — Tarifa por Transacción
```
tarifa_tx = ingreso_variable / volumen_transacciones
```

### F7 — Tarifa por Hora Logueada
```
tarifa_hl = ingreso_fijo / minutos_logueados / meses_contrato
minutos_logueados = horas_prog × (1 - ausentismo) × (1 - pct_improductivo) × 60
```

### F8 — CTS Ponderado
```
cts_ponderado = cts_a × part_a + cts_b × part_b + cts_c × part_c
part_x = vol_cadena_x / vol_total
```

---

## 4. Invariantes del Modelo

1. **Suma de participaciones = 1**: `part_a + part_b + part_c = 1.0`
2. **Duracion es consistente**: todas las hojas usan `Panel!C11` para truncar a N meses
3. **Cadena inactiva = 0 en costo y en tarifa**: `IF(cadena_activa, calcular, 0)`
4. **Margen nunca > 1**: si margen ≥ 1, el denominador es ≤ 0 → división por cero
5. **Factor indexación año 1 = 1.0**: el primer año no tiene ajuste
6. **Ramp-up para servicios sin tabla = 1.0** (o 0.0 para Plataformas/Captura)

---

## 5. Parámetros de Entrada Mínimos para un Deal Válido

```python
# Obligatorios
servicio: str                   # define márgenes, ausentismo, rotación default
ciudad: str                     # define tasa ICA
fecha_inicio: date              # define año base para indexación
meses_contrato: int             # duración proyección
ftes: Dict[str, int]            # {canal: fte} al menos un canal activo

# Con defaults razonables
margen: float = margen_objetivo_servicio  # desde parametrización
ausentismo: float = ausentismo_servicio   # desde parametrización
rotacion: float = rotacion_servicio       # desde parametrización
indexacion_humano: str = "IPC"
indexacion_tecno: str = "IPC"
```

---

## 6. Diagrama de Flujo de Datos Simplificado

```
Usuario configura Panel → Condiciones A/B/C
         │
         ├── Nómina Loaded (60 meses × perfiles)
         │       └── factor_indexacion × costo_empresa × ratio
         │
         ├── No Payroll (60 meses)
         │       └── OPEX_fijo × factor_tec + CAPEX/meses×(1+i) + estacion×FTE
         │
         ├── Costo Fijo B + Costo Variable B (60 meses)
         │
         ├── Costo Cadena C (60 meses)
         │
         └── Costos Totales (consolidado)
                 │
                 └── Pólizas/ICA/GMF/Financiación
                         │
                         └── Hoja Maestra Escenarios (por canal+modalidad)
                                 │
                                 ├── Vision Tarifas → tarifas por escenario
                                 │
                                 ├── Vision Cost To Serve → CTS por cadena
                                 │
                                 └── Visión P&G → P&G mensual + KPIs
```
