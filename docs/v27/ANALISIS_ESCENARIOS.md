# ANÁLISIS DE ESCENARIOS COMERCIALES — V2-7

---

## 1. Estructura de Escenarios

El modelo soporta hasta **5 escenarios comerciales** simultáneos, más un **Total** consolidado (Escenario 6 = "Total").

Cada escenario representa una combinación de:
- **Modalidad**: Inbound / Outbound
- **Canal**: Voz, WhatsApp, IVR, WebChat, Mensajes, Correo, Otros, Fuerza de ventas
- **Modelo de Cobro**: Fijo, Variable, Híbrido
- **Componente Fijo**: FTE, Tiempo
- **Proporción Componente Fijo**: 0.0 → 1.0
- **Componente Variable**: Transacción, Resultados, Honorarios
- **Proporción Componente Variable**: 0.0 → 1.0

---

## 2. Escenarios en el Caso Bancamia (Ejemplo Real)

### Escenario 1
| Campo | Valor |
|-------|-------|
| Modalidad | Inbound |
| Canal | Voz |
| Modelo de Cobro | Fijo |
| Componente Fijo | FTE |
| Proporción Fija | 70% |
| Componente Variable | Transacción |
| Proporción Variable | 30% |

### Escenario 2
| Campo | Valor |
|-------|-------|
| Modalidad | Inbound |
| Canal | WhatsApp |
| Modelo de Cobro | Variable |
| Componente Fijo | FTE |
| Proporción Fija | 0% |
| Componente Variable | Transacción |
| Proporción Variable | 100% |

### Escenario 3
| Campo | Valor |
|-------|-------|
| Modalidad | Inbound |
| Canal | WhatsApp |
| Modelo de Cobro | Fijo |
| Componente Fijo | FTE |
| Proporción Fija | 100% |
| Componente Variable | — |
| Proporción Variable | 0% |

### Escenarios 4 y 5
Vacíos (sin configurar en este deal).

---

## 3. Flujo de Cálculo por Escenario

La **Hoja Maestra Escenarios** replica la lógica completa para cada escenario (5 bloques idénticos de filas):

```
Escenario 1: filas 2–48      (Facturación = C47)
Escenario 2: filas 50–96     (Facturación = C95)
Escenario 3: filas 98–144    (Facturación = C143)
Escenario 4: filas 146–192   (Facturación = C191)
Escenario 5: filas 194–243   (Facturación = C240)
Total:        filas 244–289   (Facturación = C289)
```

### Por cada escenario (bloque ejemplo: Escenario 1)

```excel
# FTE del escenario (filtrado por canal del escenario)
C13 = IF(C5="Total",
          SUM('Condiciones Cadena A'!$E$17:$S$17),
          SUMIFS('Condiciones Cadena A'!$E$17:$S$17,
                 'Condiciones Cadena A'!$E$15:$S$15, C8,    # filtro canal
                 'Condiciones Cadena A'!$E$14:$S$14, C7))   # filtro modalidad

# Costos directos por cadena (ARRAY formulas filtradas por escenario)
C17 (Payroll):   =SUMIFS(Nomina_Loaded, filtro_canal_modalidad_escenario)
C18 (No Payroll): =SUMIFS(No_payroll, filtro_canal_modalidad_escenario)
C19 (ICA):       =Polizas!ICA_filtrado_escenario
...

# Reglas de negocio del escenario (todas vienen del Panel = iguales para todos)
G6  = Panel!C67  (Contingencia Operativa)
G7  = Panel!C68  (Contingencia Comercial)
G8  = Panel!C69  (Mark up)
G9  = Panel!C70  (Descuento)
G11 = Panel!C63 + SUM(G6:G9)  (Margen efectivo Cadena A)
G12 = Panel!D63 + SUM(G6:G9)  (Margen efectivo Cadena B)
G13 = Panel!E63 + SUM(G6:G9)  (Margen efectivo Cadena C)

# Ingreso por cadena
C23 (Cadena A) = C16 / ((1-G11)*(1-G6)*(1-G7)*(1-G8)*(1+G9))
C33 (Cadena B) = C26 / ((1-G12)*(1-G6)*(1-G7)*(1-G8)*(1+G9))
C43 (Cadena C) = C36 / ((1-G11)*(1-G6)*(1-G7)*(1-G8)*(1+G9))

# Facturación total del escenario
C47 = C23 + C33 + C43
```

---

## 4. Referencia de Vision Tarifas a Escenarios

`Vision Tarifas_Modelo_Cobro` lee directamente de `Hoja Maestra Escenarios`:

