# HARDCODES Y ANOMALÍAS — V2-7

---

## 1. Hardcodes Críticos (Deben parametrizarse)

### H1 — SMMLV 2026
- **Ubicación**: `Inputs de Nomina!C4`
- **Valor**: `1,750,905` COP
- **Problema**: Valor fijo; no se actualiza al cambiar de año
- **Backend**: `parametrization_provider` debe devolver este valor desde storage

### H2 — Auxilio de Transporte 2026
- **Ubicación**: `Inputs de Nomina!C5`
- **Valor**: `249,095` COP
- **Problema**: Fijo por año
- **Backend**: ídem H1

### H3 — IPC Hardcodeado en Crucero
- **Ubicación**: `Panel de Control General!C17`
- **Fórmula**: `=8000*(1+5.1%)`
- **Problema**: El 5.1% es IPC asumido sin leer de `Tasas, TRM, Polizas`. Si el IPC cambia, este valor no se actualiza.
- **Backend**: `calculators/nomina.py` debe leer IPC de parametrización

### H4 — Horas por Mes Base
- **Ubicación**: `Hoja Maestra Escenarios!J5`, hardcodeado como `42` horas semanales y `4.33` semanas
- **Valores**: 42 horas/semana, 4.33 semanas/mes, 8 horas formación/mes
- **Impacto**: Cálculo de minutos logueados y tarifas por tiempo
- **Backend**: `domain/constants.py` o parametrización HR

### H5 — Tiempos Improductivos
- **Ubicación**: `Hoja Maestra Escenarios!J13:J17`
- **Valores**: breaks=30min, deslogueos=5min, coaching=5min, pausa_activa=5min
- **Impacto**: Diferencia entre horas programadas y horas productivas
- **Backend**: Debe estar en parametrización HR (HR_productiva)

### H6 — IPC Unificado para Todos los Años
- **Ubicación**: `Tasas, TRM, Polizas!B4:G4`
- **Valor**: `0.0527` para todos los años 2025–2030
- **Problema**: IPC real varía año a año. V2-7 usa un solo valor como proxy.

### H7 — SMLV 2026 Diferenciado
- **Ubicación**: `Tasas, TRM, Polizas!C5`
- **Valor**: `0.2378` (23.78% de aumento para 2026)
- **Problema**: Los demás años usan 0.12; el 2026 es excepcionalmente alto
- **Riesgo**: Si se cambia año base, el cálculo de factor acumulado cambia drásticamente

### H8 — Factor Carga Prestacional SACO/Ventas
- **Ubicación**: `Panel de Control General!C139:G139`
- **Valor**: `0.42` (42%)
- **Backend**: `calculators/nomina.py` debe exponer este factor como parámetro

### H9 — Horas Base para Recargos
- **Ubicación**: `Inputs de Nomina` (fórmulas como `C/220`)
- **Valor**: `220` horas/mes base
- **Problema**: 220 es aproximación de 22 días × 10 horas, pero la jornada es 42h/sem
- **Backend**: verificar consistencia con 42h × 4.33 semanas = 181.86 horas reales

### H10 — GMF
- **Ubicación**: `Tasas, TRM, Polizas!B30`
- **Valor**: `0.004` (4×1000)
- **Backend**: `calculators/costos_financieros.py` debe leer de parametrización

### H11 — ICA Bogotá
- **Ubicación**: `Tasas, TRM, Polizas!F37`
- **Fórmula**: `=B37+C37+D37+E37` = 0.00966 + 0 + 0.01 + 0 = **0.01966**
- **Backend**: `calculators/costos_financieros.py` usa `ICA_RATE` = debe venir por ciudad

### H12 — Comisión de Administración
- **Ubicación**: `Tasas, TRM, Polizas!B28`
- **Valor**: `0.0118` (1.18%)
- **Activación**: `Panel!C45 = TRUE` (habilitada por defecto)
- **Backend**: `calculators/costos_financieros.py` → `COMISION_ADM_RATE`

