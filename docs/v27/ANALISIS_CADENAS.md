# ANÁLISIS INDIVIDUAL POR CADENA A / B / C — V2-7

---

## CADENA A — Operación Directa (Recurso Humano Propio)

### Definición
Cadena A representa la operación directa de Nexa/ABPS: personal propio, instalaciones propias, costos laborales completos.

### Activación
`Panel de Control General!M17 = TRUE` (Inbound) o `Panel!M30 = TRUE` (Outbound)

### Modelo de Cobro Cadena A
Componente FIJO únicamente. Las opciones son:
- **FTE**: tarifa por agente-mes
- **Tiempo**: tarifa por hora logueada o minuto pagado

### Estructura de Costos Cadena A

```
Costo Directo Cadena A = Payroll + No Payroll + ICA + GMF + Pólizas + Costos Financiación
```

#### A.1 Payroll (Nomina Loaded)
Sub-componentes:
1. **Salario Fijo** — costo base mensual por FTE × ratio staffing × indexación
2. **Salario Variable (Comisiones)** — comisiones por perfil operativo
3. **Capacitación Inicial** — costo de formación al inicio del contrato
4. **Capacitación Rotación** — costo recurrente de reemplazar personal rotado
5. **Exámenes Médicos** — costo por ingreso de nuevo personal
6. **Estudios de Seguridad** — costos de seguridad al ingresar
7. **Crucero** — beneficio de transporte del personal

Formulas clave de Nomina Loaded:
```excel
# Total Inbound mes 1:
D15 = D93+D238+D287+D349+D407+D182+D455

# Indexación mensual (fila 100 ejemplo):
D100 = IF(D14<=fin_contrato,
          costo_base × ratio × factor_indice_mes,
          0)
```

#### A.2 No Payroll
Sub-componentes:
1. **OPEX Fijo** (plataformas tecnológicas propias, licencias)
2. **Inversiones/CAPEX** (equipos, infraestructura diferida con interés)
3. **Costos Fijos por Estación** (arriendo virtual, utilities, puesto de trabajo)

Fórmula CAPEX diferido:
```excel
cuota_mensual = (valor_total / meses_diferir) * (1 + tasa_interes_mensual)
# tasa = Panel!L10 = 0.0153 mensual
```

#### A.3 Estructura del Equipo (Perfiles)

| Cargo | Tipo | Ratio típico | Se activa con |
|-------|------|--------------|---------------|
| Director de cuentas | Staff Senior | Configurable | C25=TRUE |
| Director de Performance | Staff Senior | Configurable | C26=TRUE |
| Jefe Comercial Regional | Staff Medio | Configurable | C27=FALSE |
| Analista profesional AFAC | Staff | Configurable | C28=FALSE |
| Lider de Entrenamiento | Operativo | Configurable | — |
| Coordinador de Turno | Operativo | Configurable | — |
| Analista QA | Staff | Configurable | — |
| Agente operativo | Directo | 1:1 con FTE | — |

Los ratios de staffing se leen de `Inputs de Nomina!C110:H133` por perfil de canal.

#### A.4 Fórmula de Tarifa Cadena A

**Si Componente Fijo = FTE:**
```python
tarifa_fte = ingreso_componente_fijo / fte_total / duracion_meses
# Unidad: COP por FTE por mes
```

**Si Componente Fijo = Tiempo:**
```python
tarifa_hora_logueada = ingreso_fijo / minutos_logueados_totales / duracion_meses
# Unidad: COP por minuto logueado

# Minutos logueados = horas programadas × (1 - ausentismo) × (1 - factor_deslogueos - breaks - cap)
```

**Minutos logueados (cálculo detallado):**
```python
horas_semanales = 42
semanas_mes     = 4.33
horas_prog      = horas_semanales * semanas_mes * fte_total

# Deducciones diarias (en minutos):
breaks          = 30   # 2 breaks de 15 min
capacitacion    = ((8/4)/6) * 60  # horas formación mensual / 4 semanas / 6 días
deslogueos      = 5
coaching        = 5
pausa_activa    = 5

pct_improductivo = (breaks + capacitacion + deslogueos) / ((42/6) * 60)
pct_productivo   = 1 - pct_improductivo - (coaching + pausa_activa) / ((42/6) * 60)

horas_logueadas  = horas_prog * (1 - ausentismo) * (1 - pct_deslogueos_breaks_cap)
minutos_logueados = horas_logueadas * 60
```

---

## CADENA B — Tecnología / OPEX Digital

### Definición
Cadena B es la componente de tecnología, plataformas digitales y costos variables de los canales digitales (WhatsApp, WebChat, IVR, etc.). Puede tener componente fijo (OPEX/inversiones) y variable (por transacción).

### Activación
`Panel de Control General!N17 = TRUE` (Inbound) o `Panel!N30 = TRUE` (Outbound)

### Modelo de Cobro Cadena B
Tiene COMPONENTE FIJO y COMPONENTE VARIABLE independientes.
- Fijo: OPEX mensual de plataformas/licencias
- Variable: por transacción (WhatsApp, mensajes, etc.)

### Estructura de Costos Cadena B

```
Costo Cadena B = Componente Fijo (OPEX + Inversiones + S&M) + Componente Variable (Tarifa + OPEX var + Escalamiento + HITL)
```

#### B.1 Componente Fijo

