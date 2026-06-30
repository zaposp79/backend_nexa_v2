# Ingeniería Inversa — Excel V2-5 vs Implementación Backend

**Fecha:** 2026-05-25  
**Excel:** `Nexa - Pricing - Simulador - V2-5.xlsx`  
**Metodología:** Trazabilidad inversa: Visión → Fórmula → Hoja origen → Parámetro  
**Fuente de verdad:** Excel es la única fuente de verdad funcional.

---

## 0. Estructura del Excel V2-5

| # | Hoja | Rol |
|---|------|-----|
| 0 | Riesgo | Clasificación de riesgo del deal → alimenta rangos de contingencias |
| 1 | Listas Desplegables | Catálogos maestros (servicios, ciudades, tipos) |
| 2 | Graficos | Solo visualización |
| 3 | Tasas, TRM, Polizas | Parámetros: GMF, TRM, tasas de pólizas |
| 4 | Rot, Ausent y Rentabilidad | Tabla de ramp-up por línea de negocio y mes del contrato |
| 5 | Inputs de Nomina | Tabla maestra de salarios y ratios de soporte |
| 6 | Nomina Loaded | **Calculadora** payroll mensual por perfil (60 meses) |
| 7 | No payroll | **Calculadora** OPEX/capex/costos fijos por perfil (60 meses) |
| 8 | Costo Fijo | **Calculadora** costos fijos Cadena B (60 meses) |
| 9 | Costo Variable | **Calculadora** costos variables Cadena B (60 meses) |
| 10 | Costo Cadena C | **Calculadora** todos los costos Cadena C (60 meses) |
| 11 | Costos Totales | Agregador: suma de todas las cadenas por mes/canal |
| 12 | Pólizas - Costo Financiacion | **Calculadora** ICA, GMF, pólizas, costos de financiación (60 meses) |
| 13 | Panel de Control General | **Inputs principales** del deal + reglas de negocio |
| 14 | Condiciones Cadena A | **Parametrización** perfiles/FTE/salarios Cadena A |
| 15 | Condiciones Cadena B | **Parametrización** canales/volúmenes/costos Cadena B |
| 16 | Condiciones Cadena C | **Parametrización** proveedores/costos Cadena C |
| 17 | Visiones | Índice de visiones |
| 18 | Visión Imprimible | **OUTPUT** Resumen ejecutivo del deal |
| 19 | Vision Cost To Serve | **OUTPUT** Costo por unidad operativa |
| 20 | Hoja Maestra Escenarios | **INTERMEDIARIA** Cálculo por escenario comercial (1-5) |
| 21 | Vision Tarifas_Modelo_Cobro | **OUTPUT** Tarifas por canal/escenario |
| 22 | Visión P&G | **OUTPUT** Estado de resultados mensual (60 meses) |

---

## 1. Mapa de Visiones — Ingeniería Inversa Completa

### 1.1 Visión P&G (Hoja 22)

**Estructura:** Filas = conceptos contables / Columnas C..BJ = mes 1..60

#### Header (filas 5-6) — Metadatos del deal

| Campo | Celda | Fórmula / Origen |
|-------|-------|-----------------|
| Cliente | C5 | `IF(Panel!C7="Cliente Nuevo", Panel!D6, Panel!C6)` |
| Tipo de Cliente | E5 | `Panel!C8` |
| Línea de Negocio | G5 | `Panel!C5` |
| Periodo de Pago | I5 | `Pólizas!D363` |
| Duración (fechas) | C6 | `TEXT(Panel!C10,...) & TEXT(EDATE(...))` |
| Duración en Meses | E6 | `Panel!C11` |
| Servicio | G6 | `IF(OR(G5="SACO",G5="Plataformas"),"Fuerza de Ventas","Call Center")` |

#### Cabecera de meses (filas 11-15)

| Fila | Concepto | Fórmula (mes n = columna col) |
|------|----------|-------------------------------|
| 12 | Número de mes absoluto (1..60) | `1, 1+C12, 1+D12, ...` secuencia |
| 11 | Número de mes del contrato | `IF(col12>=MATCH(Panel!C10, C13:BJ13, 0), col12-MATCH(...)+1, "")` |
| 13 | Fecha del mes | `C13=Panel!C10`, `EDATE(prev, 1)` — 60 meses |
| 14 | Estaciones de Trabajo | `SUM('Condiciones Cadena A'!E19:S19)` — fijo todos los meses |
| 15 | Ramp-up | `IFERROR(INDEX('Rot, Ausent y Rentabilidad'!B38:BI43, MATCH(Panel!C5,...), MATCH(col11,...)), "")` |

> **Ramp-up:** Lookup bidimensional: Línea de Negocio (Panel!C5) × Mes del contrato (col11).
> Origen: `'Rot, Ausent y Rentabilidad'!B38:BI43`.

#### Sección Ingresos (filas 17-27)

| Fila | Concepto | Fórmula exacta |
|------|----------|----------------|
| 18 | **Ingreso Bruto** | `C19 + C20 + C21 + C71` |
| 19 | Ingreso Cadena A | `IF(col12<=E6, C31*(1+Panel!C63)*C15, 0)` |
| 20 | Ingreso Cadena B | `IF(col12<=E6, C45*(1+Panel!C63)*C15, 0)` |
| 21 | Ingreso Cadena C | `IF(col12<=E6, C55*(1+Panel!C63)*C15, 0)` |
| 71 | (placeholder vacío) | vacío / 0 — reservado |
| 22 | Contingencia Operativa | `IF(col12<=E6, Panel!C67 * col18, 0)` |
| 23 | Contingencia Comercial | `IF(col12<=E6, Panel!C68 * col18, 0)` |
| 24 | Mark-Up | `IF(col12<=E6, Panel!C69 * col18, 0)` |
| 25 | Descuento | `IF(col12<=E6, Panel!C70 * col18, 0)` |
| 26 | **Imprevistos** ⚠ NUEVO | `IF(col12<=E6, Panel!C73 * col18, 0)` |
| 27 | **Ingreso Neto** | `col18 + SUM(col22:col24) - col25 - col26` |

