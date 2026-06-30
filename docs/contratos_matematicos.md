# Contratos Matemáticos del Motor NEXA
**Versión:** 1.0  
**Fecha:** 2026-05-20  
**Propósito:** Especificación formal e inmutable de las operaciones matemáticas del motor. Cualquier cambio aquí debe revisarse contra el baseline y los tests determinísticos.

---

## 1. Convenciones generales

### 1.1 Tipos numéricos
- **Internamente:** `float` (IEEE 754 double precision)
- **Almacenamiento:** Storage JSON con precisión hasta 6 decimales
- **Reporting:** Round-half-even a 2 decimales para montos COP, 8 para ratios

### 1.2 Reglas de redondeo
- **`round()`**: Banker's rounding (round-half-even, Python default)
- **NO se usa**: `int()`, `math.floor()`, `math.ceil()` en valores financieros (excepto FTE→estaciones)
- **Acumulación**: Se acumula en `float` y se redondea **solo al exportar** o al cruzar fronteras de sistema (API, reporting)

### 1.3 Orden de operaciones
- Sigue la **prioridad estándar de matemática** (paréntesis explícitos en código)
- **NO se asume asociatividad** flotante: `(a + b) + c ≠ a + (b + c)` en general; se respeta el orden de la fórmula Excel
- **División**: `a / b` es la última operación de un componente; NUNCA se divide por valores acumulados que pueden ser cero (siempre check `> 0`)

### 1.4 Timing
- **Mes 1 = primer mes del contrato**, NO mes calendario
- **Financiación mes 1 = 0** (no hay mes previo)
- **Indexación**: factor año = 1.0 para año de inicio; crecimiento aplica desde `mes_aplicacion_aumento` (típicamente mes 13)

---

## 2. Fórmulas oficiales

### 2.1 Salario fijo (`EMPLEADO_ESTANDAR`)

```
salario_cargado = NominaCargadaService.calcular(salario_base, comision_pct)
factor_idx      = factor_indexacion_base × factor_aumento(mes)
total_cargado   = salario_cargado × FTE × factor_idx
comisiones      = salario_base × FTE × comision_pct × pct_cumplimiento × factor_idx
salario_fijo    = total_cargado − comisiones
```

**Fuente:** Excel V2-4 `Inputs Nomina!H39` (T.Haberes) + carga social en `I39:T39` (sumada por componente)

**Tipos de carga válidos:**
- `EMPLEADO_ESTANDAR` → `NominaCargadaService.calcular()` (Ley 1819 aplica)
- `APRENDIZ_SENA` → `NominaCargadaService.calcular_aprendiz()` (Ley 789, sin pensión/salud/ARL/ICBF)
- `EQUIPO_SOPORTE_MANTENIMIENTO` → `NominaCargadaService.calcular_sm()` (prestaciones sobre pensión)
- `SOPORTE_COMISIONABLE` → `calcular()` con `comision_pct > 0`
- `IMPLEMENTACION_PROYECTOS` → `calcular()` + FTE volumétrico

### 2.2 Carga social — Empleado estándar (con Ley 1819 ON)

```
t_imponible = salario_base × (1 + comision_pct × pct_cumplimiento)
aux         = auxilio_transporte if t_imponible < 2 × SMMLV else 0
t_haberes   = t_imponible + aux
umbral_alto = factor_alto_salario_smmlv × SMMLV     # 10 × SMMLV

if t_imponible > umbral_alto:        # alto salario
    factor    = factor_corrector_alto_salario        # 0.70
    salud     = t_imponible × tasa_salud    × factor # 8.5% × 0.7
    pension   = t_imponible × tasa_pension  × factor # 12% × 0.7
    arl       = t_imponible × tasa_arl      × factor
    caja      = t_imponible × tasa_caja     × factor # 4% × 0.7
    icbf_sena = t_imponible × tasa_icbf_sena× factor # 4% × 0.7
    vac_rate  = tasa_vacaciones             × factor
    # Prestaciones desactivadas para alto salario
    cesantias = primas = int_ces = 0
else:                                # bajo salario
    if aplica_ley_1819:
        salud     = 0                # exonerado
        icbf_sena = 0                # exonerado
    else:
        salud     = t_imponible × tasa_salud
        icbf_sena = t_imponible × tasa_icbf_sena
    pension   = t_imponible × tasa_pension
    arl       = t_imponible × tasa_arl
    caja      = t_imponible × tasa_caja
    vac_rate  = tasa_vacaciones
    cesantias = t_haberes × tasa_cesantias
    primas    = t_haberes × tasa_primas
    int_ces   = cesantias × tasa_interes_cesantia

vacaciones   = t_imponible × vac_rate
dotaciones   = dotaciones_mensual if t_imponible < 2 × SMMLV else 0
total_cargado = t_haberes + salud + pension + arl + caja + icbf_sena
              + cesantias + primas + int_ces + vacaciones + dotaciones
```