```excel
# Facturación total por escenario:
C19 = 'Hoja Maestra Escenarios'!C47     # Escenario 1
D19 = 'Hoja Maestra Escenarios'!C95     # Escenario 2
E19 = 'Hoja Maestra Escenarios'!C143    # Escenario 3
F19 = 'Hoja Maestra Escenarios'!C191    # Escenario 4
G19 = 'Hoja Maestra Escenarios'!C240    # Escenario 5
H19 = 'Hoja Maestra Escenarios'!C289    # Total

# Tarifa Componente Fijo:
C20 = 'Hoja Maestra Escenarios'!G21     # Escenario 1
D20 = 'Hoja Maestra Escenarios'!G69     # Escenario 2
E20 = 'Hoja Maestra Escenarios'!G117    # Escenario 3
F20 = 'Hoja Maestra Escenarios'!G165    # Escenario 4
G20 = 'Hoja Maestra Escenarios'!G214    # Escenario 5
H20 = 'Hoja Maestra Escenarios'!G263    # Total

# Tarifa Componente Variable (depende del tipo):
C21 = IF(C16="Transacción", HME!G31,
         IF(OR(C16="Resultados", C16="Honorarios"), HME!G33, 0))
```

---

## 5. Modelo de Cobro: Lógica de Decisión

### Modelo FIJO
```python
facturacion = ingreso_cadena_a + ingreso_cadena_b
# Solo hay facturación fija. Tarifa = ingreso / FTE / meses
```

### Modelo VARIABLE
```python
facturacion = ingreso_cadena_a + ingreso_cadena_b
# Solo hay facturación variable. Tarifa = ingreso / volumen_transacciones
```

### Modelo HÍBRIDO
```python
prop_fija     = proporcion_componente_fijo    # ej: 0.70
prop_variable = proporcion_componente_variable  # ej: 0.30

ingreso_fijo     = facturacion_total × prop_fija
ingreso_variable = facturacion_total × prop_variable

tarifa_fte         = ingreso_fijo / fte_total / duracion_meses
tarifa_transaccion = ingreso_variable / volumen_transacciones
```

### Cálculo en Vision Tarifas (Escenario 1 como ejemplo):

```excel
# Ingreso Componente Fijo (G43):
G43 = C72 × D34
# C72 = Facturación Total (todos los escenarios)
# D34 = Proporción componente fijo del escenario 1

# Tarifa por FTE (G45):
G45 = IFERROR(IF(C34="FTE", G43/C37/12, G43/E126), 0)
# C34 = tipo componente fijo (FTE o Tiempo)
# C37 = FTE del escenario
# 12 = meses (hardcode aquí, usar Panel!C11)
# E126 = minutos logueados totales

# Ingreso Componente Variable (G53):
G53 = C72 × D35
# D35 = Proporción componente variable

# Tarifa por Transacción (G55):
G55 = CHOOSE(MATCH(C29, escenarios, 0),
             HME!G31, HME!G79, HME!G127, HME!G175, HME!G224)
```

---

## 6. Escenario "Total" — Consolidación

El escenario "Total" (filas 244–289 en Hoja Maestra) suma FTE de TODOS los canales/escenarios:

```excel
FTE_total = SUM('Condiciones Cadena A'!$E$17:$S$17)  # sin filtro
```

Y consolida los costos de todos los canales activos.

La facturación total (`Vision Tarifas!H19`) es la que alimenta:
- `Vision Cost To Serve!B19` (ingreso mensual)
- `Visión P&G` (ingresos por cadena)

---

## 7. Impacto del Modelo de Cobro en el Backend

El backend debe mapear los siguientes campos del `request_dto` a la lógica de escenarios:

```python
class Escenario:
    nombre: str               # "Escenario 1", ..., "Total"
    modalidad: str            # "Inbound" / "Outbound"
    canal: str                # "Voz", "WhatsApp", etc.
    modelo_cobro: str         # "Fijo", "Variable", "Híbrido"
    componente_fijo: str      # "FTE", "Tiempo"
    proporcion_fija: float    # 0.0 - 1.0
    componente_variable: str  # "Transacción", "Resultados", "Honorarios"
    proporcion_variable: float  # 0.0 - 1.0
```

Las tarifas de salida son:
```python
class TarifaEscenario:
    facturacion_total: float
    tarifa_componente_fijo: float     # COP/FTE/mes o COP/min-logueado
    tarifa_componente_variable: float # COP/transacción
    volumen_minimo: float             # si modelo variable
    ingreso_fijo: float
    ingreso_variable: float
```