> **Fórmula Ingreso Neto en V2-5:**
> ```
> Ingreso_Neto = Ingreso_Bruto + ContOp + ContCom + MarkUp - Descuento - Imprevistos
> ```

#### Sección Costos (filas 29-64)

```
C30 Costo Total = C31 + C45 + C55
│
├── C31 Costos Cadena A = C32 + C41
│   ├── C32 Payroll = SUM(C34:C40)
│   │   ├── C33 Nomina Loaded = C34 + C35
│   │   │   ├── C34 Salario Fijo         ← ARRAY from 'Nomina Loaded'!G$178
│   │   │   └── C35 Salario Variable     ← 'Nomina Loaded'!G$179
│   │   ├── C36 Capacitación Inicial     ← ARRAY from 'Nomina Loaded'
│   │   ├── C37 Capacitación Rotación    ← ARRAY from 'Nomina Loaded'
│   │   ├── C38 Exámenes Médicos         ← ARRAY from 'Nomina Loaded'
│   │   ├── C39 Estudios de Seguridad    ← ARRAY from 'Nomina Loaded'
│   │   └── C40 Crucero                  ← ARRAY from 'Nomina Loaded'
│   └── C41 No Payroll = SUM(C42:C44)
│       ├── C42 OPEX Fijo               ← ARRAY from 'No payroll'
│       ├── C43 Inversiones             ← ARRAY from 'No payroll'
│       └── C44 Costos Fijos            ← ARRAY from 'No payroll'
│
├── C45 Costos Cadena B = C46 + C50
│   ├── C46 Componente Fijo = SUM(C47:C49)
│   │   ├── C47 OPEX Fijo               ← ARRAY from 'Costo Fijo'
│   │   ├── C48 Inversiones             ← ARRAY from 'Costo Fijo'
│   │   └── C49 S&M                     ← ARRAY from 'Costo Fijo'
│   └── C50 Componente Variable = SUM(C51:C54)
│       ├── C51 Tarifa Canal            ← ARRAY from 'Costo Variable'
│       ├── C52 OPEX Variable           ← ARRAY from 'Costo Variable'
│       ├── C53 Tasa de Escalamiento    ← ARRAY from 'Costo Variable'
│       └── C54 HITL                    ← ARRAY from 'Costo Variable'
│
└── C55 Costos Cadena C = C56 + C57 + C61
    ├── C56 Tarifa Proveedor            ← ARRAY from 'Costo Cadena C'!F115:BM115
    ├── C57 Costo Integración = SUM(C58:C60)
    │   ├── C58 OPEX Fijo               ← ARRAY 'Costo Cadena C'!E143:BL143
    │   ├── C59 Inversiones             ← ARRAY 'Costo Cadena C'!D290:BK290
    │   └── C60 Equipo de Integración   ← ARRAY 'Costo Cadena C'!F339:F357 (B="Activado")
    └── C61 Costo Variable = SUM(C62:C64)
        ├── C62 Tasa de Escalamiento    ← ARRAY 'Costo Cadena C'!H398:H416 (B="Activado")
        ├── C63 OPEX Variable           ← ARRAY 'Costo Cadena C'!E190:E196 (B="Activo") + E215:E222 (B="Activado")
        └── C64 HITL                    ← ARRAY 'Costo Cadena C'!F437:F457 (B="Activado")
```

#### Componente Financiero (filas 65-70) — INFORMACIONAL, NO en Costo Total

| Fila | Concepto | Origen |
|------|----------|--------|
| 65 | **Componente Financiero** | `SUM(C66:C70)` |
| 66 | ICA | `ARRAY SUMPRODUCT('Pólizas'!E12:E83 * (B12:B83="Activado"))` |
| 67 | GMF | `ARRAY SUMPRODUCT('Pólizas'!E93:E163 * (B93:B163="Activado"))` |
| 68 | **Comisión de Administración (1.18%)** ⚠ NUEVO | `ARRAY SUMPRODUCT('Pólizas'!E222:E240 (="Activado")) + SUMPRODUCT('Pólizas'!E280:E298 (="Activado"))` |
| 69 | Pólizas adicionales | `ARRAY SUMPRODUCT('Pólizas'!E12:E163 (="Activado")) + SUMPRODUCT('Pólizas'!E197:E326 (="Activado"))` |
| 70 | Costos Financieros | `ARRAY SUMPRODUCT('Pólizas'!E377:E455 * (B377:B455="Activado"))` |

> ⚠ **Nota arquitectónica crítica:** El Componente Financiero (C65) NO está incluido en el Costo Total (C30). El P&G V2-5 muestra el componente financiero como información separada. Los costos financieros son recuperados en el ingreso a través de la Visión Tarifas (donde se incluyen en el numerador del costo antes de aplicar el factor de margen).

#### Sección Utilidad (filas 73-80)

| Fila | Concepto | Fórmula |
|------|----------|---------|
| 74 | **Contribución** | `Ingreso_Neto - Costo_Total` → `col27 - col30` |
| 75 | Contribución por Puesto | `col74 / col14` (÷ Estaciones de Trabajo) |
| 76 | % Contribución | `col74 / col27` |
| 78 | Costo Fijo | **Hardcoded 0** en V2-5 |
| 79 | **Utilidad Neta** | `col27 - col30 - col78` = `Ingreso_Neto - Costo_Total` |
| 80 | % Utilidad Neta | `col79 / col27` |

---

### 1.2 Vision Tarifas_Modelo_Cobro (Hoja 21)

**Estructura:** Cálculo por Escenario (1-5) usando FILTER() desde Panel de Control.

#### Fuentes de datos (Panel de Control A81:B113)

