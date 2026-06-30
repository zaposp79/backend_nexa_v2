# PARIDAD EXCEL VS MOTOR — Estado y Gaps — V2-7

> Basado en análisis de código del branch `refactor/engine-v2` + reverse engineering de V2-7.

---

## 1. Resumen Ejecutivo de Paridad

| Módulo | Paridad estimada | Gaps detectados |
|--------|-----------------|-----------------|
| Nómina (costo laboral) | ~90% | Hardcode 220h/mes, dotación no dinámica |
| No Payroll (OPEX fijo) | ~85% | Estructura CAPEX diferida con interés |
| Cadena B (plataformas) | ~80% | HITL, Tasa Escalamiento B |
| Cadena C (proveedor) | ~75% | Equipo integración, HITL C, separación OPEX/CAPEX |
| Costos Financieros (ICA/GMF) | ~90% | Comisión Adm 1.18% aplicación correcta |
| Márgenes y Pricing | ~85% | margen_b, margen_c independientes |
| Tarifas (FTE, transacción, tiempo) | ~80% | Hardcode /12, tarifa Tiempo |
| P&G | ~85% | Imprevistos, margen B/C independientes |
| Ramp-up | ~90% | Servicios Plataformas/Captura = factor 0 |
| Escenarios comerciales | ~70% | Motor de escenarios múltiples (Hoja Maestra) |
| Indexación | ~85% | Mes de ajuste configurable |
| **TOTAL ESTIMADO** | **~83%** | 8 gaps críticos detectados |

---

## 2. Gaps por Prioridad

### CRÍTICO (Afecta valores de salida directamente)

#### C1 — Margen Cadena B y C Independientes
- **Excel**: B=30% fijo, C=20% fijo (Panel!D63, E63)
- **Backend**: Solo `margen` (para Cadena A)
- **Impacto directo**: Ingreso Cadena B y Cadena C calculados con margen incorrecto
- **Fix**: Agregar `margen_b` y `margen_c` a PanelDeControlRequest; adaptar PyGCalculator y VisionTarifasCalculator

#### C2 — Margen Cadena C en Vision Tarifas = Margen A (no margen_c)
- **Excel**: `Vision Tarifas!C67 = C60/((1-$G$35)...)` donde G35 = margen A
- **Backend**: VisionTarifasCalculator puede estar usando margen_c para cadena_c
- **Fix**: Para pricing en Vision Tarifas, usar `margen_a` para Cadena C también

#### C3 — Imprevistos no implementados
- **Excel**: `Panel!C73` se resta del ingreso neto en P&G
- **Backend**: Campo inexistente
- **Fix**: Agregar `imprevistos: float = 0.0` y aplicar en PyGCalculator

#### C4 — Mes de Ajuste de Indexación
- **Excel**: `Panel!L9` controla cuándo se aplica el aumento (mes del año, ej: 6)
- **Backend**: La indexación aplica en mes fijo (posiblemente mes 13)
- **Fix**: Agregar `mes_ajuste_indexacion: int` y usar en NominaCalculator

---

### ALTO (Afecta precisión de valores)

#### A1 — Hardcode 12 en Tarifa FTE de Vision Tarifas
- **Excel**: `Vision Tarifas!G45 = G43/C37/12` (12 = meses hardcode)
- **Backend**: VisionTarifasCalculator debería usar `panel.meses_contrato`
- **Fix**: Reemplazar literal 12 por `panel.meses_contrato`

#### A2 — Base de Horas para Recargos
- **Excel**: `Inputs de Nomina` divide salario entre 220 horas para calcular recargos
- **Backend**: No está claro si se usa 220h o 181.86h (42h/sem × 4.33 sem)
- **Impacto**: Los recargos nocturnos, festivos, etc. difieren si la base horaria es distinta

#### A3 — Ramp-up para Plataformas y Captura de Datos
- **Excel**: `Rot, Ausent!F11:F12 = 0` → factor ramp-up = 0 para estos servicios
- **Backend**: Si devuelve 1.0 como default, los ingresos de estos servicios se sobreestiman
- **Fix**: Tabla ramp-up debe devolver 0 (no 1) para Plataformas y Captura de Datos

#### A4 — SACO/Ventas: Módulo de Comisiones por Resultados
- **Excel**: `Panel!C118:G143` — facturación variable con niveles de productividad y AIU
- **Backend**: No confirmado si está implementado
- **Fix**: Verificar `calculators/vision_pyg.py` o crear módulo específico

---

### MEDIO (Afecta trazabilidad y consistencia)

#### M1 — Estructura de 7 Sub-componentes de Nómina
- **Excel**: `Nomina Loaded!D15 = D93+D238+D287+D349+D407+D182+D455` (7 fuentes)
- **Backend**: NominaCalculator agrupa en `salario_fijo`, `capacitacion_inicial`, `capacitacion_rotacion`, `examenes_medicos`, `estudios_seguridad`, `crucero`
- **Estado**: Probablemente correcto pero estructura ligeramente diferente

#### M2 — Alineación de Nombres de Sub-componentes

