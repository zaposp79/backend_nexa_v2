# INVENTARIO COMPLETO — NEXA Pricing Simulator V2-7

> Generado por ingeniería inversa con openpyxl · Fecha: 2026-05-27

---

## 1. Resumen de Hojas (23 total)

| # | Nombre | Visibilidad | Tipo | Dimensiones | Propósito |
|---|--------|-------------|------|-------------|-----------|
| 1 | Riesgo | VISIBLE | Entrada/Cálculo | B1:Y282 | Matriz de riesgo del deal (10 factores, pesos Operativo 60% / Cliente 40%) |
| 2 | Listas Desplegables | HIDDEN | Soporte | A3:BH94 | Catálogos de validación para dropdowns; también contiene número de mes inicio |
| 3 | Graficos | HIDDEN | Soporte | A1:BV112 | Datos auxiliares para gráficas de la presentación |
| 4 | Tasas, TRM, Polizas | VISIBLE | Parametrización | A1:G54 | IPC, SMLV y acumulados por año; tarifas de pólizas; tasas ICA por municipio |
| 5 | Rot, Ausent y Rentabilidad | VISIBLE | Parametrización | A3:BI84 | Histórico de ausentismo y rotación por servicio; márgenes objetivo por servicio; tabla de ramp-up |
| 6 | Inputs de Nomina | HIDDEN | Parametrización | A3:AP133 | Salario mínimo, prestaciones sociales, recargos; cargos y salarios base; estructura de costos laborales completa |
| 7 | Nomina Loaded | VISIBLE | Cálculo | A3:CF474 | Proyección mensual de nómina por perfil/canal durante 60 meses; consolida 7 secciones de sub-cálculo |
| 8 | No payroll | VISIBLE | Cálculo | A4:CA267 | Costos tecnológicos y de infraestructura no laborales; OPEX fijo, inversiones, costos por estación |
| 9 | Costo Fijo | VISIBLE | Cálculo | A3:BS240 | Costos fijos operativos por modalidad/canal (sede, utilities, facilities) a 60 meses |
| 10 | Costo Variable | HIDDEN | Cálculo | A3:BS334 | Costos variables de Cadena B: tarifas canal, OPEX variable, tasa escalamiento, HITL |
| 11 | Costo Cadena C | VISIBLE | Cálculo | A3:BT479 | Todos los costos del proveedor externo (Cadena C): tarifa, OPEX, inversiones, integración, variable, HITL |
| 12 | Costos Totales | HIDDEN | Consolidación | A3:BL137 | Suma Nómina Loaded + No payroll por perfil; visión por canal Inbound/Outbound |
| 13 | Pólizas - Costo Financiacion | VISIBLE | Cálculo | A5:BL459 | ICA, GMF, comisión adm 1.18%, pólizas adicionales, costo de financiación por período de pago |
| 14 | Panel de Control General | VISIBLE | Entrada | A3:S211 | MAESTRO DE INPUTS: cliente, servicio, ciudad, fechas, volumetría, pólizas activas, márgenes, escenarios comerciales |
| 15 | Condiciones Cadena A | VISIBLE | Cálculo | B4:AY161 | Estructura de equipo Cadena A: perfiles, FTE, ratios de staffing, comisiones por perfil |
| 16 | Condiciones Cadena B | VISIBLE | Cálculo | A4:K170 | OPEX e inversiones de Cadena B (plataformas, cloud, licencias) |
| 17 | Condiciones Cadena C | VISIBLE | Cálculo | A3:K168 | Parámetros del proveedor externo Cadena C |
| 18 | Visiones | VISIBLE | Navegación | A1:A1 | Hoja de navegación (prácticamente vacía) |
| 19 | Visión Imprimible | VISIBLE | Salida | A1:AB119 | Resumen ejecutivo imprimible del deal |
| 20 | Vision Cost To Serve | VISIBLE | Salida | A1:DN268 | Vista detallada CTS por cadena, canal, componente; ficha del deal; economics |
| 21 | Vision Tarifas_Modelo_Cobro | VISIBLE | Salida | A1:S180 | Tarifas por escenario comercial (hasta 5); facturación total; desglose por componente fijo/variable |
| 22 | Hoja Maestra Escenarios | VISIBLE | Cálculo | A2:L289 | Motor de escenarios: 5 escenarios × cálculo completo (Cadena A + B + C + tarifas + márgenes) |
| 23 | Visión P&G | VISIBLE | Salida | A1:CO80 | P&G mensual a 60 meses: ingresos, costos por cadena, utilidad, % margen |