```
Panel!A81:A113 = Identificador de Escenario ("Escenario 1", "Escenario 2", ...)
Panel!B81:B113 = Campo de configuración ("Modalidad", "Canal", "Modelo de Cobro", 
                  "Componente Fijo", "Componente Variable")
Panel!C81:C113 = Valor del campo (Inbound/Outbound, Voz/WhatsApp, Fijo/Híbrido, FTE/Tiempo, ...)
Panel!D81:D113 = Proporción (pct_fijo para componente fijo, pct_variable para variable)
```

#### Reglas de Negocio (columna G, bloque derecho)

| Campo | Celda | Valor |
|-------|-------|-------|
| Contingencia Operativa | G30 | `Panel!C67` (0.02) |
| Contingencia Comercial | G31 | `Panel!C68` (0) |
| Mark up | G32 | `Panel!C69` (0) |
| Descuento volumen | G33 | `Panel!C70` (0) |
| Margen | G35 | `Panel!C63` (0.18) |
| **Factor acumulado** | G29 | `SUM(G30:G32) + G35 - G33` |

#### Estructura de costos por Escenario (columna C = Escenario 1)

```
C40 CADENA A = SUM(C41:C46)
├── C41 Payroll          ← FILTER(Panel!M17:M37, Escenario+Modalidad+Canal) × FTE_activo
├── C42 No Payroll       ← FILTER(Panel!M17:M37, ...) — no payroll por canal
├── C43 ICA              ← FILTER para ICA por canal
├── C44 GMF              ← FILTER para GMF por canal
├── C45 Pólizas          ← FILTER para pólizas por canal (si A54=TRUE)
└── C46 Costos financiación ← FILTER costos financieros por canal

C50 CADENA B = SUM(C51:C56)
├── C51 Comp. Fijo
├── C52 Comp. Variable
├── C53 ICA, C54 GMF
├── C55 Pólizas (si A55=TRUE)
└── C56 Costos financiación

C60 CADENA C = SUM(C61:C66)
├── C61 Comp. Fijo, C62 Comp. Variable
├── C63 ICA, C64 GMF
├── C65 Pólizas (si A65=TRUE)
└── C66 Costos financiación
```

#### Fórmulas de Ingreso — ⚠ DIFERENCIA CRÍTICA CON BACKEND

**Excel (Hoja Maestra Escenarios, fila 23 y Vision Tarifas fila 47):**
```
Ingreso_A = Costo_A / ((1 - margen) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento))
Ingreso_B = Costo_B / ((1 - margen) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento))
Ingreso_C = Costo_C / ((1 - margen) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento))
Facturación = Ingreso_A + Ingreso_B + Ingreso_C   [C47 en Hoja Maestra]
```

**Backend actual (`vision_tarifas.py`, método `_factor_billing`):**
```python
f = (1.0 - p.margen) * (1.0 - p.op_cont)
if p.com_cont > 0:
    f *= (1.0 - p.com_cont)
# FALTA: × (1 - markup) × (1 + descuento)
```

> **GAP-VT-1 CRÍTICO:** El factor de billing del backend no incluye `markup` ni `descuento` en el denominador.
> La fórmula correcta es:
> ```python
> factor = (1 - margen) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento)
> ```

#### Tarifas por componente (columna G, Hoja Maestra Escenarios)

| Celda | Concepto | Fórmula |
|-------|----------|---------|
| G19 | Ingreso Componente Fijo | `C47 × D10` (Facturación × pct_fijo) |
| G21 | Tarifa por FTE / hora logueada | `IF(C10="FTE", G19/FTE, G19/horas_logueadas)` |
| G23 | Tarifa por hora pagada | `IF(C10="Tiempo", G19/horas_pagadas, 0)` |
| G29 | Ingreso Componente Variable | `C47 × D11` (Facturación × pct_variable) |
| G31 | Tarifa por Transacción | `G29 / volumen_canal` |
| G33 | Volumen Mínimo Transacción | `(CostoTotal × pct_var) / tarifa_transaccion` |

#### Resumen por Escenario (filas 10-21, columnas C-H)

| Fila | Campo | Origen |
|------|-------|--------|
| B19 | Facturación [Directo] | `='Hoja Maestra Escenarios'!C47` (Escenario 1) |
| B20 | Tarifa Componente Fijo | `='Hoja Maestra Escenarios'!G21` |
| B21 | Tarifa Componente Variable | `IF(comp_var="Transacción", G31, IF(OR(="Resultados",="Honorarios"), G33, 0))` |
| C72 | **Facturación Total** | `C47 + C57 + C67` (suma Ingreso A+B+C) |

---

### 1.3 Vision Cost To Serve (Hoja 19)

#### Economics del Deal (filas 18-20)

| Celda | Concepto | Fórmula |
|-------|----------|---------|
| B19 | **Ingreso Mensual** | `='Vision Tarifas_Modelo_Cobro'!C72` |
| H19 | **Cost To Serve Mensual** | `='Visión P&G'!BK30 / 'Visión P&G'!E6` → CostoTotal_mes60 / meses |
| N19 | Margen del Deal | `='Panel de Control General'!C63` |
| N20 | Semáforo de Margen | `IFS(N19<mín, "⚠ Bajo", N19>máx, "✓ Excede", TRUE, "✓ OK")` |

> ⚠ **H19:** El CTS mensual se calcula como `CostoTotal_acumulado(hasta mes60) / meses_contrato`, usando la celda BK30 de la Visión P&G (columna del mes 60). **No es el promedio de todos los meses**, es el valor del último mes dividido por el contrato. Esto es diferente al promedio que calcula el backend.

#### Desglose Cadena A (filas 35-48)