### H13 — TMO Voz
- **Ubicación**: `Condiciones Cadena A!E8`
- **Valor**: `522.2` segundos
- **Backend**: Input de usuario, no hardcode en backend

### H14 — Salario Director de Cuentas
- **Ubicación**: `Inputs de Nomina!C16`
- **Valor**: `=18505000*(1+23%)` — el 23% es hardcode
- **Problema**: El factor de incremento salarial 23% no está vinculado al IPC/SMLV del año

### H15 — % Cumplimiento Variable
- **Ubicación**: `Inputs de Nomina!C6`
- **Valor**: `0.70` (70%)
- **Backend**: Parametrización HR

---

## 2. Anomalías del Modelo

### AN1 — Margen de Cadena C en Vision Tarifas vs P&G

**Descripción**: La fórmula de pricing en `Vision Tarifas_Modelo_Cobro!C67` usa **margen A** para Cadena C:
```excel
C67 = C60/((1-$G$35)*(1-$G$30)*(1-$G$31)*(1-$G$32)*(1+$G$33))
# G35 = Margen Cadena A (no Cadena C)
```
Pero en `Visión P&G!C21` se usa **margen C**:
```excel
C21 = IFERROR((C$55/(1-'Panel de Control General'!$E$63))*C$15, 0)
# E63 = 0.20 = Margen Cadena C
```
**Impacto**: Las tarifas de Vision Tarifas son diferentes a los ingresos implícitos en P&G para Cadena C.

### AN2 — Horas semanales en Vision Tarifas vs Hoja Maestra

`Vision Tarifas_Modelo_Cobro!C107:C109` repite las variables de tiempo (42h/sem, 8h formación, 4.33 semanas) pero en columna C (hardcoded), mientras `Hoja Maestra Escenarios` las tiene en columna J. Son consistentes por ahora pero cualquier cambio en uno no propagará al otro.

### AN3 — Duración hardcodeada en Tarifa FTE (Vision Tarifas)

```excel
# Vision Tarifas!G45:
G45 = G43/C37/12
# El "12" es hardcode, debería ser Panel!C11 (duración en meses)
```
Si la duración del contrato no es 12 meses, la tarifa FTE estará mal calculada.

**Hoja Maestra Escenarios usa correctamente:**
```excel
G21 = G19/C13/'Panel de Control General'!C11
```

### AN4 — Fórmula de Imprevistos Inconsistente

En `Panel de Control General!D73` hay el comentario "añadir luego de la tarifa para ver el ingreso total del deal", pero `Visión P&G!C26` ya lo aplica sobre el ingreso bruto:
```excel
C26 = C18 × Panel!C73
```
Y la fórmula de ingreso neto `C27 = C18 + SUM(C22:C24) - C25 - C26` resta los imprevistos.

**Inconsistencia**: Los imprevistos se restan del ingreso neto (reducen margen), pero conceptualmente deberían ser una contingencia que aumenta el precio. En Vision Tarifas, imprevistos NO están en la fórmula de pricing (sólo contingencias y markup).

### AN5 — Outbound con flag FALSE por defecto

`Panel!M30 = FALSE` (Cadena A Outbound desactivada por defecto).
`Panel!N30 = FALSE` (Cadena B Outbound desactivada por defecto).
`Panel!O30 = FALSE` (Cadena C Outbound desactivada por defecto).

El backend debe respetar estos flags. Si `M30=FALSE`, los costos de Outbound = 0 aunque haya FTE configurado en los canales Outbound.

### AN6 — Número de Mes Inicio en Listas Desplegables

```excel
# Nomina Loaded!C3 = SUM('Listas Desplegables'!$A$51:$BH$51)
```
El número del mes de inicio se calcula como suma sobre una fila de la hoja "Listas Desplegables". Esta es una forma no obvia de obtener un valor numérico desde una validación de lista. El backend usa directamente la fecha de inicio del Panel.

### AN7 — Inconsistencia en % Horas Pagadas

