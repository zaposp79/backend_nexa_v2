# TRAZABILIDAD INVERSA DESDE VISIONES — V2-7

> Metodología: cada celda crítica de salida → sus dependencias → hasta el input primario.

---

## 1. Vision Tarifas — Celda C72: Facturación Total

**Celda:** `Vision Tarifas_Modelo_Cobro!C72`  
**Fórmula:** `=IFERROR(C47,0)+IFERROR(C57,0)+C67`

### Nivel 1 — Componentes de Facturación Total

#### C47: Ingreso Total Cadena A
```excel
=C40/((1-$G$35)*(1-$G$30)*(1-$G$31)*(1-$G$32)*(1+$G$33))
```
Donde:
- `C40` = Costo Directo Cadena A (sum C41:C46)
- `G35` = Margen Cadena A = `'Panel de Control General'!$C$63 + SUM(G30:G33)`
- `G30` = Contingencia Operativa = `'Panel de Control General'!$C$67`
- `G31` = Contingencia Comercial = `'Panel de Control General'!$C$68`
- `G32` = Mark up = `'Panel de Control General'!$C$69`
- `G33` = Descuento volumen = `'Panel de Control General'!$C$70`

**Fórmula matemática:**
```
Ingreso_A = CostoDirecto_A / ((1 - margen_A) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento))
```

#### C57: Ingreso Total Cadena B
```excel
=C50/((1-$G$36)*(1-$G$30)*(1-$G$31)*(1-$G$32)*(1+$G$33))
```
Idéntica estructura a C47 pero con Margen Cadena B (`G36 = 'Panel de Control General'!D63 + SUM(G30:G33)`).

#### C67: Ingreso Total Cadena C
```excel
=C60/((1-$G$35)*(1-$G$30)*(1-$G$31)*(1-$G$32)*(1+$G$33))
```
Usa margen Cadena A (`G35`) como base del margen de Cadena C también.

---

### Nivel 2 — Costo Directo Cadena A (C40 = SUM C41:C46)

| Celda | Componente | Fórmula base |
|-------|-----------|--------------|
| C41 | Payroll | ARRAY: suma nómina loaded filtrada por escenario/canal |
| C42 | No Payroll | ARRAY: suma no payroll filtrada |
| C43 | ICA | ARRAY: ICA sobre costos totales |
| C44 | GMF | ARRAY: GMF sobre facturación |
| C45 | Polizas | ARRAY: suma pólizas activas |
| C46 | Costos financiación | ARRAY: costo financiero por período pago |

**C41 — Payroll (detalle):**
```excel
=SUMIFS('Nomina Loaded'!$D$xxx:$BK$xxx, filtros_canal_modalidad) / 'Panel de Control General'!$C$11
```
Fuente: `Nomina Loaded` por filas específicas de sub-sección (ver sección Nómina).

**C43 — ICA:**
```excel
ICA = costos_base × tasa_ICA_ciudad
```
Tasa ICA viene de `'Tasas, TRM, Polizas'!$F$xx` según ciudad del `'Panel de Control General'!$C$12`.  
Bogotá = 0.00966 + 0.01 (S. Bomberil) = 0.01966

**C44 — GMF:**
```excel
GMF = facturación × 0.004
```
Hardcode: `'Tasas, TRM, Polizas'!$B$30` = 0.004

---

### Nivel 3 — Nómina Loaded (fuente de C41)

`Nomina Loaded!D15` = suma total inbound mes 1:
```excel
=D93+D238+D287+D349+D407+D182+D455
```
Cada sumando es una sub-sección de costos laborales por perfil.

**Estructura interna de Nomina Loaded:**
- Filas ~15–92: Inbound (sección principal de agentes operativos)
- Filas ~93–181: Sub-sección Capacitación Inicial Inbound
- Filas ~182–237: Sub-sección Exámenes Médicos
- Filas ~238–286: Sub-sección Capacitación Rotación
- Filas ~287–348: Sub-sección Estudios de Seguridad
- Filas ~349–406: Sub-sección Crucero
- Filas ~455+: Sub-sección adicional (Outbound equivalente)

**Fórmula de nómina por perfil:**
```excel
=IF(perfil<>"", costo_empresa_x_mes × ratio_staffing × indexacion_mes, 0)
```

