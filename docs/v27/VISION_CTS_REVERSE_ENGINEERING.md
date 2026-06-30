# Visión Cost To Serve — Ingeniería Inversa Excel V2-7

## Estructura Excel (hoja "Vision Cost To Serve", A1:DN268)

### Sección 01 — Ficha del Deal (filas 7-13)
| Fila | Label | Fórmula | Backend |
|------|-------|---------|---------|
| 11 | CLIENTE | =IF(Panel!C7="Cliente Nuevo", Panel!D6, Panel!C6) | panel.cliente |
| 13 | FECHA DE INICIO | =Panel!C10 | panel.fecha_inicio |

### Sección 02 — Economics (filas 15-20)
| Fila | Label | Fórmula | Backend |
|------|-------|---------|---------|
| 19 | INGRESO MENSUAL | =IFERROR('Vision Tarifas'!C72, 0) | vision_tarifas.ingreso_mensual |
| 20 | Escenario 1 | ='Vision Tarifas'!C29 | — |

### Sección "Visión General por Servicio" (filas 25-48)
| Fila | Label | Tipo | Backend field | Status |
|------|-------|------|---------------|--------|
| 27 | Servicio | dato | panel.linea_negocio | ✓ |
| 29 | Cadena A | header | — | visual |
| 31 | Participación | % | cost_to_serve.participacion_a | ✓ |
| 34 | Cost To Serve | subtotal | cost_to_serve.cts_cadena_a | ✓ |
| 35 | Payroll | subtotal | desglose_a.nomina | ✓ |
| 36 | Nomina Loaded | subtotal | desglose_a.nomina_loaded | ✓ |
| 37 | Salario Fijo | linea | desglose_a.salario_fijo | ✓ |
| 38 | Salario Variable | linea | desglose_a.salario_variable | ✓ |
| 39 | Capacitación Inicial | linea | desglose_a.cap_inicial | ✓ |
| 40 | Capacitación Rotación | linea | desglose_a.cap_rotacion | ✓ |
| 41 | Exámenes Médicos | linea | desglose_a.examenes | ✓ |
| 42 | Estudios de Seguridad | linea | desglose_a.estudios_seguridad | ✓ |
| 43 | Crucero | linea | — | GAP-CTS-HIER-1 |
| 45 | No Payroll | subtotal | desglose_a.no_payroll | ✓ |
| 46 | OPEX Fijo | linea | desglose_a.opex_fijo | ✓ |
| 47 | Inversiones | linea | desglose_a.inversiones | ✓ |
| 48 | Costos Fijos x Estación | linea | desglose_a.costos_fijos_estacion | ✓ |

### Sección "Visión General por Canal" (filas 58-83) — CONDICIONAL
**Condición**: `=IF($C$27="SAC", "✓ Habilitado", "— Deshabilitado")`
**Nota**: Verifica si el servicio es "SAC" para habilitar desglose por canal.

#### Inbound (filas 62-71)
Canales: WhatsApp, Correo, WebChat, Mensajes, Voz, Otros, IVR

#### Outbound (filas 73-83)  
Canales: WhatsApp, Mensajes, Correo, WebChat, IVR, Voz, Otros, Fuerza de Ventas

**STATUS**: Backend NO implementa channel-level CTS breakdown → **GAP-CTS-CHAN-1**

### Sección "Visual Detallada por Canal" (filas 87-270)
Una tabla por canal: CTS × modalidad (Inbound + Outbound)
**STATUS**: Backend NO implementa → **GAP-CTS-CHAN-1**

## Denominadores

| Denominador | Excel | Backend | Fórmula |
|-------------|-------|---------|---------|
| K50 | Panel!M52 = SUM(M44:M51) | CostToServeCalculator._k50() | FTE_outbound + vol_cadena_a_mensual_inbound |
| L50 | Panel!N52 = SUM(N44:N51) | CostToServeCalculator._l50() | SUM(vol_mensual cadena_b channels) |
| M50 | Panel!O52 | CostToServeCalculator._m50() | SUM(vol_mensual cadena_c channels) |