En `Hoja Maestra Escenarios!J24` (horas pagadas):
```excel
J24 = 0  # hardcoded a 0%
```
Esto significa `horas_pagadas = horas_programadas × (1 - 0%) = horas_programadas`.
Pero en `Vision Tarifas!C124`:
```excel
C124 = 0
```
Consistente, pero el campo existe como si pudiera configurarse. En la práctica, 0% de deducción por horas pagadas significa que TODAS las horas programadas se pagan.

### AN8 — Ausentismo en Nómina vs en Horas

El ausentismo se aplica en dos lugares:
1. En `Hoja Maestra Escenarios!J25` (cálculo de horas logueadas) → para la tarifa por tiempo
2. En `Panel!C19` → para el cálculo de capacitación de rotación en Nomina Loaded

Ambos usan el mismo valor de Panel!C19, pero la primera impacta la tarifa y la segunda impacta el costo.

### AN9 — Dotaciones: Factor 23% No Vinculado

```excel
# Inputs de Nomina!C7:
C7 = (50000/4)*12*(1+23%)
```
El 23% coincide con el SMLV 2026, pero NO está vinculado a `Tasas!C5`. Es hardcode.

### AN10 — Director de Cuentas: Costo Hardcodeado

```excel
AM16 = 29031301  # número fijo, no =W16
```
Para todos los demás cargos `AM{row} = W{row}`, pero para Director de Cuentas el costo empresa es un número absoluto. Esto rompe la dinámica de indexación.

---

## 3. Observaciones Sobre Redondeo

El Excel no usa `ROUND()` en ninguna fórmula de pricing o costos. Los valores se presentan con precisión flotante completa. El backend no debe redondear intermedios; sólo redondear en presentación de visiones.

---

## 4. Campos Vacíos con Impacto

| Campo | Condición | Comportamiento Excel | Impacto Backend |
|-------|-----------|---------------------|-----------------|
| Contingencia Operativa (C67) | = 0 | Sin contingencia | OK, no-op |
| Contingencia Comercial (C68) | = 0 | Sin contingencia | OK, no-op |
| Imprevistos (C73) | = 0 | Sin imprevistos | OK, no-op |
| Descuento Volumen (C70) | = 0 | Sin descuento | OK, no-op |
| Escenarios 4 y 5 | Vacíos | IFERROR → 0 | Backend debe manejar escenarios vacíos |
| Outbound flags | FALSE | Sin costos Outbound | Backend debe verificar cada flag |

---

## 5. WAVE 5 — Anomalía Director de cuentas / GTR Comisión

**Origen**: WAVE 4 Bug #4.

El Excel V2-7, hoja "Inputs de Nomina", columna E ("% Comisión recibido"),
contiene **0** en las filas:

| Rol | Fila Excel | Excel E | Spec negocio | Acción WAVE 4 |
|-----|-----------|---------|---------------|----------------|
| Director de cuentas | E16 | 0 | 5% | Override aplicado en `hr.json[nomina]` con flag `_wave4_business_override_comision=true` |
| GTR | E26 | 0 | 10% | Override aplicado en `hr.json[nomina]` con flag `_wave4_business_override_comision=true` |

**Justificación de la divergencia**: Los tests pre-existentes
(`tests/unit/test_tipos_carga.py::TestComisionPct::test_director_cuentas_comision_pct`
y `test_gtr_comision_pct`) **exigen** 0.05 y 0.10 respectivamente — esto refleja
la política comercial vigente. El Excel V2-7 **omite** estos valores en la
columna E (probable oversight de quien parametrizó la hoja).

**Decisión WAVE 5 (definitiva)**: Se mantiene el override marcado en `hr.json`
con `_wave4_business_override_comision`. Esto es **deliberado**, no un bug a
arreglar en el backend. Cualquier futura re-extracción del Excel debe
preservar el override (el script `wave4_resync_nomina.py` ya respeta valores
con flag de override en la metadata).

**Cómo eliminar la divergencia**:
1. Corregir el Excel V2-7 en E16=5% y E26=10%, y eliminar el flag de override
   en `hr.json`.
2. O bien mover formalmente estos valores a `business_rules.json[commissions]`
   y consumirlos desde ahí en lugar de `HR-Nomina`.