Donde:
- `costo_empresa_x_mes` viene de `Inputs de Nomina!AM{row}` (costo empresa total)
- `ratio_staffing` viene de `Condiciones Cadena A!W{row}` (FTE_agentes / FTE_staff)
- `indexacion_mes` = factor IPC/SMLV según mes y tipo de indexación elegida

---

### Nivel 4 — Inputs de Nomina (fuente de costo empresa)

**Costo empresa por cargo (columna AM):**
```excel
AM{row} = W{row}   (para la mayoría de cargos)
         = hardcode (Director de Cuentas = 29,031,301 COP)
```

**W{row} = Carga Prestacional Total:**
```excel
W = M + P + U + V
```
Donde:
- `M` = Seguridad Social Empleado = `H + I + J + L` (Salud + Pensión + ARL×2)
- `P` = Parafiscales = `N + O` (Caja + ICBF/Sena)
- `U` = Prestaciones = `Q + R + S + T` (Cesantías + Primas + Interés + Vacaciones)
- `V` = Dotaciones = `IF(salario < 2×SMMLV, dotacion_mensual, 0)`

**H = T. Haberes:**
```excel
H = F + G + AL
```
Donde:
- `F = C + D` (salario base + variable/comisión)
- `G = IF(F < 2×SMMLV AND F > 0, auxilio_transporte, 0)` = 249,095 COP
- `AL = X + Z + AB + AD + AF + AH + AJ` (suma recargos)

**Recargos (fórmula tipo):**
```excel
X = (C/220) × Y × 0.90    # recargo festivo
Z = (C/220) × AA × 0.90   # recargo dominical
AB = (C/220) × AC × 0.35  # recargo nocturno
```
Base de cálculo: 220 horas/mes (hardcode)

**Salud (I):**
```excel
I = IF(F > 10×SMMLV, F×8.5%×70%, 0)
```
Nota: empleados con salario > 10 SMMLV: exención del 30% de la base → base = salario × 70%

**Pensión (J):**
```excel
J = IF((H-G) > 10×SMMLV, (H-G)×12%×70%, (H-G)×12%)
```

---

## 2. Hoja Maestra Escenarios — Celda C47: Facturación Escenario 1

**Fórmula:** `=C23+C33+C43`

### C23: Ingreso Cadena A (Escenario 1)
```excel
=C16/((1-$G$11)*(1-$G$6)*(1-$G$7)*(1-$G$8)*(1+$G$9))
```
Misma estructura matemática que Vision Tarifas C47.

### C16: Costo Directo Cadena A (Escenario 1)
```excel
=SUM(C17:C22)
```
- C17: Payroll (ARRAY formula)
- C18: No Payroll (ARRAY formula)
- C19: ICA (ARRAY formula)
- C20: GMF (ARRAY formula)
- C21: Pólizas (ARRAY formula)
- C22: Costos financiación (ARRAY formula)

### G21: Tarifa por FTE (Componente Fijo)
```excel
=IFERROR(IF(C10="FTE", G19/C13/'Panel de Control General'!C11, G19/L26/'Panel de Control General'!C11), 0)
```
Donde:
- `G19` = Ingreso Componente Fijo = `C47 × D10` (facturación × proporción fija)
- `C13` = FTE total (suma de FTE por canal filtrado)
- `L26` = Minutos logueados = `K26 × 60`

### G31: Tarifa por Transacción (Componente Variable)
```excel
=IFERROR(CHOOSE(MATCH(C5, {"Escenario 1";"Escenario 2";...}, 0),
    'Hoja Maestra Escenarios'!G31,
    'Hoja Maestra Escenarios'!G79,
    ...), 0)
```

### G33: Volumen Mínimo de Transacción
```excel
=IF(C11="Transacción",
    (SUM(C16,C26,C36)*D11)/G31,
    (G29+G31)/'Vision Tarifas_Modelo_Cobro'!$C$133)
```

---

## 3. Vision Cost To Serve — B19: Ingreso Mensual

**Fórmula:** `=IFERROR('Vision Tarifas_Modelo_Cobro'!$C$72, 0)`

### H19: Cost to Serve Mensual
```excel
=('Vision Tarifas_Modelo_Cobro'!C40 + 'Vision Tarifas_Modelo_Cobro'!C50 + 'Vision Tarifas_Modelo_Cobro'!C60)
```
Suma de costos directos de las 3 cadenas.