| Celda | Sub-componente | Origen |
|-------|----------------|--------|
| C37 | Salario Fijo | `SUM(IF(M15=TRUE,'Nomina Loaded'!D100:BK100,0),IF(M28=TRUE,...)) / meses / M50` |
| C38 | Salario Variable | `SUM(IF(M15=TRUE,'Nomina Loaded'!D189:BK189,0),...) / meses / M50` |
| C39 | Capacitación Inicial | `SUM(IF(M15=TRUE,'Nomina Loaded'!D245:BK245,0),...) / meses / M50` |
| C40 | Capacitación Rotación | `SUM(IF(M15=TRUE,'Nomina Loaded'!D294:BK294,0),...) / meses / M50` |
| C41 | Exámenes Médicos | `SUM(IF(M15=TRUE,'Nomina Loaded'!D356:BK356,0),...) / meses / M50` |
| C42 | Estudios de Seguridad | `SUM(IF(M15=TRUE,'Nomina Loaded'!D414:BK414,0),...) / meses / M50` |
| C43 | Crucero | `SUM(IF(M15=TRUE,'Nomina Loaded'!D462:BK462,0),...) / meses / M50` |
| C46 | OPEX Fijo | `SUM(IF(M15=TRUE,'No payroll'!D114:BK114,0),...) / meses / M50` |
| C47 | Inversiones | `SUM(IF(M15=TRUE,'No payroll'!D193:BK193,0),...) / meses / M50` |
| C48 | Costos Fijos x Estación | `SUM(IF(M15=TRUE,'No payroll'!D255:BK255,0),...) / meses / M50` |

> **Denominador M50:** `SUM(M42:M49)` = volumen total ponderado de todos los canales.

#### Denominadores K50 / L50 (participaciones)

| Participación | Celda | Fórmula |
|---------------|-------|---------|
| Cadena A | C31 | `='Panel de Control General'!M51` → `M50/L50` (vol Cad A / vol total) |
| Cadena B | G31 | `='Panel de Control General'!N51` |
| Cadena C | K31 | `='Panel de Control General'!O51` |

#### CTS Ponderado

```
CTS_Ponderado = (CTS_A × participación_A) + (CTS_B × participación_B) + (CTS_C × participación_C)
```
Celda G49: `=(C34*C31) + (G34*G31) + (K34*K31)`

> ⚠ **GAP-CTS-1:** El backend solo considera Cadenas A y B en el CTS ponderado. V2-5 incluye Cadena C.

#### Desglose por Canal (filas 62-83)

```
Para cada canal (WhatsApp, Correo, WebChat, Mensajes, Voz, IVR, Otros):
  E64 = IF(M15=TRUE & FILTER(...canal...)<>0,
           SUMPRODUCT('Costos Totales'!..., filtro_canal),
           0)
  CTS_canal = SUMPRODUCT(Costos_Totales × canal) / total_vol
```

---

### 1.4 Visión Imprimible (Hoja 18)

La Visión Imprimible es **composición pura** — no calcula nada nuevo:

| Sección | Origen |
|---------|--------|
| FICHA DEL DEAL (01) | Directo de Panel de Control General |
| ECONOMICS (02) — Ingreso Mensual | `='Vision Tarifas_Modelo_Cobro'!C72` |
| ECONOMICS (02) — CTS Mensual | `='Visión P&G'!BK30/'Visión P&G'!E6` |
| ECONOMICS (02) — Margen | `='Panel de Control General'!C63` |
| CONFIGURACIÓN COMERCIAL (03) | Desde Vision Tarifas (C33, C34, G47, G55) |
| ANÁLISIS GRÁFICO (04) | Desde Visión P&G (datos mensuales) |
| COMPARATIVO ESCENARIOS (05) | Desde Panel de Control (B80:D113) |

---

## 2. Parámetros de Entrada — Panel de Control General

### 2.1 Datos del Deal

| Campo | Celda | Tipo | Alimenta |
|-------|-------|------|---------|
| Servicio / Línea de Negocio | C5 | Lista | Ramp-up, CTS tipo, clasificación |
| Nombre de cliente | C6 / D6 | Texto | Metadatos visiones |
| Antigüedad | C7 | Derivado | Metadatos |
| Tipo de cliente | C8 | Lista | Metadatos |
| Periodo de pago | C9 | Número (días) | Costo financiación, facturación |
| Fecha Inicio | C10 | Fecha | Meses del contrato, fechas |
| Duración meses | C11 | Número (1-60) | Límite iteración mensual |
| Ciudad | C12 | Lista | Sede, parámetros ciudad |
| Sede | C13 | Lista | Costos sitio |

### 2.2 Volumetría por Canal

| Cadenas | Rango | Descripción |
|---------|-------|-------------|
| Inbound (Cad A activa=M15) | K17:L23 | Volumen total por canal inbound |
| Outbound (Cad A activa=M28) | K30:L37 | FTE por canal outbound |
| Cadena B | N col | Volumen transacciones automatización |
| Cadena C | O col | Volumen proveedores |

### 2.3 Reglas de Negocio (filas 60-75)

| Campo | Celda | Valor actual | Rango válido |
|-------|-------|-------------|-------------|
| Margen objetivo | C63 | 0.18 | — |
| Contingencia Operativa | C67 | 0.02 | [D67, E67] desde Riesgo |
| Contingencia Comercial | C68 | 0.00 | [D68, E68] desde Riesgo |
| Mark up | C69 | 0.00 | [0.02, 0.08] |
| Descuento volumen | C70 | 0.00 | [0.00, 0.08] |
| **Imprevistos** ⚠ NUEVO | C73 | 0.00 | — |
| Porcentaje acumulado | C75 | `=SUM(C67:C69)-C70` | [0.12, 0.15] |

### 2.4 Escenarios Comerciales (filas 81-113)

```
Columnas: A=Escenario, B=Campo, C=Valor, D=Proporción

Escenario 1: Inbound - Voz - Fijo (Tiempo × 1.0)
Escenario 2: Inbound - WhatsApp - Fijo (FTE × 1.0, Transacción × 0)
Escenario 3: Inbound - WebChat - Híbrido (FTE × 0.7, Transacción × 0.3)
Escenario 4: vacío
Escenario 5: vacío
Total:       Columna H con configuración del deal completo
```

