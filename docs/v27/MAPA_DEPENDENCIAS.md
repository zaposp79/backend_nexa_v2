# MAPA DE DEPENDENCIAS ENTRE HOJAS — V2-7

> Grafo completo de flujo de datos. Las flechas indican "depende de" (→).

---

## 1. Grafo Principal (texto)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INPUTS PRIMARIOS                                     │
├─────────────────┬──────────────────────┬───────────────────────────────────-┤
│ Panel de Control│  Tasas, TRM, Polizas │  Rot, Ausent y Rentabilidad         │
│ General         │  (IPC, SMLV, pólizas,│  (ausentismo, rotación, márgenes,   │
│ (todos los      │   ICA por municipio) │   ramp-up por servicio)             │
│ inputs usuario) │                      │                                     │
└────────┬────────┴──────────┬───────────┴──────────────────┬─────────────────┘
         │                   │                              │
         ▼                   ▼                              │
┌────────────────┐  ┌────────────────────┐                 │
│ Inputs de      │  │ Listas Desplegables│                 │
│ Nomina         │  │ (mes inicio,       │                 │
│ (SMMLV, ARL,   │  │  catálogos)        │                 │
│ prestaciones,  │  └────────┬───────────┘                 │
│ ratios staff)  │           │                             │
└────────┬───────┘           │                             │
         │                   │                             │
         ▼                   ▼                             │
┌────────────────────────────────────────────────────────-─┤
│                CAPA DE ESTRUCTURAS                        │
│                                                           │
│  Condiciones Cadena A ◄── Panel + Inputs de Nomina       │
│  Condiciones Cadena B ◄── Panel                          │
│  Condiciones Cadena C ◄── Panel                          │
└──────────┬───────────────────┬────────────────────────---┘
           │                   │
           ▼                   ▼
┌──────────────────────────────────────────────────────────┐
│                 CAPA DE CÁLCULO MENSUAL (60 meses)        │
│                                                           │
│  Nomina Loaded     ◄── Panel + Condiciones A + Inp.Nom   │
│  No payroll        ◄── Panel + Nomina Loaded (fecha)     │
│  Costo Fijo        ◄── Panel + Nomina Loaded (fecha)     │
│  Costo Variable    ◄── Panel (volumetría)                │
│  Costo Cadena C    ◄── Panel + Condiciones C             │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                 CAPA CONSOLIDADORA                         │
│                                                           │
│  Costos Totales [HIDDEN] ◄── Nomina Loaded + No payroll  │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              CAPA FINANCIERA                               │
│                                                           │
│  Pólizas - Costo Financiacion ◄── Costos Totales + Panel │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              MOTOR DE ESCENARIOS                           │
│                                                           │
│  Hoja Maestra Escenarios ◄── Panel + Condic.A +          │
│                               Nomina + NoPayroll +        │
│                               CostoFijo + CostoVariable + │
│                               CostoCadenaC + Pólizas      │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              CAPA DE TARIFAS                               │
│                                                           │
│  Vision Tarifas_Modelo_Cobro ◄── Hoja Maestra Escenarios │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              VISIONES DE SALIDA                            │
│                                                           │
│  Vision Cost To Serve ◄── Vision Tarifas + todas capas   │
│  Visión P&G           ◄── Vision Tarifas + todas capas   │
│  Visión Imprimible    ◄── Vision Tarifas + P&G           │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Dependencias por Hoja (Detalle)

### Panel de Control General
**Depende de:**
- `Listas Desplegables` (SUM para número mes inicio en C3 de Nomina Loaded)
- `Rot, Ausent y Rentabilidad` (margen objetivo C63 por servicio)
- `Condiciones Cadena A` (FTE summary por canal L19:L25, L32:L39)
- `Tasas, TRM, Polizas` (no directamente, pero parametrización viene de ahí)

**Alimenta:**
- Todas las hojas de cálculo (es la fuente primaria)

---

### Inputs de Nomina
**Depende de:**
- `Tasas, TRM, Polizas!$B$4` (IPC para indexar salarios)
- `Condiciones Cadena A!$T$25:$T$48` (% comisión por cargo)
- `Condiciones Cadena A!$W25:$AK48` (ratios de staffing)

**Alimenta:**
- `Nomina Loaded` (costo empresa por cargo)
- `Condiciones Cadena A` (relación bidireccional de comisiones)

---

### Condiciones Cadena A
**Depende de:**
- `Panel de Control General` (FTE por canal, ausentismo, rotación)
- `Inputs de Nomina!$C$110:$H$133` (ratios de staffing por cargo)
- `Inputs de Nomina!$C$4` (SMMLV para salario base)

**Alimenta:**
- `Hoja Maestra Escenarios` (FTE por canal/modalidad → C13)
- `Nomina Loaded` (estructura de perfiles)
- `Visión P&G` (FTE para estaciones de trabajo)
- `Inputs de Nomina` (% comisión — circular resuelto por Excel)

**Fórmulas clave:**
```excel
E17: FTE por perfil (input directo usuario)
E19: =E17×E18  (estaciones presenciales = FTE × % presencial)
E25..S25: Ratios staffing = INDEX(Inputs_Nomina, MATCH(cargo, cargos), MATCH(perfil, perfiles))
W25..AK25: Ratio FTE = (FTE_agente/FTE_staff) [× rotacion si aplica]
```

---

### Nomina Loaded
**Depende de:**
- `Listas Desplegables` (mes inicio)
- `Panel de Control General` (duración, índices, fechas)
- `Condiciones Cadena A` (perfiles de equipo)
- `Inputs de Nomina` (costos laborales base)

**Alimenta:**
- `Costos Totales` (por perfil SUMIFS)
- `Vision Cost To Serve` (por sub-sección)
- `Visión P&G` (por sub-sección)
- `Hoja Maestra Escenarios` (por filtros canal/modalidad)