### 2.3 Capacitación inicial (amortizada)

```
cap_inicial = días_cap_inicial × tarifa_dia_cap × FTE × factor_idx / meses_contrato
```

### 2.4 Capacitación rotación

```
personas_nuevas = FTE × pct_rotacion
cap_rotacion    = días_cap_rotacion × tarifa_dia_cap × personas_nuevas × factor_idx
```

### 2.5 Exámenes médicos (3 componentes)

```
fte_efectivo = perfil.fte + sum(perfil.fte / ratio_rol  for rol in [
                "Formadores", "Monitor de Calidad", "Supervisor", "Validador"
              ] if ratio_rol > 0)

fraccion = 1/meses_contrato + pct_rotacion + pct_examen_anual/12

examenes = costo_examen_ciudad × fte_efectivo × fraccion × factor_idx
```

**Fuente:** Excel V2-4 `Nomina Loaded!C322:C324` (3 componentes: inicial + rotación + anual)

### 2.6 Crucero

```
crucero = costo_crucero × FTE × factor_idx
```

### 2.7 No Payroll (por estación)

```
estaciones = sum(p.fte for p in perfiles if not p.es_soporte)

# Si algún perfil tiene no_payroll_mensual override, sumar overrides (Excel V2-4)
override_opex = sum(p.no_payroll_mensual for p in perfiles
                    if not p.es_soporte and p.no_payroll_mensual > 0)

opex_ti = override_opex if override_opex > 0 else (opex_ti_por_estacion × estaciones)
capex_recurrente = capex_recurrente_por_estacion × estaciones
capex_inicial    = capex_inicial_por_estacion × estaciones if mes == 1 else 0
costos_fijos     = (arriendo + energia + vigilancia + aseo + otros_fijos) × estaciones

no_payroll = opex_ti + capex_recurrente + capex_inicial + costos_fijos
```

### 2.8 Cadena B (canal-based)

```
costo_b = sum_por_canal(opex_fijo + tarifa_unitaria × volumen_mensual + escalamiento)
        + sum(opex_consumo_variable.valor × cantidad)
        + costo_personal_sm × factor_idx
        + opex_herramientas_sm
        + inversion_mensual

donde costo_personal_sm = sum(
    calcular_sm(salario_rol) × pct_dedicacion × fte_equipo_sm
    for rol in equipo_sm if activo
)
```

### 2.9 Polizas (gross-up)

```
factor_margenes      = (1 − margen) × (1 − op_cont)
ingreso_antes_polizas = costo_op / factor_margenes
polizas              = (ingreso_antes_polizas + financiacion) × tasa_polizas_efectiva

donde tasa_polizas_efectiva = SUMPRODUCT(valor × atribucion) sobre OP-Poliza.aplica=True
```

### 2.10 ICA (gross-up)

```
ica = (costo_op / factor_margenes + polizas + financiacion) × tasa_ica
```

### 2.11 GMF (flat, sin gross-up)

```
gmf = (costo_op + polizas + financiacion) × tasa_gmf
```

### 2.12 Financiación (Excel V2-4 convention)