Fuente: `Costo Fijo` + `Condiciones Cadena B`

- **OPEX Fijo**: plataformas licencias (ej: sesión WhatsApp = 183 COP/sesión)
- **Inversiones**: CAPEX diferido con interés (misma fórmula que Cadena A)
- **S&M**: Sales & Marketing

Fórmula OPEX:
```excel
# Condiciones Cadena B!J8:
=IF(F8="Total", H8, H8*I8)
# Donde H8=precio unitario, I8=cantidad (ej: volumetría de Panel)
# F8="Unitario" → precio × cantidad
# F8="Total"   → precio ya es total
```

#### B.2 Componente Variable

Fuente: `Costo Variable` (HIDDEN)

- **Tarifa Canal**: precio por interacción por canal
- **OPEX Variable**: costos variables de operación
- **Tasa de Escalamiento**: comisiones o bonos por rendimiento
- **HITL** (Human-in-the-Loop): costo del agente humano que interviene en flujos digitales

#### B.3 Tarifas Cadena B

```python
# Tarifa por Transacción:
tarifa_transaccion_b = (costo_total_cadenas × prop_variable_b) / volumen_total_transacciones

# Volumen Mínimo Transaccional:
volumen_minimo = (costo_A + costo_B + costo_C) × prop_variable / tarifa_transaccion

# Ingreso por persona (si modelo = Honorarios/Resultados):
ingreso_persona = (ingreso_fijo + ingreso_variable) / n_personas / duracion_meses
```

---

## CADENA C — Proveedor Externo / BPO Tercero

### Definición
Cadena C representa el costo de un proveedor externo de BPO. NEXA actúa como intermediario, cobrando margen sobre los costos del proveedor.

### Activación
`Panel de Control General!O17 = TRUE` (Inbound) o `Panel!O30 = TRUE` (Outbound)

### Modelo de Cobro Cadena C
Solo componente variable (por volumen) dado que es un proveedor externo.

### Estructura de Costos Cadena C

```
Costo Cadena C = Tarifa Proveedor + Costo Integración + Costo Variable
```

#### C.1 Tarifa Proveedor

```excel
# Vision Cost To Serve!K35:
=IFERROR(SUM('Costo Cadena C'!$F$115:$BM$115) / 'Panel de Control General'!$C$11 / 'Panel de Control General'!$O$52, 0)
```
- Suma los 60 meses de tarifa del proveedor
- Divide por duración (para obtener promedio mensual)
- Divide por participación de Cadena C en el total de FTE/volumetría

#### C.2 Costo de Integración

Sub-componentes (por canal Inbound/Outbound):
- **OPEX Fijo** (infraestructura de integración)
- **Inversiones** (CAPEX diferido)
- **Equipo de Integración** (personal de proyecto)

#### C.3 Costo Variable Cadena C

Sub-componentes:
- **Tasa de Escalamiento** (C!H405, C!H417)
- **OPEX Variable** (C!E197, C!E224)
- **HITL** (C!F444, C!F457)

#### C.4 Tarifa Cadena C en Vision Tarifas

Cadena C usa el **margen de Cadena A** (G35) como base de pricing:
```excel
# Vision Tarifas!C67:
=C60/((1-$G$35)*(1-$G$30)*(1-$G$31)*(1-$G$32)*(1+$G$33))
```
Esto significa que Cadena C tiene el mismo margen objetivo que Cadena A (no el 20% de margen_c que está en Panel!E63). Panel!E63 se usa en P&G, no en Vision Tarifas.

**INCONSISTENCIA DETECTADA**: Vision Tarifas usa margen_A para Cadena C, pero Visión P&G usa margen_C para Cadena C. Son dos vistas diferentes del mismo deal.

---

## Comparativa de Cadenas

| Atributo | Cadena A | Cadena B | Cadena C |
|----------|----------|----------|----------|
| Tipo | Operación propia | Tecnología/Digital | Proveedor externo |
| Componente fijo | Sí (FTE o Tiempo) | Sí (OPEX/Inversiones) | No (solo variable) |
| Componente variable | No | Sí (por transacción) | Sí (volumetría) |
| Margen en Vision Tarifas | Panel!C63 | Panel!D63 | Panel!C63 (igual que A) |
| Margen en P&G | Panel!C63 | Panel!D63 | Panel!E63 |
| Activación | Panel!M17/M30 | Panel!N17/N30 | Panel!O17/O30 |
| Hoja de costos principal | Nomina Loaded + No payroll | Costo Fijo + Costo Variable | Costo Cadena C |
| Indexación humana | Sí (SMMLV/IPC) | No | No |
| Indexación tecnológica | Sí | Sí | No |
| Afecta FTE en tarifas | Sí (base de tarifa FTE) | No | No |
| Pólizas | Sí | Sí (Aplica Pólizas = FALSE en default) | No |

---

## CTS Ponderado (Participación de Cadenas)

```excel
# Vision Cost To Serve!G49:
=(C34×C31) + (G34×G31) + (K34×K31)

# C31 = Panel!$M$53 = M52/L52 = FTE_cadena_A/FTE_total
# G31 = Panel!$N$53 = N52/L52 = FTE_cadena_B/FTE_total
# K31 = Panel!$O$53 = O52/L52 = FTE_cadena_C/FTE_total
```

Participación calculada desde volumetría (sumas de canales por cadena).