### 2.5 Parámetros Operativos

| Campo | Celda | Valor actual |
|-------|-------|-------------|
| Tarifa diaria capacitación | C16 | 20,000 |
| Crucero | C17 | `=8000*(1+5.27%)` |
| Horas de formación mensual | C18 | 8 |
| % Ausentismo | C19 | 0.065 |
| % Rotación | C20 | 0.085 |
| Se considera financiación | C21 | Si |
| ICA | C34 | 0.01 |
| GMF | C35 | `FILTER('Tasas, TRM, Polizas'!B22:B32, ...)` |

---

## 3. Árbol de Dependencias — Cadena Completa

```
Panel de Control General (inputs usuario)
│
├── Condiciones Cadena A (perfiles/FTE/salarios)
│   └── Inputs de Nomina (tabla maestra salarios)
│       └── Nomina Loaded (payroll mensual × 60 meses)
│           └── No payroll (OPEX/capex/CF × 60 meses)
│
├── Condiciones Cadena B (canales/volúmenes/costos)
│   ├── Costo Fijo (OPEX fijo Cadena B × 60 meses)
│   └── Costo Variable (tarifa canal/OPEX var/escalamiento/HITL × 60 meses)
│
├── Condiciones Cadena C (proveedores)
│   └── Costo Cadena C (todos los componentes × 60 meses)
│
├── Tasas, TRM, Polizas (GMF, IPC, tasas)
│   └── Pólizas - Costo Financiacion (ICA, GMF, pólizas, financiación × 60 meses)
│
└── Rot, Ausent y Rentabilidad (tabla ramp-up)

─────────────── CALCULADORAS ───────────────

Costos Totales (agregador por canal y mes)
    ↓
Hoja Maestra Escenarios (facturación por escenario)
    ↓
┌─────────────────────────────────────┐
│  Vision Tarifas_Modelo_Cobro        │ ← Tarifas finales
│  Visión P&G                         │ ← Estado resultados 60m
│  Vision Cost To Serve               │ ← CTS por unidad
│  Visión Imprimible                  │ ← Resumen ejecutivo
└─────────────────────────────────────┘
```

---

## 4. Análisis de Diferencias Backend vs Excel V2-5

### 4.1 GAP-VT-1 — Factor de Billing Incompleto (CRÍTICO)

**Archivo:** `calculators/vision_tarifas.py:341-352`

**Excel V2-5:**
```
factor = (1 - margen) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento)
```

**Backend actual:**
```python
def _factor_billing(self) -> float:
    p = self._panel
    f = (1.0 - p.margen) * (1.0 - p.op_cont)
    if p.com_cont > 0:
        f *= (1.0 - p.com_cont)
    return f  # FALTA: × (1-markup) × (1+descuento)
```

**Corrección requerida:**
```python
def _factor_billing(self) -> float:
    p = self._panel
    f = (1.0 - p.margen) * (1.0 - p.op_cont) * (1.0 - p.com_cont)
    if p.markup > 0:
        f *= (1.0 - p.markup)
    if p.descuento > 0:
        f *= (1.0 + p.descuento)  # descuento SUMA en denominador (reduce precio)
    return f
```

---

### 4.2 GAP-PYG-1 — Campo "Imprevistos" Faltante (NUEVO en V2-5)

**Archivo:** `calculators/pyg.py`, `domain/models.py` (PyGMensual)

**Excel V2-5 (fila 26):**
```
Imprevistos = Panel!C73 × Ingreso_Bruto
Ingreso_Neto = Ingreso_Bruto + ContOp + ContCom + MarkUp - Descuento - Imprevistos
```

**Backend actual:** No existe campo `imprevistos` en `PyGMensual`. `ingreso_neto` no lo resta.

**Corrección requerida:**
1. Agregar `imprevistos: float = 0.0` en `PanelDeControl` ← Panel!C73
2. Agregar `imprevistos_ingreso: float = 0.0` en `PyGMensual`
3. En `PyGCalculator.calcular_mes()`:
   ```python
   imprevistos = self._panel.imprevistos * ingreso_bruto
   ```
4. En la propiedad `ingreso_neto` de `PyGMensual`:
   ```python
   @property
   def ingreso_neto(self) -> float:
       return (self.ingreso_bruto 
               + self.contingencia_op + self.contingencia_com + self.markup_ingreso
               - self.descuento_ingreso - self.imprevistos_ingreso)
   ```

---

### 4.3 GAP-PYG-2 — Componente Financiero No en Costo Total (ARQUITECTURA)

**Excel V2-5:**
- `Costo_Total (C30) = Cadena_A + Cadena_B + Cadena_C` — SIN costos financieros
- `Componente_Financiero (C65)` = ICA + GMF + Comisión Admin + Pólizas + Costos Fin — SEPARADO
- `Contribución = Ingreso_Neto - Costo_Total` — La contribución excluye costos financieros del denominador

**Backend actual:**
```python
# En PyGMensual:
costo_total = payroll_a + no_payroll_a + costo_b + costo_c 
              + ica + gmf + polizas + financiacion  # Incluye financiero en costo_total
contribucion = ingreso_neto - costo_total
```

**Impacto:** La "Contribución" del backend incluye los costos financieros, lo que diverge del Excel donde la Contribución es solo operativa.

**Corrección requerida:** Separar `costo_operativo` de `componente_financiero` en `PyGMensual` y calcular `contribucion = ingreso_neto - costo_operativo`.

---

### 4.4 GAP-PYG-3 — Comisión de Administración 1.18% (NUEVO en V2-5)

**Excel V2-5 (fila 68):**
```
Comisión Administración = SUMPRODUCT('Pólizas'!E222:E240 × (B="Activado"))
                        + SUMPRODUCT('Pólizas'!E280:E298 × (B="Activado"))
```