## Fórmulas CTS (filas 46-48)
```
CTS_component = SUM(IF(M17=TRUE, [cadena_a rows], 0), IF(M30=TRUE, [cadena_b rows], 0))
              / meses_contrato
              / K50
```

## Gaps (Fase 2 — estado de cierre)
| ID | Descripción | Estado | Resolución |
|----|-------------|--------|-----------|
| GAP-CTS-HIER-1 | Campo "crucero" en DesgloseCTSCadenaA | **CERRADO** | Premisa Fase-1 "siempre 0" **CORREGIDA**: workbook fila 43 = 11.17, canal WhatsApp fila 107 = 8408. Campo `crucero` añadido; acumulado desde `ResultadoNomina.crucero`. Sub-componentes payroll ahora suman exacto al agregado `nomina` (verificado). |
| GAP-CTS-ACT-1 | Regla IF(C27="SAC") + servicio como driver | **CERRADO (modelo servicio-driven)** | Ver "Modelo servicio-driven" abajo. Catálogo único desde `Listas Desplegables!A4:A9`; gate desde `domain/services/servicio_catalogo.py`. Servicio SÍ es driver funcional (nómina/ramp-up) pero NO de chains/channels (inputs independientes). |
| GAP-CTS-CHAN-1 | Channel-level CTS (filas 64-270) | **UNDETERMINED** | Las fórmulas usan denominador por canal `FILTER(Panel!M19:M25, K19:K25=canal)` = volumen Cadena-A por canal con split inbound/outbound. El backend no expone esa tabla de volumen por canal con mapeo 1:1 trazable; implementarla exige validar `volumetria → Panel!K/L/M/P` celda a celda. **No se fabrica** — requiere validación de workbook. |

## GAP-CTS-ACT-1 — Modelo servicio-driven (derivado de Excel)

**Catálogo de servicios** (`Listas Desplegables!A4:A9`, fuente única de verdad):
Cobranzas · SAC · Ventas multicanal · SACO · Plataformas · Captura de Datos

**Qué `servicio` (Panel!C5) SÍ controla (verificado celda a celda):**

| Dimensión | Mecanismo Excel | Backend |
|-----------|-----------------|---------|
| Salarios/capacidad nómina | `INDEX('Inputs de Nomina'!C110:H133, MATCH(rol,…), MATCH(C5,'Inputs de Nomina'!C109:H109,0))` — servicio elige COLUMNA | Lookup salario/rol por `linea_negocio` (certificado) |
| Curva ramp-up | `MATCH(C5,'Rot, Ausent y Rentabilidad'!A38:A43)` | `calcular_rampup(linea_negocio,…)` (certificado) |
| Columna de gráfico | `Graficos!I4` IFS sobre servicio | cosmético |
| Cabecera detalle canal (CTS) | `C58/C87 = IF(C5="SAC",…)` | `canal_view_habilitado` (flag, no oculta datos) |

**Qué `servicio` NO controla (verificado — inputs independientes):**

| Dimensión | Driver real | Evidencia |
|-----------|-------------|-----------|
| Chains activas A/B/C | `Panel!M17`/`M30` (booleanos = `cadenas_activas`) | No referencian C5 |
| Channels activos | volumen `Panel!L19:L25` > 0 | `K19:K25` nombres fijos; sin ref C5 |

**Clasificación de `IF(C27="SAC")`**: NO etiqueta cosmética (depende de un driver
funcional) pero tampoco filtro estructural ni switch de cálculo — es un **gate de
relevancia semántica** (marca si el desglose por canal es la vista primaria del
servicio). Los datos por canal **se computan siempre** (verificado: servicio="Captura
de Datos" → cabecera "Deshabilitado" pero WhatsApp vol=26292, CTS=4.12M computados).
El backend expone el gate y **NO suprime cómputo** (suprimir contradiría el workbook).

> Corrección a la lectura previa: "etiqueta cosmética" era incompleto. El servicio SÍ
> es driver funcional, pero en la capa nómina/ramp-up (ya implementada), NO en la
> activación de chains/channels de la vista CTS.