---

## 2. Hojas de Entrada (Inputs del usuario)

### Panel de Control General — Hoja maestra de configuración

**Sección: Datos Operativos (B3:C21)**

| Celda | Campo | Valor ejemplo | Tipo |
|-------|-------|---------------|------|
| C5 | Servicio | `"Captura de Datos"` | Dropdown |
| C6 | Nombre de cliente actual | `"AMERICAS BUSINESS PROCESS SERVICES S.A"` | Texto |
| D6 | Nombre cliente nuevo | `"Bancamia"` | Texto |
| C7 | Antigüedad | `=IF(C6="CLIENTE NUEVO","Cliente Nuevo","Cliente Antiguo")` | Fórmula |
| C8 | Tipo de cliente | `"No Grupo Aval"` | Dropdown |
| C9 | Período de pago (días) | `30` | Numérico |
| C10 | Fecha Inicio | `2026-06-01` | Fecha |
| C11 | Duración meses | `12` | Numérico |
| C12 | Ciudad | `"Bogota "` | Dropdown |
| C13 | Sede | `"Bogota - Toberin"` | Texto |
| C16 | Tarifa diaria capacitación | `20000` | COP |
| C17 | Crucero | `=8000*(1+5.1%)` → hardcode 5.1% IPC | COP |
| C18 | Horas de formación mensual | `8` | Horas |
| C19 | % Ausentismo | `0.065` | % |
| C20 | % Rotación | `0.085` | % |
| C21 | Se considera costo financiación | `"No"` | Dropdown |

**Sección: Indexación (K5:L9)**

| Celda | Campo | Valor |
|-------|-------|-------|
| L6 | Componente Humano | `"80% SMMLV 20% IPC"` |
| L7 | Componente Tecnológico | `"20% SMMLV 80% IPC"` |
| L8 | Frecuencia | `"Anual"` |
| L9 | Mes de Ajuste | `6` |
| L10 | Tasa de interés mensual | `0.0153` |

**Sección: Volumetría Mensual Inbound (K18:R25)**

Canales: Voz, IVR, WebChat, Mensajes, WhatsApp, Correo, Otros  
Dimensiones: FTE (Cadena A), Volumen (Cadena B), Volumen (Cadena C)

**Sección: Pólizas activas (B33:F55)**

| Póliza | Habilitada | % Prima | % Atribuible |
|--------|-----------|---------|--------------|
| Póliza de Seriedad | — | 0.50% | variable |
| Póliza de Cumplimiento | — | 0.62% | variable |
| Poliza de Salarios | — | 1.19% | variable |
| Poliza de Calidad | — | 1.19% | variable |
| Poliza de rc cruzada | — | 2.75% | variable |
| Póliza de IRF | FALSE | 2.75% | 10% |
| Póliza de Responsabilidad | FALSE | 0.69% | 40% |
| Comisión Adm 1.18% | TRUE | 1.18% | 100% |
| Otros impuestos | FALSE | 1.00% | 0% |

**Sección: Márgenes y reglas de negocio (B60:E75)**

| Celda | Campo | Valor |
|-------|-------|-------|
| C63 | Margen objetivo Cadena A | FORMULA (por servicio, ver Rot,Ausent) |
| D63 | Margen objetivo Cadena B | `0.30` |
| E63 | Margen objetivo Cadena C | `0.20` |
| C67 | Contingencia Operativa | `0` |
| C68 | Contingencia Comercial | `0` |
| C69 | Mark up (complejidad, horarios) | `0` (rango: 2%–8%) |
| C70 | Descuento volumen | `0` (máx 8%) |
| C73 | Imprevistos | `0` |