La Comisión de Administración del 1.18% sobre ventas (Gcomercial-Operaciones) es un nuevo componente financiero en V2-5 que NO está implementado en el backend.

**Corrección requerida:**
- Agregar cálculo de `comision_administracion` en `CostosFinancierosCalculator`
- Fuente: `Panel!C45` = 1.18% (Comisión de Administración, activada=True)
- Fórmula: `comision_adm = 0.0118 × ingreso_bruto` (proporción atribuible = 1.0, Panel!G45)

---

### 4.5 GAP-CTS-1 — Cadena C en CTS Ponderado (FALTANTE)

**Excel V2-5:**
```
CTS_Ponderado = (CTS_A × part_A) + (CTS_B × part_B) + (CTS_C × part_C)
```
- `part_C = Panel!O51` = O50/L50

**Backend actual:**
```python
denominador = k50 + l50
cts_pond = (cts_a * k50 + cts_b * l50) / denominador
```
No incluye Cadena C.

**Corrección requerida:** Incluir `m50` (volumen Cadena C) y `cts_c` en el cálculo ponderado.

---

### 4.6 GAP-CTS-2 — CTS Mensual en Imprimible (CÁLCULO DIFERENTE)

**Excel V2-5:**
```
H19 (Vision Imprimible) = 'Visión P&G'!BK30 / 'Visión P&G'!E6
                        = Costo_Total_Acumulado(mes60) / meses_contrato
```

**Backend actual:** KPIsCalculator calcula `costo_mensual_promedio = SUM(costo_total) / meses`. Esto es el promedio real de los 60 meses.

> Nota: El Excel usa el valor acumulado de la columna BK (mes 60), que es efectivamente la suma acumulada hasta ese mes. Son equivalentes: `SUM(costo_mes1..costo_mes60) / 60`.

**Conclusión:** La fórmula produce el mismo resultado matemáticamente.

---

### 4.7 GAP-PCG-1 — Estructura de Escenarios vs Perfiles (ARQUITECTÓNICO)

**Excel V2-5:** La Visión Tarifas y Hoja Maestra Escenarios reciben configuración mediante **escenarios** (1-5) definidos en Panel!A81:D113. Cada escenario tiene: Modalidad, Canal, Modelo de Cobro, Componente Fijo (tipo + %), Componente Variable (tipo + %).

**Backend actual:** La `VisionTarifasCalculator` recibe `perfiles_cadena_a` directamente (lista de `PerfilCadenaA`). No hay concepto de "escenario" separado.

**Evaluación:** La implementación actual es conceptualmente equivalente — cada perfil activo representa efectivamente un "escenario". Sin embargo, el Excel puede tener múltiples escenarios con el mismo canal (ej. Escenario 1 y Escenario 2 ambos son Inbound pero diferente configuración), lo que el backend no maneja si hay duplicidad de canal.

---

### 4.8 GAP-PCG-2 — Pólizas: Nuevas Filas V2-5

**Excel V2-5 — Panel de Control General (filas 37-55):**

Pólizas estándar incluidas:
| Póliza | Cadena A | Cadena B | Cadena C | % Póliza | % Atribuible | ¿Se extiende? | Meses |
|--------|----------|----------|----------|----------|-------------|---------------|-------|
| Seriedad | ✗ | ✓ | - | 0.50% | 10% | ✓ | 24 |
| Cumplimiento | ✓ | ✓ | - | 0.62% | 20% | ✗ | - |
| Salarios | ✓ | ✓ | - | 1.19% | 10% | ✗ | - |
| Calidad | ✗ | ✓ | ✓ | 1.19% | 20% | ✓ | 36 |
| RC Cruzada | ✗ | - | ✓ | 2.75% | 40% | ✗ | - |
| IRF | ✗ | - | ✓ | 2.75% | 10% | ✗ | - |
| Responsabilidad | ✓ | - | ✓ | 0.69% | 40% | ✗ | - |
| **Comisión Adm.** | ✓ | - | ✗ | **1.18%** | **100%** | ✗ | - |
| Resp. Civil Protec. Datos | ✗ | ✓ | - | 3.50% | 40% | ✗ | - |

**Nuevas pólizas en V2-5 vs backend:** La estructura de pólizas es más compleja, con extensiones temporales y atribuciones por porcentaje que el backend no modela completamente.

---

### 4.9 GAP-ING-1 — Ingreso Cadena A en P&G usa Panel!C63 relativo para Cadena C

**Excel P&G filas 19-21:**
```
C19 (Cad A): =C31*(1+'Panel de Control General'!$C$63)*C15  ← $C$63 FIJO
C20 (Cad B): =C45*(1+'Panel de Control General'!$C$63)*C15  ← $C$63 FIJO
C21 (Cad C): =C55*(1+'Panel de Control General'!C$63)*C15   ← C$63 RELATIVO (columna varía)
```

Para mes D (mes 2), C21 se convierte en `D55*(1+Panel!D$63)*D15`. Si el margen no varía entre columnas en Panel, esto es equivalente. Sin embargo, en filas H-L hay un offset observado:
- H21 usa `Panel!J$63` (desfasado 2 columnas)

**Evaluación:** Esto parece un error de fórmula en el Excel, no una intención de margen variable. El backend usando Panel!C63 fijo es correcto.

---

### 4.10 GAP-VIS-1 — Vision Imprimible no implementada completamente

**Excel V2-5:** La Visión Imprimible tiene secciones:
1. Ficha del Deal
2. Economics (Ingreso, CTS, Margen)
3. Configuración Comercial (Modelo de Cobro, tarifas)
4. Análisis Gráfico (Waterfall, evolución mensual)
5. Comparativo de Escenarios

**Backend:** El endpoint de Visión Imprimible (`/api/v1/simulation/results`) expone un formato básico. Las secciones 4 y 5 (gráficos y comparativo de escenarios) no están implementadas.

---

## 5. Reglas de Negocio Detectadas