### N19: Margen del Deal
```excel
='Panel de Control General'!C63
```
Margen objetivo directo del panel.

### G49: CTS Ponderado
```excel
=(C34×C31) + (G34×G31) + (K34×K31)
```
Donde C31, G31, K31 son las participaciones de Cadena A, B, C respectivamente.

---

## 4. Visión P&G — Cadena de Ingreso Neto

### C27: Ingreso Neto Mensual (mes 1)
```excel
=C18+SUM(C22:C24)-C25-C26
```

### C18: Ingreso Bruto
```excel
=C19+C20+C21+C71
```

### C19: Ingreso Cadena A (mes 1)
```excel
=IFERROR((C31/(1-'Panel de Control General'!$C$63)) × C15, 0)
```
Donde:
- `C31` = Costos Cadena A mes 1 (suma Payroll + No Payroll)
- `C15` = Factor de Ramp-up del mes 1
- `C63` = Margen objetivo Cadena A

**Fórmula matemática:**
```
Ingreso_A_mes = (Costo_A_mes / (1 - margen_A)) × ramp_up_factor
```

### C15: Factor de Ramp-up
```excel
=IFERROR(INDEX('Rot, Ausent y Rentabilidad'!$B$38:$BI$43,
    MATCH('Panel de Control General'!$C$5, 'Rot, Ausent y Rentabilidad'!$A$38:$A$43, 0),
    MATCH(C$11, 'Rot, Ausent y Rentabilidad'!$B$37:$BI$37, 0)), 1)
```
Lookup de tabla ramp-up: servicio × mes del contrato → factor (0.85 mes 1, 0.92 mes 2, 1.0 mes 3+)

### C74: Contribución (Utilidad Bruta)
```excel
=C27-C30
```

### C76: % Contribución
```excel
=IFERROR(C74/C27, 0)
```

### C79: Utilidad Neta
```excel
=C27-C30-C78
```
Donde C78 = Costo Fijo adicional (actualmente 0).

### BK27: Valor Total del Contrato (referenciado desde CTS)
Suma acumulada de C27:BJ27 (ingresos netos de los 60 meses).

---

## 5. ICA — Fórmula en Pólizas (Trazabilidad Completa)

**Pólizas - Costo Financiacion!E12** (ICA Inbound Voz mes 1):
```excel
=IF('Costos Totales'!E$8 <= ('Panel de Control General'!$C$11 + 'Nomina Loaded'!$C$3 - 1),
    (('Costos Totales'!E37 / ((1-'Panel de Control General'!$C$63)*(1-'Panel de Control General'!$C$67)*(1-'Panel de Control General'!$C$68)*(1-'Panel de Control General'!$C$69)*(1+'Panel de Control General'!$C$70)))
    × ICA_rate), 0)
```

Flujo: `Costos Totales` (por canal) → aplica markup/margen para obtener ingreso → aplica tasa ICA.

---

## 6. Ratio de Staffing (Condiciones Cadena A → Inputs de Nomina)

**Condiciones Cadena A!W25** (ratio Director de Cuentas para perfil Inbound 25):
```excel
=IFERROR(IF(OR($V25=$V$38, $V25=$V$39),
    (E$17/E25) × 'Panel de Control General'!$C$20,
    (E$17/E25)), 0)
```
Donde:
- `E17` = FTE de agentes del canal
- `E25` = FTE del cargo staff (Director de Cuentas)
- `$C$20` = % de Rotación (0.085)
- `V38`, `V39` = roles afectados por rotación (Reclutamiento, Capacitación)

**Fórmula matemática:**
```
ratio = FTE_agentes / FTE_staff_cargo
      × rotacion_factor  (solo para roles Reclutamiento/Capacitación)
```

**E25 — FTE del cargo en tabla de ratios:**
```excel
=IF(AND($D25=$D$35, $B$35=8, $C$35=TRUE, E$16<>""), 200,
 IF(AND($C25=TRUE, E$16<>""),
    INDEX('Inputs de Nomina'!$C$110:$H$133,
          MATCH($D25, 'Inputs de Nomina'!$B$110:$B$133, 0),
          MATCH(E$16, 'Inputs de Nomina'!$C$109:$H$109, 0)),
 0))
```
Lookup en tabla de ratios de `Inputs de Nomina` (filas 110–133).