**Sección: Escenarios comerciales (B77:G113) — Hasta 5 escenarios**

Cada escenario tiene: Modalidad, Canal, Modelo de Cobro (Fijo/Variable/Híbrido), Componente Fijo, Proporción Fijo, Componente Variable, Proporción Variable

---

## 3. Tablas y Rangos Nombrados

El archivo no usa Named Ranges formales, pero usa rangos clave referenciados directamente:

| Rango | Hoja | Contenido |
|-------|------|-----------|
| `$E$17:$S$17` | Condiciones Cadena A | FTE por canal/modalidad |
| `$E$15:$S$15` | Condiciones Cadena A | Canal por columna |
| `$D$25:$D$48` | Condiciones Cadena A | Lista de cargos |
| `$C$110:$H$133` | Inputs de Nomina | Ratios de staffing por cargo |
| `$B$110:$B$133` | Inputs de Nomina | Nombre de cargos (lookup) |
| `$C$4` | Inputs de Nomina | Salario Mínimo = 1,750,905 COP |
| `$C$5` | Inputs de Nomina | Auxilio Transporte = 249,095 COP |
| `$A$51:$BH$51` | Listas Desplegables | Número de mes inicio (SUM → mes actual) |
| `$B$38:$BI$43` | Rot, Ausent y Rentabilidad | Tabla ramp-up por servicio × mes |

---

## 4. Dropdowns y Validaciones Detectadas

| Campo | Opciones identificadas |
|-------|----------------------|
| Servicio | Cobranzas, SAC, Ventas Multicanal, SACO, Plataformas, Captura de Datos |
| Canal | Voz, IVR, WebChat, Mensajes, WhatsApp, Correo, Otros, Fuerza de ventas |
| Modalidad | Inbound, Outbound |
| Modelo de Cobro | Fijo, Variable, Híbrido |
| Componente Fijo | FTE, Tiempo |
| Componente Variable | Transacción, Resultados, Honorarios |
| Ciudad | Armenia, Barranquilla, Bogota, Bucaramanga, Cali, Cartagena, Manizales, Medellín, Neiva, Palmira, Pasto... |
| Tipo de cliente | Grupo Aval, No Grupo Aval |
| Indexación Humano | 80% SMMLV 20% IPC, 50% SMMLV 50% IPC, IPC, SMLV, Tarifas definidas, etc. |

---

## 5. Hardcodes Detectados

| Hoja | Celda | Valor | Descripción |
|------|-------|-------|-------------|
| Panel de Control General | C17 | `=8000*(1+5.1%)` | Tarifa crucero con IPC hardcodeado 5.1% |
| Inputs de Nomina | C4 | `1,750,905` | SMMLV 2026 |
| Inputs de Nomina | C5 | `249,095` | Auxilio transporte 2026 |
| Inputs de Nomina | C16 | `=18505000*(1+23%)` | Salario Director de Cuentas con factor 23% hardcode |
| Inputs de Nomina | I13 | `0.085` | % Salud empleado |
| Inputs de Nomina | J13 | `0.12` | % Pensión |
| Inputs de Nomina | K13 | `0.00522` | % ARL Agentes |
| Inputs de Nomina | L13 | `0.00522` | % ARL Staff |
| Inputs de Nomina | N13 | `0.04` | % Caja |
| Inputs de Nomina | O13 | `0.04` | % ICBF + Sena |
| Inputs de Nomina | Q13 | `0.0833` | % Cesantías |
| Inputs de Nomina | R13 | `0.0833` | % Primas |
| Inputs de Nomina | S13 | `0.12` | % Interés cesantías |
| Inputs de Nomina | T13 | `0.0417` | % Vacaciones |
| Inputs de Nomina | X13 | `0.90` | % Recargo festivo |
| Inputs de Nomina | Z13 | `0.90` | % Recargo dominical |
| Inputs de Nomina | AB13 | `0.35` | % Recargo nocturno |
| Inputs de Nomina | AD13 | `0.15` | % Recargo festivo nocturno |
| Tasas | B4 | `0.0527` | IPC 2025–2030 (todos iguales) |
| Tasas | C5 | `0.2378` | SMLV 2026 (diferente resto) |
| Condiciones Cadena A | E8 | `522.2` | TMO en segundos |
| Hoja Maestra Escenarios | J5 | `42` | Horas semanales |
| Hoja Maestra Escenarios | J6 | `8` | Horas formación mensual |
| Hoja Maestra Escenarios | J7 | `4.33` | Semanas al mes |
| Hoja Maestra Escenarios | J13 | `30` | Minutos de breaks (2×15 min) |
| Hoja Maestra Escenarios | J15 | `5` | Minutos de deslogueo |
| Hoja Maestra Escenarios | J16 | `5` | Minutos de coaching |
| Hoja Maestra Escenarios | J17 | `5` | Minutos de pausa activa |
| Condiciones Cadena B | H8 | `183` | COP por sesión WhatsApp |
| Panel de Control General | D63 | `0.30` | Margen Cadena B fijo |
| Panel de Control General | E63 | `0.20` | Margen Cadena C fijo |