### 5.1 Ramp-Up
```
Origen: 'Rot, Ausent y Rentabilidad'!B38:BI43
Lookup: INDEX(rango, MATCH(linea_negocio, A38:A43, 0), MATCH(mes_contrato, ..., 0))
Líneas de negocio: SAC, SACO, Cobranzas, Plataformas, Ventas Multicanal, etc.
Meses: 1..60 (columnas B..BI)
```

### 5.2 Indexación
```
Componente Humano: IPC (Anual, Mes de Ajuste = Panel!L9 = mes 6)
Componente Tecnológico: IPC (Anual, Mes de Ajuste = Panel!L9)
Tasa: Panel!L6 = IPC humano, Panel!L7 = IPC tecnológico
```

### 5.3 Semáforo de Margen
```
Rangos: desde Vision Cost To Serve!C229:D244 filtrados por categoría de Riesgo (Riesgo!G16, G17)
Categorías de Riesgo: definidas en hoja 'Riesgo'
Estado: "⚠ Bajo mínimo" / "✓ Excede máximo" / "✓ Dentro de rango"
```

### 5.4 Modelo de Cobro — Lógica de Componentes
```
Modelo    | Comp. Fijo     | Comp. Variable
----------|----------------|---------------
Fijo      | FTE o Tiempo   | —
Variable  | —              | Transacción
Híbrido   | FTE o Tiempo   | Transacción
Resultados| —              | Honorarios/Comisión
SACO      | Por Venta TC   | Por Seguro
```

### 5.5 Activación de Cadenas
```
Panel!M15 = TRUE → Cadena A Inbound activa
Panel!M28 = TRUE → Cadena A Outbound activa
Panel!N15 = TRUE → Cadena B Inbound activa
Panel!O15 = TRUE → Cadena C Inbound activa
```

### 5.6 Horas Productivas (para FTE)
```
Horas semanales: 42
Semanas al mes: 4.33
Breaks (2×15min/día): 30min
Deslogueos: 5min
Coaching: 5min
Pausa activa: 5min
Formación promedio: ((horas_formación_mes/4)/6)×60 min
─────────────────────────────────────
Total improductivo: SUM de anteriores
Horas logueadas: semanas×horas - ausentismo
Horas productivas: logueadas - coaching - pausa_activa
```

---

## 6. Patrones de 60 Meses

### Estructura general
- **Filas = conceptos**, **Columnas = meses**
- Columna C = Mes 1 (Panel!C10 = Fecha Inicio)
- Columna BJ = Mes 60 (`EDATE` encadenado 59 veces)
- Mes del contrato (fila 11): `IF(col12>=MATCH(fechaInicio, C13:BJ13, 0), col12-MATCH(...)+1, "")`

### Patrón de activación
```python
# Para cada celda col_i:
if mes_del_contrato <= meses_contrato:
    valor = calcular_valor(mes_del_contrato)
else:
    valor = 0  # o "" para labels
```

### Patrón SUMPRODUCT con filtro "Activado"
```
SUMPRODUCT(data_range * (status_range = "Activado"))
```
Permite activar/desactivar items individualmente por cadena.

---

## 7. Estructura de Almacenamiento Requerida

### 7.1 Parámetros que deben persistirse en storage

```
PanelDeControl:
  - servicio (linea_negocio)
  - nombre_cliente, tipo_cliente, antiguedad
  - periodo_pago
  - fecha_inicio, meses_contrato
  - ciudad, sede
  - margen (C63)
  - contingencia_op (C67)
  - contingencia_com (C68)
  - markup (C69)
  - descuento (C70)
  - imprevistos (C73) ← NUEVO V2-5
  - ica_rate (C34)
  - gmf_rate (C35)
  - crucero (C17)
  - tarifa_capacitacion (C16)
  - horas_formacion_mensual (C18)
  - pct_ausentismo (C19)
  - pct_rotacion (C20)
  - considera_financiacion (C21)

PerfilesCadenaA (por perfil, E..S en Condiciones Cadena A):
  - modalidad (Inbound/Outbound)
  - canal (Voz, WhatsApp, etc.)
  - nombre_perfil
  - fte
  - pct_presencial
  - salario_especifico
  - comisiones
  - modelo_cobro
  - pct_fijo
  - pct_variable

EscenariosComerciales (Panel A81:D113):
  - escenario (1-5)
  - modalidad, canal
  - modelo_cobro
  - componente_fijo (tipo + proporcion)
  - componente_variable (tipo + proporcion)

Pólizas (Panel B38:I55):
  - nombre_poliza
  - aplica_cadena_a, aplica_cadena_b, aplica_cadena_c
  - pct_poliza
  - pct_atribuible
  - se_extiende
  - meses_extension
  - activa (True/False)

VolumetriaCanales:
  - canal, tipo_modalidad (Inbound/Outbound)
  - vol_cadena_a, vol_cadena_b, vol_cadena_c
  - participacion_a, participacion_b, participacion_c
```

### 7.2 Business Rules que deben centralizarse en config/business_rules

```yaml
# config/business_rules/margenes.yaml
margen_minimo_por_linea:
  SAC: 0.15
  Cobranzas: 0.18
  SACO: 0.20
  Plataformas: 0.18

margen_maximo_por_linea:
  SAC: 0.25
  Cobranzas: 0.28

# config/business_rules/operaciones.yaml
horas_semanales: 42
semanas_al_mes: 4.33
breaks_diarios_min: 30
deslogueos_min: 5
coaching_min: 5
pausa_activa_min: 5
```

---

## 8. Resumen de Gaps — Priorización