```
factor_periodo = periodo_pago_dias / 30                          # 30 days = 1 mes
if mes == 1:
    financiacion = 0                                              # no hay mes previo
else:
    financiacion = costo_op_mes_anterior × tasa_financ × factor_periodo
```

### 2.13 P&G mensual

```
costo_total       = payroll_a + no_payroll_a + costo_b + costo_c + polizas + ica + gmf + financiacion
ingreso_bruto_a   = (payroll_a + no_payroll_a) × (1 + margen) × rampup
ingreso_bruto_b   = costo_b × (1 + margen) × rampup
ingreso_bruto_c   = costo_c × (1 + margen) × rampup
contingencia_op   = ingreso_bruto × op_cont
contingencia_com  = ingreso_bruto × com_cont
markup_monto      = ingreso_bruto × markup
descuento_monto   = ingreso_bruto × descuento
ingreso_neto      = ingreso_bruto + contingencia_op + contingencia_com + markup_monto - descuento_monto
utilidad_neta     = ingreso_neto - costo_total
pct_utilidad_neta = utilidad_neta / ingreso_neto
```

### 2.14 FTE volumétrico (Especialista de Proyectos)

```
# Excel V2-4 W48 = SUM(W44:W45) / SUM($W$44:$AK$45)
# Backend simplificación con ratio calibrado:
fte_volumetrico = fte_agente / ratio_calibrado    # ratio = 24.76 para WhatsApp+Validador en multi-canal
```

### 2.15 FTE Aprendiz SENA

```
# Excel V2-4 W46 = SUM(W25:W44) / E46
# SUM(W25:W44) excluye Validador (W45) y Especialista (W48)
fte_sena = (fte_agente + sum_soporte_BASE) / ratio_sena

donde sum_soporte_BASE excluye {Validador, Especialista de Proyectos, Aprendiz SENA, Inclusión}
```

---

## 3. Orden de cálculo (pipeline)

El motor `NexaPricingEngine.calcular()` ejecuta en este orden estricto:

```
1. NominaCalculator.calcular_para_mes(perfiles, mes)
   ↓
2. NoPayrollCalculator.calcular_para_mes(perfiles, mes)
   ↓
3. CadenaBCalculator.calcular_para_mes(...)
   ↓
4. CadenaCCalculator.calcular_para_mes(...)
   ↓
5. CostosTotalesCalculator → costo_op = sum(a+b+c)
   ↓
6. CostosFinancierosCalculator.calcular(costo_op, mes, costo_op_mes_anterior)
   • financiación PRIMERO (depende solo de mes anterior)
   • luego polizas (con gross-up y financiación)
   • luego ica (con gross-up y polizas + financiación)
   • finalmente gmf (flat sobre costo + polizas + financiación)
   ↓
7. PyGCalculator.calcular_mes(...) — encadena costo_anterior para mes+1
   ↓
8. KPIsCalculator.calcular(pyg_completo)
   ↓
9. CostToServeCalculator
   ↓
10. VisionTarifasCalculator
```

**Invariante de pipeline:** El orden NO debe cambiar. Cualquier reordenamiento afectará la financiación (que depende del mes anterior) y las polizas/ICA (que dependen de la financiación).

---

## 4. Indexación temporal (IPC, SMLV, etc.)

### 4.1 Factor base = 1.0 (año inicio del contrato)

```
factor_indexacion_base = 1.0
```

**Justificación:** El Excel V2-4 trata el año de inicio del contrato como base (`Tasas, TRM, Polizas!B8 = 1.0`). Los salarios storage ya están en moneda del año de inicio.

### 4.2 Factor de aumento por mes

```
def calcular_factor_aumento(mes, pct_aumento_salarial, mes_aplicacion_aumento):
    # Número de años cumplidos desde mes_aplicacion:
    anios_completos = (mes - mes_aplicacion_aumento) // 12 + 1 if mes >= mes_aplicacion_aumento else 0
    return (1 + pct_aumento_salarial) ** anios_completos
```