---

## 6. Dependencias Inter-Hojas (Resumen)

```
Panel de Control General
    ├── Condiciones Cadena A (FTE, perfiles, TMO, ratios)
    │       └── Inputs de Nomina (salarios, prestaciones, ratios staff)
    │               └── Tasas, TRM, Polizas (IPC, SMLV)
    ├── Condiciones Cadena B (OPEX, inversiones)
    ├── Condiciones Cadena C (proveedor externo)
    ├── Listas Desplegables (número mes inicio)
    └── Rot, Ausent y Rentabilidad (márgenes, ausentismo, ramp-up)

Nomina Loaded
    ├── Panel de Control General (fechas, duración, indexación)
    ├── Condiciones Cadena A (FTE por perfil)
    └── Inputs de Nomina (costos laborales)

No payroll
    ├── Panel de Control General
    └── Nomina Loaded (fecha inicio)

Costo Fijo
    ├── Panel de Control General
    └── Nomina Loaded (fecha inicio)

Costo Variable [HIDDEN]
    └── Panel de Control General (volumetría)

Costo Cadena C
    ├── Panel de Control General
    └── Condiciones Cadena C

Costos Totales [HIDDEN]
    ├── Nomina Loaded
    └── No payroll

Pólizas - Costo Financiacion
    ├── Costos Totales
    └── Panel de Control General (márgenes, período pago)

Hoja Maestra Escenarios
    ├── Panel de Control General (escenarios, márgenes)
    ├── Condiciones Cadena A (FTE)
    ├── Nomina Loaded (nómina por escenario)
    ├── No payroll (no-payroll por escenario)
    ├── Costo Fijo (costos fijos por escenario)
    ├── Costo Variable (costos variables)
    ├── Costo Cadena C (costos proveedor)
    └── Pólizas - Costo Financiacion (ICA, GMF, pólizas)

Vision Tarifas_Modelo_Cobro
    └── Hoja Maestra Escenarios (facturación, tarifas por escenario)

Vision Cost To Serve
    ├── Vision Tarifas_Modelo_Cobro
    ├── Nomina Loaded
    ├── No payroll
    ├── Costo Fijo
    ├── Costo Variable
    ├── Costo Cadena C
    └── Panel de Control General

Visión P&G
    ├── Vision Tarifas_Modelo_Cobro (ingresos)
    ├── Nomina Loaded (costos)
    ├── No payroll (costos)
    ├── Costo Fijo (costos)
    ├── Costo Variable (costos)
    ├── Costo Cadena C (costos)
    ├── Pólizas - Costo Financiacion (componente financiero)
    └── Rot, Ausent y Rentabilidad (ramp-up)
```