**Estructura interna:**
```
Row 15: TOTAL Inbound = D93+D238+D287+D349+D407+D182+D455
Row 93: Sección Salario Fijo Inbound
Row 182: Sección Estudios de Seguridad
Row 238: Sección Capacitación Rotación
Row 245+: Sección Capacitación Inicial
Row 287: Sección sub-cálculo 3
Row 349: Sección sub-cálculo 4
Row 407: Sección sub-cálculo 5
Row 455: Sección adicional (Outbound)
```

---

### No Payroll
**Depende de:**
- `Nomina Loaded` (fecha inicio)
- `Panel de Control General` (duración, índice tecnológico)

**Alimenta:**
- `Vision Cost To Serve!C46:C48` (OPEX fijo, inversiones, costos estación)
- `Visión P&G!C42:C44`

**Estructura interna:**
```
Row 14: TOTAL Inbound = D107+D186+D248
Row 107: OPEX Fijo Inbound
Row 186: Inversiones Inbound
Row 248: Costos Fijos x Estación Inbound
```

---

### Costo Fijo
**Depende de:**
- `Nomina Loaded` (fecha inicio)
- `Panel de Control General` (aumento componentes, mes aumento)

**Alimenta:**
- `Vision Cost To Serve` (OPEX fijo cadena B, inversiones, S&M)
- `Visión P&G!C47:C49`

**Estructura interna:**
```
Row 14: TOTAL Inbound = E53+D144+F195
Row 53: Sub-bloque OPEX Fijo
Row 144: Sub-bloque Inversiones
Row 195: Sub-bloque S&M
```

---

### Costo Variable (HIDDEN)
**Depende de:**
- `Panel de Control General` (volumetría por canal)

**Alimenta:**
- `Vision Cost To Serve!G42:G45` (tarifa, OPEX var, escalamiento, HITL)
- `Visión P&G!C51:C54`

**Filas clave:**
```
Row 49: Tarifa canal Inbound
Row 61: Tarifa canal Outbound  
Row 87: OPEX Variable Inbound
Row 113: OPEX Variable Outbound
Row 132: Tasa Escalamiento Inbound
Row 144: Tasa Escalamiento Outbound
Row 170: HITL Inbound
Row 182: HITL Outbound
```

---

### Costo Cadena C
**Depende de:**
- `Panel de Control General` (volumetría, flags cadenas activas)
- `Condiciones Cadena C` (parámetros proveedor)

**Alimenta:**
- `Vision Cost To Serve!K35:K43` (todas las sub-categorías de C)
- `Visión P&G!C56:C64`

**Filas clave (documentadas en Vision Cost To Serve):**
```
Row 115: Tarifa Proveedor Inbound
Row 143: OPEX C Inbound
Row 169: OPEX C Outbound
Row 197: OPEX Variable C Inbound
Row 224: OPEX Variable C Outbound
Row 290: Inversiones C Inbound
Row 315: Inversiones C Outbound
Row 332: Equipo integración Inbound
Row 333: Equipo integración Outbound
Row 405: Tasa Escalamiento C Inbound
Row 417: Tasa Escalamiento C Outbound
Row 444: HITL C Inbound
Row 457: HITL C Outbound
```

---

### Costos Totales (HIDDEN)
**Depende de:**
- `Nomina Loaded` (SUMIFS por perfil)
- `No payroll` (SUMIFS por perfil)

**Alimenta:**
- `Pólizas - Costo Financiacion` (base para ICA por canal)

**Fórmula tipo:**
```excel
E10: =SUMIFS('Nomina Loaded'!F:F,'Nomina Loaded'!$D:$D,$B10)
   + SUMIFS('No payroll'!F:F,'No payroll'!$D:$D,$B10)
```

---

### Pólizas - Costo Financiacion
**Depende de:**
- `Costos Totales` (base de costos por canal)
- `Panel de Control General` (margen A, reglas, período pago)
- `Tasas, TRM, Polizas` (tasas ICA por municipio)

**Alimenta:**
- `Hoja Maestra Escenarios` (ICA, GMF, comisión adm, pólizas)
- `Vision Cost To Serve` (componente financiero)
- `Visión P&G!C65:C70`

---

### Hoja Maestra Escenarios
**Depende de:** TODAS las hojas de cálculo  
**Alimenta:**
- `Vision Tarifas_Modelo_Cobro!C19:G21` (facturación y tarifas por escenario)
- `Vision Tarifas_Modelo_Cobro!C29 (escenario seleccionado)`

---

## 3. Patrón de Cálculo Mensual

La mayoría de hojas usa el mismo patrón para proyectar 60 meses:

```excel
# Fila de fechas:
E13: [fecha inicio]
F13: =EDATE(E13,1)
G13: =EDATE(F13,1)
...

# Fila de valores:
E{row}: [valor mes 1]
F{row}: =IF(mes<=duracion, valor_con_indexacion, 0)

# Indexación típica (Componente Humano):
factor = IF(mes >= mes_ajuste AND año_ajuste >= año_inicio,
            factor_acumulado_SMMLV_o_IPC, 1)
```

---

## 4. Ciclo Crítico (No Circular)

La relación `Condiciones Cadena A ↔ Inputs de Nomina` parece circular pero NO lo es:

1. `Inputs de Nomina!E16` lee `Condiciones Cadena A!$T$25` (comisión %)
2. `Condiciones Cadena A!E25` lee `Inputs de Nomina!$C$110:$H$133` (ratios)

Estas son tablas de referencia independientes: `T` son comisiones (input usuario), `C110:H133` son ratios estructurales (parámetros fijos). No hay circularidad real.