**Ejemplo:** contrato 24 meses, IPC anual=5.27%, mes_aplicacion=13.
- Meses 1-12: factor = 1.0 (sin aumento)
- Meses 13-24: factor = 1.0527 (aumento año 2)

---

## 5. Cascadas de redondeo

### 5.1 Sin redondeo intermedio
Los componentes (`salario_fijo`, `comisiones`, `cap_inicial`, etc.) se acumulan en `float` sin redondeo.

### 5.2 Redondeo solo en frontera de sistema
- **API output:** `round(x, 2)` para montos COP, `round(x, 8)` para ratios
- **Storage:** se preserva precisión completa (hasta 6+ decimales en JSON)
- **CLI/reporting:** formato de presentación, no de cálculo

---

## 6. Reglas de precisión

### 6.1 Comparación de igualdad
```python
# NUNCA usar:
if a == b: ...                # falla por flotante

# SIEMPRE usar:
if abs(a - b) < 1e-9: ...     # tolerancia
```

### 6.2 División segura
```python
denom = factor_margenes  # puede ser 0
result = (x / denom) if denom > 1e-9 else 0.0
```

### 6.3 Acumuladores
- Sum en `sum()` o list-comprehension
- No usar `+=` en loops largos (precisión flotante drift)

---

## 7. Contratos por componente

| Componente | Función | Idempotencia | Determinismo |
|-----------|---------|-------------|--------------|
| `NominaCalculator._salario_fijo` | (perfil, mes) → float | ✅ | ✅ Mismo input → mismo output |
| `_comisiones` | (perfil, mes) → float | ✅ | ✅ |
| `_examenes` | (perfil, mes) → float | ✅ | ✅ |
| `CostosFinancierosCalculator.calcular` | (costo_op, mes, costo_anterior) → CFM | ✅ | ✅ |
| `PyGCalculator.calcular_contrato` | (perfiles) → list[PyG] | ✅ | ✅ |

**Garantía:** Dadas las mismas entradas (storage + user_input), el motor produce **bit-exact mismas salidas**.

---

## 8. Test de invariantes (en suite determinística)

```python
def test_pct_utilidad_match_excel():
    """% utilidad neta debe matchear Excel V2-4 a 4 decimales."""
    ui = load("bancamia_whatsapp_only.json")
    res = run_pipeline(ui)
    assert abs(res.pyg_por_mes[0].pct_utilidad_neta - (-0.0172)) < 0.0001
    assert abs(res.pyg_por_mes[2].pct_utilidad_neta - (0.1354)) < 0.0001

def test_payroll_a_exact_match():
    """payroll_a mes 1 debe matchear Excel V2-4 al peso."""
    ui = load("bancamia_whatsapp_only.json")
    res = run_pipeline(ui)
    assert abs(res.pyg_por_mes[0].payroll_a - 30_017_217) < 1.0

def test_financiacion_mes_1_zero():
    """Financiación mes 1 siempre = 0 (no hay mes previo)."""
    ui = load(any_case)
    res = run_pipeline(ui)
    assert res.pyg_por_mes[0].financiacion == 0.0
```

---

## 9. Migración entre versiones

Si una fórmula cambia (por ley o por decisión de negocio):

1. **Bumpear `schema_version`** en este documento
2. **Actualizar baseline** vía `python scripts/generate_baseline.py`
3. **Documentar cambio** con razón legal/operativa
4. **Validar con tests** — todo el suite debe pasar con la nueva fórmula

**Cambios prohibidos sin revisión:**
- Tasas legales (Salud, Pensión, ARL, Caja, ICBF+SENA, Cesantías, Primas, Vacaciones)
- Umbrales de Ley 1819 (10 SMMLV, factor 0.7)
- Convención de auxilio de transporte (< 2 SMMLV)
- Orden de pipeline

**Cambios permitidos sin revisión:**
- Valor numérico de tasas en storage (con doc de fuente legal)
- Ratios HR por línea/canal
- Comisiones por rol (HR-Nomina.ComisionPct)
- Atribuciones de pólizas (OP-Poliza)