| ID | Severidad | Componente | Gap | Impacto |
|----|-----------|------------|-----|---------|
| GAP-VT-1 | 🔴 CRÍTICO | vision_tarifas.py | Factor billing incompleto (falta markup×descuento) | Tarifa incorrecta |
| GAP-PYG-1 | 🔴 CRÍTICO | pyg.py, domain | Imprevistos no implementado (Panel!C73) | Ingreso Neto incorrecto |
| GAP-PYG-2 | 🔴 CRÍTICO | domain/models.py | Componente Financiero en Costo Total (debe separarse) | Contribución incorrecta |
| GAP-PYG-3 | 🟡 ALTO | costos_financieros.py | Comisión Administración 1.18% faltante | Costo financiero incompleto |
| GAP-CTS-1 | 🟡 ALTO | cost_to_serve.py | Cadena C excluida de CTS ponderado | CTS ponderado incorrecto |
| GAP-PCG-2 | 🟡 ALTO | costos_financieros.py | Pólizas con extensión temporal y atribución parcial | Cálculo pólizas incompleto |
| GAP-VIS-1 | 🟠 MEDIO | adapters/serializer | Secciones 4-5 Visión Imprimible no implementadas | Output incompleto |
| GAP-PCG-1 | 🟠 MEDIO | adapters | Escenarios comerciales como concepto distinto de perfiles | Flexibilidad limitada |
| GAP-ING-1 | 🟢 BAJO | pyg.py | Fórmula relativa C63 en Cadena C (error Excel) | No requiere acción |
| GAP-CTS-2 | 🟢 BAJO | kpis.py | CTS mensual: promedio vs BK30/meses (equivalente) | Sin impacto |

---

## 9. Flujo Correcto Requerido

```
1. PARAMETRIZACIÓN (Panel de Control + Condiciones Cadenas A/B/C)
   └── Persistir en storage: panel, perfiles, escenarios, pólizas, volumetría

2. BUSINESS RULES (config/business_rules)
   └── Cargar: margen mínimo/máximo, horas productivas, tasas fijas

3. MOTOR DE CÁLCULO (orden obligatorio)
   ├── NominaCalculator(perfiles, mes) → payroll por mes (60 iteraciones)
   ├── NoPayrollCalculator(perfiles, mes) → opex/capex/CF por mes
   ├── CadenaBCalculator(canales_b, mes) → costos fijo/variable Cadena B
   ├── CadenaCCalculator(condiciones_c, mes) → todos costos Cadena C
   ├── CostosFinancierosCalculator(costo_op_anterior, mes) 
   │   └── ICA + GMF + ComisionAdm(1.18%) + Pólizas + Financiación
   ├── PyGCalculator.calcular_contrato() → List[PyGMensual] con:
   │   ├── ingreso_a/b/c = costo_cadena × (1+margen) × rampup
   │   ├── ingreso_bruto = a+b+c
   │   ├── contingencia_op/com = pct × ingreso_bruto
   │   ├── markup_ingreso = pct × ingreso_bruto
   │   ├── descuento_ingreso = pct × ingreso_bruto
   │   ├── imprevistos_ingreso = Panel.imprevistos × ingreso_bruto  ← NUEVO
   │   ├── ingreso_neto = bruto+contOp+contCom+markup-descuento-imprevistos
   │   ├── costo_operativo = Cad_A + Cad_B + Cad_C  (SIN financiero)
   │   ├── componente_financiero = ICA+GMF+ComAdm+Pólizas+Financiación  (SEPARADO)
   │   ├── costo_total = costo_operativo  (no incluye financiero en total reportado)
   │   └── contribucion = ingreso_neto - costo_total
   └── KPIsCalculator → KPIsDeal

4. CONSTRUCCIÓN DE VISIONES (solo consumo de resultados)
   ├── VisionPyGBuilder(pyg_por_mes) → acumulados + presentación
   ├── VisionTarifasCalculator(pyg_por_mes, escenarios) 
   │   └── factor = (1-margen)×(1-cont_op)×(1-cont_com)×(1-markup)×(1+descuento)
   ├── CostToServeCalculator(pyg_por_mes, k50, l50, m50)
   │   └── cts_ponderado incluye Cadena C
   └── VisionImprimibleBuilder() → composición pura de las anteriores
```

---

## 10. Conclusiones

### Lo que el Excel V2-5 cambió respecto a V2-4

1. **Imprevistos** (Panel!C73): Nuevo campo que reduce el Ingreso Neto. Actualmente 0 pero la fórmula está activa.

2. **Comisión de Administración 1.18%** (fila 68): Nuevo componente financiero en el P&G y Vision Tarifas.

3. **Pólizas adicionales** (fila 69): La fórmula ahora suma más rangos del sheet Pólizas.

4. **Factor de ingreso en Vision Tarifas**: Ahora incluye 5 factores: `(1-m)×(1-co)×(1-cc)×(1-mu)×(1+d)`.

5. **Estructura de escenarios**: La Visión Tarifas ahora muestra hasta 5 escenarios comparativos, con configuración dinámica desde Panel de Control.

6. **Cadena C en CTS**: El CTS ponderado ahora incluye Cadena C con su participación.

### Lo que ya estaba bien en el backend

- Estructura de 60 meses dinámica ✓
- Ramp-up por línea de negocio ✓
- Payroll con sub-componentes (salario, cap, exámenes, seguridad, crucero) ✓
- No Payroll con OPEX/inversiones/CF ✓
- Cadena B fijo/variable/HITL/escalamiento ✓
- ICA y GMF sobre costo anterior ✓
- Acumulados en P&G ✓
- K50 Inbound (vol_cadena_a) + Outbound (FTE) ✓

### Próximos pasos requeridos

1. **Implementar `imprevistos`** en PanelDeControl + PyGMensual + PyGCalculator
2. **Corregir `_factor_billing`** en VisionTarifasCalculator para incluir markup y descuento
3. **Separar `componente_financiero`** de `costo_total` en PyGMensual
4. **Implementar `ComisionAdministracion` (1.18%)** en CostosFinancierosCalculator
5. **Incluir Cadena C** en CTS ponderado en CostToServeCalculator
6. **Mapear escenarios comerciales** correctamente desde Panel de Control
7. **Auditar pólizas** con extensión temporal en CostosFinancierosCalculator