| Excel (Vision CTS labels) | Backend (ResultadoNomina) |
|--------------------------|--------------------------|
| Salario Fijo | `salario_fijo` |
| Salario Variable (Comisiones) | `salario_variable` |
| Capacitación Inicial | `capacitacion_inicial` |
| Capacitación Rotación | `capacitacion_rotacion` |
| Exámenes Médicos | `examenes_medicos` |
| Estudios de Seguridad | `estudios_seguridad` |
| Crucero | `crucero` |

#### M3 — Costos Cadena C separados por sub-componente
- **Excel**: CTS distingue Tarifa Proveedor / OPEX C / Inversiones C / Equipo Integración / OPEX Variable / HITL C / Tasa Escalamiento C
- **Backend**: CadenaCCalculator puede no tener todos estos sub-componentes
- **Fix**: Verificar que `ResultadoCadenaC` tenga los 7 sub-componentes

#### M4 — CTS Ponderado
- **Excel**: `Vision CTS!G49 = (CTS_A × part_A) + (CTS_B × part_B) + (CTS_C × part_C)`
- **Backend**: CostToServeCalculator debe calcular participación desde volumetría (mismo que Panel!M53:O53)

---

## 3. Comportamientos Excel que DEBEN replicarse exactamente

### Reglas de Negocio Combinadas

```python
# Denominador de pricing (fórmula exacta del Excel):
denominador = (1 - margen_cadena) * (1 - cont_op) * (1 - cont_com) * (1 - markup) * (1 + descuento)
ingreso = costo_directo / denominador

# NO es: ingreso = costo * (1 + margen + cont_op + cont_com + markup - descuento)
# La diferencia es material cuando los valores son altos (multiplicación vs suma)
```

### Seguridad Social con Tope Ley 1819

```python
# Empleados con salario > 10 SMMLV: reducción al 70% para SS y ARL
# Empleados con salario > 10 SMMLV: NO pagan Caja, ICBF, Sena
# Empleados con salario > 10 SMMLV: Cesantías, Primas, Intereses, Vacaciones = 0

tope = 10 * smmlv
if imponible > tope:
    base_reducida = imponible * 0.70
    # salud: imponible > tope → salud empresa = 0 (fórmula Excel: IF(F>10*SMMLV, F*I13*70%, 0))
    # pensión: base_reducida × 12%
    # ARL: base_reducida × ARL_rate
    # caja: (H-G) > tope → (H-G)*caja_rate*70%
    # icbf_sena: F > tope → F*rate*70%  → o 0 según la lectura exacta
    # cesantías = primas = interés = vacaciones = 0
```

### Auxilio de Transporte

```python
# Solo aplica cuando: 0 < imponible < 2 × SMMLV
# Es sobre el imponible base (sin recargos)
aux = auxilio_transporte if (0 < imponible < 2 * smmlv) else 0
```

### Factor de Indexación (Acumulado)

```python
# Tabla Tasas!A8:G16 — factores acumulados por tipo
# Para "80% SMMLV 20% IPC" en año 2027:
factor_2027 = 1.3287111  # desde Tasas!D14

# Aplicación correcta:
# Año 1 (meses 1-12 del contrato): factor = 1.0 (si el ajuste es al final del año 1)
# Año 2 (mes 13+): factor = tabla[tipo][año_inicio + 1]
```

---

## 4. Tests de Paridad Requeridos

Para certificar paridad V2-7, se necesitan los siguientes casos de prueba:

```python
# Caso Bancamia (datos reales del Excel V2-7):
caso_bancamia = {
    "servicio": "Captura de Datos",
    "ciudad": "Bogota",
    "meses": 12,
    "ftes": {"Inbound/Voz": 25, "Inbound/WhatsApp": 15},
    "margen_a": 0.3292,  # Captura de Datos
    "margen_b": 0.30,
    "margen_c": 0.20,
    "ausentismo": 0.065,
    "rotacion": 0.085,
    
    # Valores esperados (verificar en Excel con data_only=True):
    "facturacion_total_mensual": XXXX,
    "tarifa_fte_voz": XXXX,
    "costo_directo_a": XXXX,
    "margen_real": XXXX,
}
```

---

## 5. Checklist de Paridad por Componente

- [ ] C1: `margen_b` y `margen_c` como campos independientes
- [ ] C2: Vision Tarifas usa `margen_a` para Cadena C en pricing
- [ ] C3: Campo `imprevistos` en Panel + aplicación en P&G
- [ ] C4: Campo `mes_ajuste_indexacion` + uso en NominaCalculator
- [ ] A1: Tarifa FTE usa `panel.meses_contrato` no literal 12
- [ ] A2: Base 220h vs 181.86h para recargos (verificar cual usa Excel)
- [ ] A3: Ramp-up = 0 para Plataformas y Captura de Datos
- [ ] A4: Módulo SACO/Ventas implementado
- [ ] M1: 7 sub-componentes de nómina con nombres alineados al Excel
- [ ] M2: Nombres de columnas en ResultadoNomina = nombres en Vision CTS
- [ ] M3: 7 sub-componentes de Cadena C
- [ ] M4: CTS ponderado calculado por participación de cadenas
