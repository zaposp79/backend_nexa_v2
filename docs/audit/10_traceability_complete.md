# Fase 10 — Documentación de Trazabilidad Completa

**Date**: 2026-05-21  
**Status**: ✅ COMPLETE — Trazabilidad 100% documentada  
**Cobertura**: entry_data → domain → calculadoras → visiones → serializer → endpoints → frontend

---

## Tabla de Contenidos

1. [Arquitectura de Flujo por Capas](#1-arquitectura-de-flujo-por-capas)
2. [Capa 1: Entry Data Contract (entry_data)](#2-capa-1-entry-data-contract)
3. [Capa 2: Context Builder (adapters/context_builder.py)](#3-capa-2-context-builder)
4. [Capas 3-10: Pipeline de Calculadoras](#4-capas-3-10-pipeline-de-calculadoras)
5. [Capa 11: Visiones y Agregados](#5-capa-11-visiones-y-agregados)
6. [Capa 12: Serialización (pricing_serializer.py)](#6-capa-12-serializacion)
7. [Capa 13: Endpoints REST](#7-capa-13-endpoints-rest)
8. [Trazabilidad de @property Fields](#8-trazabilidad-de-property-fields)
9. [Dependencias Intermensuales](#9-dependencias-intermensuales)
10. [Versionado de Parametrización](#10-versionado-de-parametrizacion)
11. [Contratos Oficiales de Entrada/Salida](#11-contratos-oficiales-de-entradasalida)
12. [Valores Derivados Fuera de Calculadoras](#12-valores-derivados-fuera-de-calculadoras)

---

## 1. Arquitectura de Flujo por Capas

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  FLUJO COMPLETO NEXA SIMULATOR — Trazabilidad Entrada → Salida                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

ENTRADA (Frontend / API)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  CAPA 0: entry_data (JSON)                          │
│  4 secciones: panel_de_control, condiciones_a/b/c   │
│  Archivo: adapters/json_loader.py                   │
│  Modelo: domain/user_inputs.py                      │
└─────────────────────────────────────────────────────┘
    │ UserInput
    ▼
┌─────────────────────────────────────────────────────┐
│  CAPA 1: Context Builder                            │
│  Archivo: adapters/context_builder.py               │
│  Responsabilidad: UserInput + ParametrizationProvider│
│     → PricingRequest                                │
│  Outputs: PanelDeControl, PerfilCadenaA[],          │
│           ParametrosNomina, ParametrosNoPayroll,     │
│           ParametrosCadenaB, ParametrosCadenaC       │
└─────────────────────────────────────────────────────┘
    │ PricingRequest
    ▼
┌─────────────────────────────────────────────────────┐
│  MOTOR (engine.py) — Composition Root               │
│  Instancia y conecta todos los calculadores         │
│  Orquesta el pipeline de 10 capas                   │
└─────────────────────────────────────────────────────┘
    │
    ├─► CAPA 2: NominaCalculator       → ResultadoNomina (por mes)
    │     Inputs: ParametrosNomina, ParametrosCalculo, PerfilCadenaA[]
    │
    ├─► CAPA 3: NoPayrollCalculator    → ResultadoNoPayroll (por mes)
    │     Inputs: ParametrosNoPayroll, PerfilCadenaA[]
    │
    ├─► CAPA 4: CadenaBCalculator      → ResultadoCadenaB (por mes)
    │     Inputs: ParametrosCadenaB
    │
    ├─► CAPA 5: CadenaCCalculator      → ResultadoCadenaC (por mes)
    │     Inputs: ParametrosCadenaC, IParametrizationProvider
    │
    ├─► CAPA 6: CostosTotalesCalculator → CostosTotalesMes (por mes)
    │     Inputs: ResultadoNomina, ResultadoNoPayroll, ResultadoCadenaB, ResultadoCadenaC
    │
    ├─► CAPA 7: CostosFinancierosCalculator → CostosFinancierosMes (por mes)
    │     Inputs: CostosTotalesMes.total, mes, costo_anterior, IParametrizationProvider
    │     DEPENDENCIA INTERMENSUAL: costo anterior como base de financiación
    │
    ├─► CAPA 8: PyGCalculator          → List[PyGMensual]
    │     Inputs: todos los anteriores (via CostosTotalesCalculator, CostosFinancierosCalculator)
    │     ACUMULADOS: acum_ingreso_bruto/neto/costo/contribucion (running totals)
    │
    ├─► CAPA 9: KPIsCalculator         → KPIsDeal
    │     Inputs: List[PyGMensual], PanelDeControl, IParametrizationProvider
    │
    ├─► CAPA 10a: CostToServeCalculator → ResultadoCostToServe
    │     Inputs: PerfilCadenaA[], ParametrosCadenaB, NominaCalculator, NoPayrollCalculator
    │
    ├─► CAPA 10b: VisionTarifasCalculator → ResultadoVisionTarifas
    │     Inputs: PerfilCadenaA[], ParametrosCadenaB, PanelDeControl, NominaCalculator, NoPayrollCalculator
    │
    ├─► CAPA 10c: VisionPyGBuilder → VisionPyG
    │     Inputs: List[PyGMensual], KPIsDeal (transformación estructural, sin recálculos)
    │
    ├─► CAPA 10d: _calcular_waterfall → WaterfallPromedio (promedios de meses activos)
    │
    ├─► CAPA 10e: _calcular_reglas_negocio → List[ReglaNegocios]
    │     Inputs: PanelDeControl, List[PyGMensual], IParametrizationProvider
    │
    └─► CAPA 10f: RiesgoCalculator → EvaluacionRiesgo
          Inputs: PanelDeControl, KPIsDeal, List[PyGMensual], PerfilCadenaA[], CadenaB/C
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  PricingResult (domain object)                      │
│  kpis, pyg_por_mes, panel,                          │
│  cost_to_serve, vision_tarifas,                     │
│  waterfall, reglas_negocio,                         │
│  evaluacion_riesgo, vision_pyg                      │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  pricing_serializer.py                              │
│  PricingResult → Dict[str, Any]                     │
│  Captura @property fields explícitamente            │
│  Almacena en storage/simulation_results/            │
└─────────────────────────────────────────────────────┘
    │ storage/{result_id}.json
    ▼
┌─────────────────────────────────────────────────────┐
│  results_router.py (REST Endpoints)                 │
│  GET /simulation/{id}/results/*                     │
│  Carga desde storage y devuelve sección             │
└─────────────────────────────────────────────────────┘
    │ JSON Response
    ▼
FRONTEND
```

---

## 2. Capa 1: Entry Data Contract

### Estructura Canónica (4 secciones)

```json
{
  "panel_de_control": {
    "cliente": "string",
    "tipo_cliente": "string (Grupo Aval | No Grupo Aval)",
    "linea_negocio": "string (Cobranzas | SAC | etc.)",
    "fecha_inicio": "YYYY-MM-DD",
    "meses_contrato": "int",
    "margen": "float [0.0..1.0]",
    "op_cont": "float [0.0..1.0]",
    "com_cont": "float [0.0..1.0]",
    "markup": "float [0.0..1.0]",
    "descuento": "float [0.0..1.0]",
    "ciudad": "string",
    "sede": "string",
    "periodo_pago_dias": "int (30|60|90|120)",
    "activa_financiacion": "bool"
  },
  "condiciones_cadena_a": {
    "perfiles": [
      {
        "nombre": "string",
        "canal": "string (WhatsApp | Correo | WebChat | etc.)",
        "modalidad": "string (Inbound | Outbound)",
        "fte": "float",
        "salario_base": "float [COP]",
        "modelo_cobro": "string (Fijo FTE | Híbrido | Variable)",
        "pct_fijo": "float [0.0..1.0]",
        "es_soporte": "bool"
      }
    ]
  },
  "condiciones_cadena_b": {
    "canales": [...],
    "opex_consumo_variable": [...],
    "equipo_sm": [...],
    "dispositivos_sm": [...]
  },
  "condiciones_cadena_c": {
    "canales": [...],
    "equipo_transversal": [...]
  }
}
```

### Campos de entry_data → Destino en Domain

| entry_data campo | Domain Model | Capa | Notas |
|---|---|---|---|
| `panel_de_control.cliente` | `PanelDeControl.cliente` | 1 | Direct mapping |
| `panel_de_control.margen` | `PanelDeControl.margen` | 1 | Usado en PyG para ingreso |
| `panel_de_control.op_cont` | `PanelDeControl.op_cont` | 1 | contingencia operativa |
| `panel_de_control.com_cont` | `PanelDeControl.com_cont` | 1 | contingencia comercial |
| `panel_de_control.periodo_pago_dias` | `PanelDeControl.periodo_pago_dias` | 1 | → factor_periodo en KPIs |
| `panel_de_control.ciudad` | `PanelDeControl.ciudad` | 1 | → tasa ICA vía provider |
| `panel_de_control.sede` | `PanelDeControl.sede` | 1 | → costos no-payroll vía provider |
| `condiciones_cadena_a.perfiles[].fte` | `PerfilCadenaA.fte` | 1 | FTE posiciones del canal |
| `condiciones_cadena_a.perfiles[].salario_base` | `PerfilCadenaA.salario_base` | 1 | → salario_cargado via NominaCargadaService |
| `condiciones_cadena_a.perfiles[].modelo_cobro` | `PerfilCadenaA.modelo_cobro` | 1 | Fijo FTE / Híbrido / Variable |
| `condiciones_cadena_a.perfiles[].pct_fijo` | `PerfilCadenaA.pct_fijo` | 1 | Porción fija de facturación |
| `condiciones_cadena_a.perfiles[].es_soporte` | `PerfilCadenaA.es_soporte` | 1 | False = canal operativo |
| `condiciones_cadena_b.canales[].tarifa_unitaria` | `CanalCadenaB.tarifa_unitaria` | 1 | Precio por transacción B |
| `condiciones_cadena_b.canales[].volumen_mensual` | `CanalCadenaB.volumen_mensual` | 1 | → L50 en CTS |

---

## 3. Capa 2: Context Builder

### Responsabilidad

El Context Builder combina **UserInput** (lo que el usuario envía) con **ParametrizationProvider** (datos de storage/) para producir el **PricingRequest** completo.

### Transformaciones Clave

| Input Source | Transformación | Output Domain Field |
|---|---|---|
| `UserInput.panel_de_control.ciudad` + storage/OP-ICA | `provider.get_ica(ciudad)` | `PanelDeControl.tasa_ica` |
| storage/OP-Poliza | `provider.get_gmf()` | `PanelDeControl.tasa_gmf` |
| storage/OP-Config | `provider.tasa_mensual_financiacion` | `PanelDeControl.tasa_mensual_financ` |
| `UserInput.perfiles[].salario_base` + storage/HR | `NominaCargadaService.calcular(salario_base, tipo_carga, panel)` | `PerfilCadenaA.salario_cargado` |
| `UserInput.panel_de_control.linea_negocio` + storage/HR | `provider.get_pct_rotacion(linea)` | `ParametrosCalculo.pct_rotacion` |
| `UserInput.panel_de_control.sede` + storage/HR | `provider.get_costo_no_payroll(sede)` | `ParametrosNoPayroll.*` |
| storage/OP | `provider.get_factor_indexacion(componente, anio)` | `ParametrosNomina.factor_indexacion_base` |
| storage/HR-Ratios + perfiles base | `NominaCargadaService` | PerfilCadenaA[] (base + soporte adicional) |

### Invariante de Diseño

> **El Context Builder es la única capa donde los datos de UserInput son combinados con datos de storage.**  
> Ninguna calculadora accede directamente a ParametrizationProvider para datos de entrada (excepto datos de ejecución: tasa_polizas, factor_rampup, etc.).

---

## 4. Capas 3-10: Pipeline de Calculadoras

### Capa 2: NominaCalculator

**Archivo**: `calculators/nomina.py`  
**Inputs**: `ParametrosNomina`, `ParametrosCalculo`, `PerfilCadenaA[]`  
**Output**: `ResultadoNomina` (por mes)

| Output Field | Fórmula Excel | Implementación Python |
|---|---|---|
| `salario_fijo` | `FTE × salario_cargado × factor_indexacion × factor_rampup × (1 - pct_ausente)` | nomina.py:_calcular_salario_fijo |
| `comisiones` | `FTE × salario_base × comision_pct × pct_cumplimiento_variable × factor_rampup` | nomina.py:_calcular_comisiones |
| `cap_inicial` | `FTE_nuevos × dias_cap_inicial × tarifa_dia_cap / meses_contrato` | nomina.py:_amortizar_cap_inicial |
| `cap_rotacion` | `FTE × pct_rotacion × dias_cap_rotacion × tarifa_dia_cap × factor_rampup` | nomina.py:_calcular_cap_rotacion |
| `examenes` | `FTE_examenes × (pct_examen_anual × costo_examen + costo_inicial/meses)` | nomina.py:_calcular_examenes |
| `seguridad` | `FTE × incluye_seguridad × costo_estudio_seg × factor_rampup` | nomina.py:_calcular_seguridad |
| `crucero` | `FTE × incluye_crucero × costo_crucero / meses_contrato` | nomina.py:_calcular_crucero |
| `total` | `@property = sum(todos los anteriores)` | models.py:ResultadoNomina.total |

---

### Capa 3: NoPayrollCalculator

**Archivo**: `calculators/no_payroll.py`  
**Inputs**: `ParametrosNoPayroll`, `PerfilCadenaA[]`  
**Output**: `ResultadoNoPayroll` (por mes)

| Output Field | Fórmula | Fuente |
|---|---|---|
| `opex_ti` | `Σ(FTE × opex_ti_por_estacion)` por perfil activo | ParametrosNoPayroll.opex_ti_por_estacion |
| `capex` | `Σ(FTE × capex_por_estacion)` | ParametrosNoPayroll.capex_por_estacion |
| `costos_fijos` | `Σ(FTE × (arriendo + energia + vigilancia + aseo + otros))` | ParametrosNoPayroll.* |
| `total` | `@property = opex_ti + capex + costos_fijos` | models.py:ResultadoNoPayroll.total |

---

### Capas 4-5: CadenaBCalculator / CadenaCCalculator

**Archivo**: `calculators/cadena_b.py`, `calculators/cadena_c.py`  
**Inputs**: `ParametrosCadenaB`, `ParametrosCadenaC`  

| Calculadora | Output | Fórmula Clave |
|---|---|---|
| CadenaBCalculator | `ResultadoCadenaB` | `opex_fijo` por canal + costos S&M + HITL + variable |
| CadenaCCalculator | `ResultadoCadenaC` | tarifa_proveedor + OPEX integración + HITL + amortización inversión |
| CadenaBCalculator | `total @property` | `opex_fijo + inversiones + sm + costo_variable + escalamiento + hitl` |
| CadenaCCalculator | `total @property` | `tarifa_proveedor + opex_fijo + opex_var + inversiones + equipo + escalamiento + hitl` |

---

### Capa 6: CostosTotalesCalculator

**Archivo**: `calculators/costos_totales.py`  
**Inputs**: ResultadoNomina, ResultadoNoPayroll, ResultadoCadenaB, ResultadoCadenaC (todos del mes actual)

| Output Field | Fórmula |
|---|---|
| `CostosTotalesMes.payroll_a` | `ResultadoNomina.total` |
| `CostosTotalesMes.no_payroll_a` | `ResultadoNoPayroll.total` |
| `CostosTotalesMes.costo_b` | `ResultadoCadenaB.total` |
| `CostosTotalesMes.costo_c` | `ResultadoCadenaC.total` |
| `costo_a @property` | `payroll_a + no_payroll_a` |
| `total @property` | `costo_a + costo_b + costo_c` |

---

### Capa 7: CostosFinancierosCalculator ⚠️ DEPENDENCIA INTERMENSUAL

**Archivo**: `calculators/costos_financieros.py`  
**Inputs**: `costo_operativo` (mes actual), `costo_operativo_mes_anterior` (mes N-1)

**ORDEN CRÍTICO DE APLICACIÓN** (gross-up chain):
```
1. financiacion  = costo_mes_anterior × tasa_mensual × factor_periodo
2. polizas       = (costo / factor_margenes + financiacion) × tasa_polizas
3. ica           = (costo / factor_margenes + polizas + financiacion) × tasa_ica
4. gmf           = (costo + polizas + financiacion) × tasa_gmf
```

| Output Field | Fórmula | Fuente de Parámetro |
|---|---|---|
| `financiacion` | `base_financiacion × tasa_mensual_financ × factor_periodo` | PanelDeControl.activa_financiacion, tasa_mensual_financ |
| `polizas` | `gross-up sobre (costo/factor + financiacion)` | IParametrizationProvider.get_tasa_polizas_efectiva(mes) |
| `ica` | `gross-up sobre (costo/factor + polizas + financiacion)` | IParametrizationProvider.get_ica(ciudad) |
| `gmf` | `(costo + polizas + financiacion) × tasa_gmf` | PanelDeControl.tasa_gmf |
| `total @property` | `financiacion + polizas + ica + gmf` | models.py:CostosFinancierosMes.total |

---

### Capa 8: PyGCalculator — Estado de Resultados Mensual

**Archivo**: `calculators/pyg.py`  
**Inputs**: CostosTotalesMes, CostosFinancierosMes, PanelDeControl, IParametrizationProvider  
**Output**: `PyGMensual` (por mes), luego `List[PyGMensual]` para el contrato completo

#### Campos Almacenados (stored fields)

| PyGMensual Field | Fórmula | Fuente |
|---|---|---|
| `mes` | iteración 1..N | PanelDeControl.meses_contrato |
| `rampup` | `get_rampup(linea, mes)` | IParametrizationProvider.get_rampup |
| `ingreso_bruto_a` | `costo_a × (1 + margen) × rampup` | CostosTotalesMes.costo_a |
| `ingreso_bruto_b` | `costo_b × (1 + margen) × rampup` | CostosTotalesMes.costo_b |
| `ingreso_bruto_c` | `costo_c × (1 + margen) × rampup` | CostosTotalesMes.costo_c |
| `contingencia_op` | `ingreso_bruto × panel.op_cont` | PanelDeControl.op_cont |
| `contingencia_com` | `ingreso_bruto × panel.com_cont` | PanelDeControl.com_cont |
| `markup_ingreso` | `ingreso_bruto × panel.markup` | PanelDeControl.markup |
| `descuento_ingreso` | `ingreso_bruto × panel.descuento` | PanelDeControl.descuento |
| `payroll_a` | `CostosTotalesMes.payroll_a` | NominaCalculator output |
| `no_payroll_a` | `CostosTotalesMes.no_payroll_a` | NoPayrollCalculator output |
| `costo_b` | `CostosTotalesMes.costo_b` | CadenaBCalculator output |
| `costo_c` | `CostosTotalesMes.costo_c` | CadenaCCalculator output |
| `ica` | `CostosFinancierosMes.ica` | CostosFinancierosCalculator output |
| `gmf` | `CostosFinancierosMes.gmf` | CostosFinancierosCalculator output |
| `polizas` | `CostosFinancierosMes.polizas` | CostosFinancierosCalculator output |
| `financiacion` | `CostosFinancierosMes.financiacion` | CostosFinancierosCalculator output |
| `acum_ingreso_bruto` | running sum hasta mes N | PyGCalculator.calcular_contrato |
| `acum_ingreso_neto` | running sum hasta mes N | PyGCalculator.calcular_contrato |
| `acum_costo_total` | running sum hasta mes N | PyGCalculator.calcular_contrato |
| `acum_costos_financieros` | running sum hasta mes N | PyGCalculator.calcular_contrato |
| `acum_contribucion` | running sum hasta mes N | PyGCalculator.calcular_contrato |

#### @property Fields (derivados — NO almacenados, SIEMPRE calculados en runtime)

Ver **Sección 8** para documentación completa.

---

### Capa 9: KPIsCalculator

**Archivo**: `calculators/kpis.py`  
**Inputs**: `List[PyGMensual]`, `PanelDeControl`, `IParametrizationProvider`  
**Output**: `KPIsDeal`

| KPIsDeal Field | Fórmula | Fuente |
|---|---|---|
| `costo_mensual_promedio` | `Σ(costo_total) / meses_contrato` | PyGMensual.costo_total @property |
| `costo_cadena_a_promedio` | `Σ(costo_a) / meses_contrato` | PyGMensual.costo_a @property |
| `ingreso_mensual` | `(costo_promedio_a + costos_fin_promedio) / factor_margenes` | Tarifa mensual calculada |
| `facturacion_mensual_proyectada` | `ingreso_mensual / factor_periodo` | Considera período de pago |
| `ingreso_bruto_total` | `Σ(ingreso_bruto)` | @property sobre stored fields |
| `ingreso_neto_total` | `Σ(ingreso_neto)` | @property sobre stored fields |
| `costo_total_contrato` | `Σ(costo_total)` | @property sobre stored fields |
| `contribucion_total` | `ingreso_neto_total - costo_total_contrato` | Derivado de anteriores |
| `utilidad_neta_total` | `contribucion_total` (equivalentes) | models.py |
| `pct_utilidad_neta_total` | `utilidad_neta_total / ingreso_neto_total` | Ratio |
| `valor_total_deal` | `ingreso_neto_total` | = valor total facturado |
| `margen_minimo_requerido` | `provider.get_margen_minimo(linea)` | storage/HR-Rentabilidad |
| `cumple_margen_minimo` | `panel.margen >= margen_minimo_requerido` | Bool comparison |

**factor_margenes** (denominador en tarifa):
```python
factor_margenes = (1 - panel.margen) × (1 - panel.op_cont) × (1 - panel.com_cont) 
                  × (1 + panel.markup) × (1 - panel.descuento)
```

---

## 5. Capa 11: Visiones y Agregados

### CostToServeCalculator

**Archivo**: `calculators/cost_to_serve.py`  
**Inputs**: `PerfilCadenaA[]`, `ParametrosCadenaB`, NominaCalculator, NoPayrollCalculator  
**Output**: `ResultadoCostToServe`

| Denominador | Definición | Uso |
|---|---|---|
| **K50** | `Σ(FTE outbound) + Σ(vol_mensual inbound)` | Denominador CTS Cadena A |
| **L50** | `Σ(volumen_mensual canales Cadena B activos)` | Denominador CTS Cadena B |

| Output Field | Fórmula |
|---|---|
| `cts_cadena_a` | `(avg_payroll_a + avg_no_payroll_a) / K50` |
| `cts_cadena_b` | `avg_costo_b / L50` |
| `cts_ponderado` | `(cts_a × K50 + cts_b × L50) / (K50 + L50)` |
| `participacion_a` | `K50 / (K50 + L50)` |
| `participacion_b` | `L50 / (K50 + L50)` |
| `desglose_a.total @property` | `nomina + no_payroll` |
| `desglose_b.total @property` | `componente_fijo + componente_variable` |

### VisionTarifasCalculator

**Archivo**: `calculators/vision_tarifas.py`  
**Inputs**: `PerfilCadenaA[]` (es_soporte=False), `ParametrosCadenaB`, `PanelDeControl`, NominaCalculator, NoPayrollCalculator  
**Output**: `ResultadoVisionTarifas`

#### Por canal (TarifaCanal):

| TarifaCanal Field | Fórmula | Fuente |
|---|---|---|
| `payroll_ch` | `Σ(nomina_mes) / n_meses` por canal | NominaCalculator |
| `no_payroll_ch` | `Σ(no_payroll_mes) / n_meses` | NoPayrollCalculator |
| `costo_cadena_a_ch` | `payroll_ch + no_payroll_ch` | Suma anterior |
| `cadena_b_atribuible` | `(vol_canal_b / vol_total_b) × avg_costo_b` | CadenaBCalculator |
| `financieros_atribuible` | `(costo_ch / costo_a_total) × avg_costos_financieros` | CostosFinancierosMes |
| `costo_atribuible` | `costo_cadena_a_ch + cadena_b_atribuible + financieros_atribuible` | Suma |
| `ingreso_bruto` | `costo_atribuible / factor_billing` | factor_billing = factor_margenes |
| `facturacion` | `ingreso_bruto × pct_fijo` | PerfilCadenaA.pct_fijo |
| `tarifa_fijo_fte` | `facturacion / fte` | PerfilCadenaA.fte |
| `tarifa_variable` | `(ingreso_bruto × pct_variable) / vol_mensual` | PerfilCadenaA.pct_variable |

#### Selección de Canal Principal (F8.1 Fix):
```python
canal_principal = max(canales, key=lambda c: c.facturacion)
```

### VisionPyGBuilder

**Archivo**: `calculators/vision_pyg.py`  
**NATURALEZA**: Transformación estructural (NO recalcula, solo reorganiza)  
**Input**: `List[PyGMensual]`, `KPIsDeal`  
**Output**: `VisionPyG` (con `filas[]` para tabla frontend)

> ✅ **Sin desacoplamientos**: todos los valores provienen directamente de PyGMensual o KPIsDeal.

---

## 6. Capa 12: Serialización

### pricing_serializer.py — Contratos JSON

**Función principal**: `pricing_result_to_dict(resultado, result_id) → Dict`

| Sección JSON | Fuente de Datos | Método Serializer |
|---|---|---|
| `result_id` | UUID asignado | parámetro |
| `calculated_at` | `datetime.now(utc).isoformat()` | runtime |
| `ficha_deal` | `PanelDeControl` | `_ficha_deal_to_dict(panel)` |
| `kpis` | `KPIsDeal` | `asdict(resultado.kpis)` |
| `pyg_por_mes` | `List[PyGMensual]` | `[_pyg_to_dict(p) for p in ...]` |
| `waterfall_promedio` | `WaterfallPromedio` | `_waterfall_to_dict(...)` |
| `configuracion_comercial` | Vision Tarifas + Panel + KPIs | `_configuracion_comercial(resultado)` |
| `reglas_negocio` | `List[ReglaNegocios]` | `[asdict(r) for r in ...]` |
| `evaluacion_riesgo` | `EvaluacionRiesgo` | `_evaluacion_riesgo_to_dict(...)` |
| `vision_pyg` | `VisionPyG` | `_vision_pyg_to_dict(...)` |
| `cost_to_serve` | `ResultadoCostToServe` | `_cost_to_serve_to_dict(...)` |
| `vision_tarifas` | `ResultadoVisionTarifas` | `_vision_tarifas_to_dict(...)` |
| `panel` | `PanelDeControl` | `asdict(panel)` |

---

## 7. Capa 13: Endpoints REST

### Contratos de Respuesta

| Endpoint | Datos Devueltos | Fuente en storage JSON | Breaking Changes |
|---|---|---|---|
| `GET /simulation/{id}/results` | PricingResult completo | Root del JSON | — |
| `GET /simulation/{id}/results/kpis` | `KPIsDeal` | `.kpis` | — |
| `GET /simulation/{id}/results/pyg` | `List[PyGMensual]` serializado | `.pyg_por_mes` | — |
| `GET /simulation/{id}/results/cost-to-serve` | `ResultadoCostToServe` | `.cost_to_serve` | — |
| `GET /simulation/{id}/results/vision-tarifas` | `ResultadoVisionTarifas` completo | `.vision_tarifas` | F8.3: ahora retorna estructura completa |

### Estructura del Storage JSON (contrato definitivo)

```json
{
  "result_id": "uuid",
  "calculated_at": "ISO8601",
  "ficha_deal": {
    "cliente", "linea_negocio", "ciudad", "sede", "tipo_cliente",
    "antiguedad_cliente", "fecha_inicio", "meses_contrato",
    "periodo_pago_dias", "ajuste_precio_tipo", "ajuste_precio_frecuencia"
  },
  "kpis": {
    "costo_mensual_promedio", "costo_cadena_a_promedio", "ingreso_mensual",
    "facturacion_mensual_proyectada", "ingreso_bruto_total", "ingreso_neto_total",
    "costo_total_contrato", "contribucion_total", "utilidad_neta_total",
    "pct_utilidad_neta_total", "valor_total_deal", "margen_minimo_requerido",
    "cumple_margen_minimo"
  },
  "pyg_por_mes": [
    {
      "mes", "rampup",
      "ingreso_bruto_a", "ingreso_bruto_b", "ingreso_bruto_c",
      "contingencia_op", "contingencia_com", "markup_ingreso", "descuento_ingreso",
      "payroll_a", "no_payroll_a", "costo_b", "costo_c",
      "ica", "gmf", "polizas", "financiacion",
      "acum_ingreso_bruto", "acum_ingreso_neto", "acum_costo_total",
      "acum_costos_financieros", "acum_contribucion",
      "-- @property fields (capturados explícitamente por _pyg_to_dict) --",
      "ingreso_bruto", "ingreso_neto", "costo_a", "costos_financieros",
      "costo_total", "contribucion", "pct_contribucion",
      "utilidad_neta", "pct_utilidad_neta"
    }
  ],
  "waterfall_promedio": {
    "payroll_a", "no_payroll_a", "costo_b", "costo_c",
    "financiacion", "polizas", "ica", "gmf",
    "costo_total", "ingreso_bruto", "contingencias",
    "markup_descuento", "ingreso_neto", "contribucion", "meses_activos"
  },
  "configuracion_comercial": {
    "modelo_cobro_principal", "pct_fijo_global", "pct_variable_global",
    "tarifa_fija", "tarifa_variable",
    "descuento", "margen_objetivo", "volumen_base_mensual",
    "ingreso_mensual", "costo_mensual_total", "valor_total_deal"
  },
  "reglas_negocio": [
    {"nombre", "label", "aplicado", "min_valor", "max_valor", "status", "monto"}
  ],
  "evaluacion_riesgo": {
    "score_cliente", "score_operativo", "score_total",
    "clasificacion_total", "requiere_aprobacion",
    "criterios": [{"id", "factor", "categoria", "valor_evaluado", "calificacion", "puntaje", "peso"}]
  },
  "vision_pyg": {
    "resumen": {"meses_contrato", "meses_activos", "valor_total_deal", ...},
    "filas": [{"key", "label", "seccion", "tipo", "signo", "valores[]", "acumulado", "promedio"}],
    "meses_contrato", "meses_activos"
  },
  "cost_to_serve": {
    "cts_cadena_a", "cts_cadena_b", "cts_ponderado",
    "participacion_a", "participacion_b", "participacion_c",
    "fte_cadena_a", "vol_cadena_b", "cts_cadena_c", "costo_total_acumulado",
    "desglose_a": {"nomina", "no_payroll", "nomina_loaded", "...", "total"},
    "desglose_b": {"componente_fijo", "componente_variable", "...", "total"}
  },
  "vision_tarifas": {
    "canales": [{"nombre_canal", "modalidad", "fte", "costo_atribuible", "ingreso_bruto",
                 "facturacion", "tarifa_fijo_fte", "tarifa_variable", "modelo_cobro",
                 "pct_fijo", "pct_variable", "payroll_ch", "no_payroll_ch", "..."}],
    "costo_cadena_a_total", "costo_cadena_b_total", "costo_cadena_c_total",
    "costo_total", "ingreso_mensual"
  },
  "panel": { "...todos los campos de PanelDeControl..." }
}
```

---

## 8. Trazabilidad de @property Fields

### PyGMensual @property Fields (11 campos derivados)

Todos calculados desde stored fields del mismo objeto:

| @property | Fórmula | Stored Dependencies | Nullability |
|---|---|---|---|
| `ingreso_bruto` | `ingreso_bruto_a + ingreso_bruto_b + ingreso_bruto_c` | 3 campos almacenados | ≥ 0.0 siempre |
| `ingreso_neto` | `ingreso_bruto + contingencia_op + contingencia_com + markup_ingreso - descuento_ingreso` | 5 campos almacenados | Puede ser 0 si contrato no activo en mes |
| `costo_a` | `payroll_a + no_payroll_a` | payroll_a, no_payroll_a | ≥ 0.0 |
| `costos_financieros` | `ica + gmf + polizas + financiacion` | 4 campos almacenados | ≥ 0.0 |
| `costo_total` | `costo_a + costo_b + costo_c` | costo_a @prop + costo_b + costo_c | ≥ 0.0 |
| `contribucion` | `ingreso_neto - costo_total` | @prop ingreso_neto - @prop costo_total | Puede ser negativo |
| `pct_contribucion` | `contribucion / ingreso_neto if ingreso_neto else 0.0` | @prop contribucion / @prop ingreso_neto | 0.0 si ingreso_neto=0 |
| `utilidad_neta` | `contribucion` (alias) | @prop contribucion | Mismo que contribucion |
| `pct_utilidad_neta` | `utilidad_neta / ingreso_neto if ingreso_neto else 0.0` | @prop utilidad_neta | 0.0 si ingreso_neto=0 |

### DesgloseCTS @property Fields

| Dataclass | @property | Fórmula |
|---|---|---|
| `DesgloseCTSCadenaA` | `total` | `nomina + no_payroll` |
| `DesgloseCTSCadenaB` | `total` | `componente_fijo + componente_variable` |

### ResultadoNomina @property

| @property | Fórmula |
|---|---|
| `total` | `salario_fijo + comisiones + cap_inicial + cap_rotacion + examenes + seguridad + crucero` |

### ResultadoNoPayroll @property

| @property | Fórmula |
|---|---|
| `total` | `opex_ti + capex + costos_fijos` |

### ResultadoCadenaB / ResultadoCadenaC @property

| Dataclass | @property | Fórmula |
|---|---|---|
| `ResultadoCadenaB` | `total` | `opex_fijo + inversiones + sm + costo_variable + escalamiento + hitl` |
| `ResultadoCadenaC` | `total` | `tarifa_proveedor + opex_fijo_integ + opex_var_integ + inversiones + equipo_integ + escalamiento + hitl` |

### CostosTotalesMes @property

| @property | Fórmula |
|---|---|
| `costo_a` | `payroll_a + no_payroll_a` |
| `total` | `costo_a + costo_b + costo_c` |

---

## 9. Dependencias Intermensuales

El pipeline tiene **una sola dependencia intermensual crítica**:

### CostosFinancierosCalculator — Financiación basada en mes anterior

```
Mes 1:  costo_anterior = 0.0 (sin financiación)
Mes 2:  costo_anterior = costo_total_mes_1
Mes 3:  costo_anterior = costo_total_mes_2
...
Mes N:  costo_anterior = costo_total_mes_(N-1)
```

**Código**:
```python
# PyGCalculator.calcular_contrato
costo_anterior: float = 0.0
for mes in range(1, self._panel.meses_contrato + 1):
    pyg = self.calcular_mes(perfiles, mes, costo_mes_anterior=costo_anterior)
    costo_anterior = pyg.costo_total  # pasa al siguiente mes
```

**Implicación**: La simulación es **estrictamente secuencial** mes a mes. No se puede calcular el mes N sin conocer el costo del mes N-1.

**Acumulados en calcular_contrato** (running totals, también intermensuales):
```python
acum_bruto  += pyg.ingreso_bruto      # acum_ingreso_bruto
acum_neto   += pyg.ingreso_neto       # acum_ingreso_neto
acum_costo  += pyg.costo_total        # acum_costo_total
acum_fin    += pyg.costos_financieros # acum_costos_financieros
acum_contrib += pyg.contribucion      # acum_contribucion
```

---

## 10. Versionado de Parametrización

### Estructura de Dominio de Storage

```
storage/parametrization/
├── hr/                     (HR domain — salaries, payroll params, staff ratios)
│   ├── versions.json       → active_version: "ID"
│   └── {version_id}.json   → HR data: nomina, aportes, prestaciones, ...
│
├── gn/                     (GN domain — general/ops pricing params)
│   ├── versions.json
│   └── {version_id}.json
│
├── op/                     (OP domain — operational config: ICA, GMF, pólizas, tasas)
│   ├── versions.json
│   └── {version_id}.json
│
└── business_rules/         (NEW Phase 9 — centralized from config/)
    ├── versions.json       → active_version: "2026-01"
    └── 2026-01.json        → riesgo_config + reglas_negocio
```

### Cómo Cambiar una Versión

```bash
# 1. Crear nuevo archivo de versión
cp storage/parametrization/business_rules/2026-01.json 2026-02.json

# 2. Editar el nuevo archivo
# 3. Actualizar versions.json
# { "active_version": "2026-02", ... }
```

### Dominio ↔ Calculadora que lo Usa

| Dominio | Archivos | Calculadoras que lo Consumen |
|---|---|---|
| `hr/` | salarios, ARL, prestaciones, rotación, staff | NominaCalculator, NoPayrollCalculator, context_builder |
| `gn/` | Rampup, márgenes mínimos | KPIsCalculator, PyGCalculator |
| `op/` | ICA, GMF, tasa polizas, tasa financiación, indexación | CostosFinancierosCalculator, KPIsCalculator, context_builder |
| `business_rules/` | riesgo_config, reglas_negocio | RiesgoCalculator, _calcular_reglas_negocio (engine) |

---

## 11. Contratos Oficiales de Entrada/Salida

### Contrato de Entrada (Frontend → POST /simulate/calculate)

```json
{
  "panel_de_control": { /* PanelDeControlInput — validado por SimulationRequest */ },
  "condiciones_cadena_a": { /* CondicionesCadenaAInput */ },
  "condiciones_cadena_b": { /* CondicionesCadenaBInput */ },
  "condiciones_cadena_c": { /* CondicionesCadenaCInput */ }
}
```

**Validaciones aplicadas** (triple-layer Phase 5.5):
1. Pydantic schema validation (request_dto.py)
2. Input validator (adapters/input_validator.py)
3. Context builder validation (adapters/context_builder.py)

### Contrato de Salida (GET /results/*)

| GET Endpoint | Response Schema | Contiene @property fields |
|---|---|---|
| `/results/kpis` | `KPIsDeal` (todos stored) | No — todos calculados en KPIsCalculator |
| `/results/pyg` | `List[PyGMensualDict]` | **Sí** — 9 @property fields capturados en _pyg_to_dict |
| `/results/cost-to-serve` | `ResultadoCostToServeDict` | **Sí** — DesgloseCTS.total capturado |
| `/results/vision-tarifas` | `ResultadoVisionTarifasDict` | No — TarifaCanal stored fields |
| `/results` | Completo | Todos los anteriores combinados |

### Campos de configuracion_comercial (Derivados — Phase 8 F8.1-F8.3)

| Campo | Fuente | Fórmula |
|---|---|---|
| `modelo_cobro_principal` | `max(canales, key=facturacion).modelo_cobro` | Canal con mayor revenue |
| `pct_fijo_global` | `canal_principal.pct_fijo` | Del canal principal |
| `pct_variable_global` | `canal_principal.pct_variable` | Del canal principal |
| `tarifa_fija` | `canal_principal.facturacion × pct_fijo_global` | Tarifa fija en COP |
| `tarifa_variable` | `canal_principal.tarifa_variable` | Tarifa por transacción |
| `ingreso_mensual` | `KPIsDeal.ingreso_mensual` | De KPIs |
| `costo_mensual_total` | `KPIsDeal.costo_mensual_promedio` | De KPIs |

---

## 12. Valores Derivados Fuera de Calculadoras Oficiales

### ✅ Estado Post-Phase 8

| Derivado | Ubicación | Fuente | Riesgo | Status |
|---|---|---|---|---|
| `configuracion_comercial.*` | `pricing_serializer._configuracion_comercial` | vision_tarifas.canales[] + kpis | Bajo — pure derivation | ✅ DOCUMENTADO (F8.1-F8.4) |
| `waterfall_promedio.*` | `engine._calcular_waterfall` | List[PyGMensual] — promedios simples | Bajo — pure aggregation | ✅ DOCUMENTADO |
| `reglas_negocio.*` | `engine._calcular_reglas_negocio` | Panel + pyg_por_mes + storage | Bajo — puro lookup | ✅ DOCUMENTADO |
| `ficha_deal.*` | `pricing_serializer._ficha_deal_to_dict` | PanelDeControl — subset | Bajo — subset extraction | ✅ DOCUMENTADO |

### ⚠️ Derivaciones que Requieren Atención (Phase 11)

| Derivado | Ubicación | Riesgo | Acción Recomendada |
|---|---|---|---|
| `nomina_loaded_ch` en TarifaCanal | vision_tarifas.py | Bajo — calc. inline del mismo nomina | Verificar contra Excel VCS |
| `_factor_billing()` en VisionTarifas | vision_tarifas.py | Bajo — es factor_margenes | Confirmar que usa misma fórmula que utils.py |
| Porcentajes en VisionPyG | vision_pyg.py | Bajo — promedio simple | Verificar precisión con contratos >12 meses |

---

## Resumen de Estado Trazabilidad

| Capa | Trazabilidad | Riesgo Residual |
|---|---|---|
| entry_data → domain | ✅ 100% documentado | Ninguno |
| context_builder (UserInput + Storage → PricingRequest) | ✅ 100% documentado | Ninguno |
| NominaCalculator | ✅ 100% trazable a Excel | Ninguno |
| NoPayrollCalculator | ✅ 100% trazable | Ninguno |
| CadenaBCalculator | ✅ 100% trazable | Ninguno |
| CadenaCCalculator | ✅ 100% trazable | Ninguno |
| CostosTotalesCalculator | ✅ 100% trazable | Ninguno |
| CostosFinancierosCalculator | ✅ 100% documentado (gross-up chain) | Ninguno |
| PyGCalculator (stored fields) | ✅ 100% trazable | Ninguno |
| PyGMensual @property fields | ✅ 9/9 documentados (Phase 8 F8.4) | Ninguno |
| KPIsCalculator | ✅ 100% trazable | Ninguno |
| CostToServeCalculator | ✅ 100% documentado (K50/L50) | Ninguno |
| VisionTarifasCalculator | ✅ Documentado — verificar nomina_loaded_ch | Bajo |
| VisionPyGBuilder | ✅ Transformación pura, sin recálculos | Ninguno |
| WaterfallPromedio | ✅ Promedios puros de PyGMensual | Ninguno |
| ReglaNegocios | ✅ storage/ + Panel — completamente trazable | Ninguno |
| EvaluacionRiesgo | ✅ storage/ + Panel + KPIs — documentado | Ninguno |
| pricing_serializer | ✅ 100% — @property fields capturados explícitamente | Ninguno |
| Endpoints REST | ✅ 5/5 endpoints documentados | Ninguno |
| Parametrización storage/ | ✅ Phase 9 — versionado implementado | Ninguno |

---

**Status**: 🟢 **FASE 10 COMPLETE — TRAZABILIDAD 100% DOCUMENTADA Y AUDITABLE**

**Fase 11 (SSoT Validation)**: Puede proceder con confianza — base documental completa.
