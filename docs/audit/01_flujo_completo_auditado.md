# Flujo Completo Auditado — NEXA Simulator

**Versión**: 2026-05-21  
**Estado**: Auditoría Fase 1  
**Responsabilidad**: Validar que no existan transformaciones ocultas, hardcodes manuales o precálculos fuera de las calculadoras oficiales.

---

## 1. Resumen Ejecutivo

El flujo de cálculo del simulador NEXA sigue una arquitectura pipeline clara de 10 capas secuenciales:

```
ENTRADA                 PROCESAMIENTO                    SALIDA
─────────────────────   ──────────────────────────────   ──────────────────
entry_data (JSON)       Capa 2-10: Calculadoras          PricingResult
  ↓                      (pipeline de precios)              ↓
UserInput               engine.py (orquestación)        Serialización
  ↓                      ├─ NominaCalculator              ↓
SimulationContext       ├─ NoPayrollCalculator           endpoints REST
Builder                 ├─ CadenaBCalculator              (GET /simulation/...)
  ↓                      ├─ CadenaCCalculator
PricingRequest          ├─ CostosTotalesCalculator
                        ├─ CostosFinancierosCalculator
                        ├─ PyGCalculator
                        ├─ KPIsCalculator
                        ├─ CostToServeCalculator
                        ├─ VisionTarifasCalculator
                        ├─ VisionPyGBuilder
                        ├─ RiesgoCalculator
                        └─ Reglas de Negocio
```

**Validación preliminar**: ✓ No se detectan precálculos manuales ni transformaciones ocultas en auditoría inicial.  
**Problemas encontrados**: Algunos campos de visiones calculan datos sin modelo base (nomina_loaded_ch).  
**Acciones recomendadas**: Ver Sección 7 (Inconsistencias Identificadas).

---

## 2. Entrada de Datos (entry_data/)

### 2.1 Estructura de Contrato Esperada

**Ubicación**: `/entry_data/`

**Archivos JSON esperados**:
- `panel_control_copy.json` — Configuración comercial del deal
- `cadena_a.json` — Perfiles de agentes y personal de soporte
- `cadena_b.json` — Plataforma digital, OPEX, canales operativos
- `cadena_c.json` — Integración IA, chatbots

### 2.2 Estructura de panel_control

```json
{
  "panel_de_control": {
    "cliente": "string",
    "linea_negocio": "Cobranzas|Telemercadeo|etc",
    "ciudad": "Bogota|Medellin|etc",
    "sede": "string",
    "meses_contrato": 24,
    "margen": 0.18,
    "op_cont": 0.025,
    "com_cont": 0.05,
    "markup": 0.02,
    "descuento": 0.01,
    "periodo_pago_dias": 30,
    "tasa_ica": 0.008,  // (opcional, se resuelve desde storage si no se proporciona)
    "tasa_gmf": 0.004,  // (opcional)
    "tasa_mensual_financ": 0.0088,  // (opcional)
    "pct_ausentismo": 0.10,  // (opcional)
    "pct_rotacion": 0.05,  // (opcional)
    "componente_indexacion_humano": "70SMMLV_30IPC",
    "componente_indexacion_tecnologico": "IPC",
    "aplica_ley_1819": true,
    "activa_financiacion": true,
    "antiguedad_cliente": "nuevo|medio|antiguo"
  },
  "condiciones_cadena_a": {
    "perfiles": [
      {
        "nombre": "Especialista Cobranza",
        "modalidad": "Fija|Variable",
        "canal": "WhatsApp|Email|Correo",
        "fte": 50.0,
        "rol": "Especialista",
        "pct_presencia": 1.0,
        "salario_base": null,  // (opcional, se resuelve desde storage)
        "comision_pct": 0.15,
        "dias_cap_inicial": 5,
        "dias_cap_rotacion": 2,
        "tmo_segundos": 300,
        "incluye_examenes": true,
        "incluye_seguridad": true,
        "incluye_crucero": false,
        "modelo_cobro": "unitario",
        "pct_fijo": 0.8,
        "no_payroll_mensual": 50000.0,  // (opcional)
        "cadena_b_mensual": 25000.0,    // (opcional)
        "costos_financieros_mensual": 0.0,  // (opcional)
        "vol_cadena_a_mensual": 1000.0
      }
    ]
  },
  "condiciones_cadena_b": {
    "canales": [
      {
        "nombre_canal": "WhatsApp Business",
        "num_agentes": 50.0,
        "vol_mensual": 5000.0
      }
    ],
    "opex": {
      "items": [
        {
          "rubro": "Plataformas y licencias",
          "producto": "Zendesk",
          "tipo_de_cobro": "Mensual",
          "tipo_de_gasto": "Fijo",
          "costo_unitario": 500.0,
          "cantidad": 1.0,
          "costo_total": 500.0
        }
      ]
    }
  },
  "condiciones_cadena_c": {
    "canales": [
      {
        "nombre_canal": "Chatbot IA",
        "tipo_dispositivo": "Whatsapp",
        "vol_mensual": 2000.0,
        "costo_unitario": 0.05
      }
    ]
  }
}
```

### 2.3 Validación de Entrada

**Archivo**: `adapters/input_validator.py` (si existe) o `adapters/user_input_loader.py`

**Responsabilidad**:
- Validar estructura JSON contra esquema esperado
- Validar rangos (ej. margen entre 0% y 100%, meses_contrato > 0)
- Rechazar campos unknown (no en contrato esperado)

**Campos ignorados (actualmente)**:
- ⚠️ `rubro` (Cadena B)
- ⚠️ `tipo_de_cobro` (Cadena B)
- ⚠️ `tipo_de_gasto` (Cadena B)
- ⚠️ `ItemOpexConsumoB.producto` (se almacena pero nunca se usa)

---

## 3. Transformación: SimulationContextBuilder

### 3.1 Responsabilidad

**Archivo**: `adapters/context_builder.py`

**Entrada**: `UserInput` (parsed JSON) + `IParametrizationProvider` (storage/)

**Salida**: `PricingRequest` completamente poblado y listo para el motor

### 3.2 Flujo de Construcción

```python
SimulationContextBuilder.construir(user_input: UserInput) → PricingRequest

Pasos internos:
  1. Resolver `PanelDeControl`:
     - Tomar valores del usuario si se proporcionaron
     - Fallback a storage/ si no están presentes:
       * tasa_ica → ParametrizationProvider.get_ica(ciudad)
       * tasa_gmf → ParametrizationProvider.get_gmf()
       * tasa_mensual_financ → ParametrizationProvider.tasa_mensual_financiacion
       * pct_ausentismo → ParametrizationProvider.get_pct_ausentismo(linea)
       * indexacion → storage/parametrization/op/

  2. Resolver `PerfilCadenaA`:
     - Para cada perfil usuario:
       * salario_base → ParametrizationProvider.get_salario_rol(rol)
       * nómina_cargada → NominaCargadaService.calcular(salario_base, comision_pct)
       * fte_examenes → calcula FTE incluyendo staff de soporte (Formadores, Monitor, Supervisor, Validador)

  3. Generar `PerfilCadenaA` de soporte automáticamente:
     - Lee ratios_staff desde storage
     - Lee reglas_staff desde storage
     - Genera perfiles de Supervisores, Formadores, Monitors, etc.
     - FTE calculado por ratio: fte_base / ratio_staff

  4. Resolver `ParametrosNomina` y `ParametrosCalculo`:
     - Todas las tablas desde storage/parametrization/hr/
     - Costos de capacitación, exámenes, seguridad
     - % rotación, % ausentismo, % examen anual
     - Costos operativos (ICA, GMF, pólizas)

  5. Resolver `CadenaBCalculator` y `CadenaCCalculator`:
     - Mapear inputs de user_input a domain models
     - Validar activación (si cadena_a_activa=false, ¿incluir datos?)

Resultado: PricingRequest con TODAS las dependencias resueltas
```

### 3.3 Fuentes de Datos por Campo

| Campo en PricingRequest | Origen | Ubicación |
|-------------------------|--------|-----------|
| `panel.tasa_ica` | Usuario o storage | `storage/parametrization/op/ICA` |
| `panel.tasa_gmf` | Usuario o storage | `storage/parametrization/op/Poliza` |
| `panel.tasa_mensual_financ` | Usuario o storage | `storage/parametrization/op/Config` |
| `panel.pct_ausentismo` | Usuario o storage | `storage/parametrization/hr/rotacion_ausentismo` |
| `perfiles_a[].salario_base` | Usuario o storage | `storage/parametrization/hr/nomina` |
| `perfiles_a[].salario_cargado` | **NominaCargadaService** | Calculado en dominio |
| `perfiles_soporte[].salario_base` | storage | `storage/parametrization/hr/nomina` |
| `parametros_nomina.ratios` | storage | `storage/parametrization/hr/ratios` |
| `parametros_nomina.rampup[mes]` | storage | `storage/parametrization/hr/campana` |
| `parametros_nomina.costo_fijo[sede]` | storage | `storage/parametrization/hr/costo_fijo` |

---

## 4. Orquestación: NexaPricingEngine

### 4.1 Entrada y Salida

**Archivo**: `engine.py`

**Entrada**: `PricingRequest` (desde context_builder)

**Salida**: `PricingResult` con:
- `kpis`: KPIsDeal
- `pyg_por_mes`: List[PyGMensual]  (1 elemento por mes del contrato)
- `panel`: PanelDeControl (entrada, para referencia)
- `cost_to_serve`: ResultadoCostToServe
- `vision_tarifas`: ResultadoVisionTarifas
- `vision_pyg`: VisionPyG (structured para frontend)
- `waterfall`: WaterfallPromedio
- `reglas_negocio`: List[ReglaNegocios]
- `evaluacion_riesgo`: EvaluacionRiesgo

### 4.2 Pipeline de 10 Capas

```
PricingRequest
    ↓
Composition Root (_construir_calculadores):
  - NominaCalculator → ResultadoNomina por mes
  - NoPayrollCalculator → ResultadoNoPayroll por mes
  - CadenaBCalculator → ResultadoCadenaB por mes
  - CadenaCCalculator → ResultadoCadenaC por mes
  - CostosTotalesCalculator → Suma A+B+C por mes
  - CostosFinancierosCalculator → ICA, GMF, pólizas, financiación
  - PyGCalculator → PyGMensual (ingreso, costo, utilidad) por mes
    ├─ KPIsCalculator → KPIsDeal (tarifa mensual, facturación, margen, etc.)
    └─ Otros:
       ├─ CostToServeCalculator → CTS por cadena
       ├─ VisionTarifasCalculator → Tarifas por canal
       ├─ VisionPyGBuilder → Modelo estructurado para frontend
       ├─ RiesgoCalculator → Evaluación de riesgo
       └─ _calcular_reglas_negocio → Validación vs políticas comerciales
```

### 4.3 Dependencias Entre Capas

```
NominaCalculator (Capa 2)
  └─ Recibe: ParametrosNomina, ParametrosCalculo
  └─ Produce: ResultadoNomina por mes
  └─ Deps: ninguna (capa base)

NoPayrollCalculator (Capa 3)
  └─ Recibe: ParametrosNoPayroll
  └─ Produce: ResultadoNoPayroll por mes
  └─ Deps: ninguna (capa base)

CadenaBCalculator (Capas 4-5)
  └─ Recibe: ParametrosCadenaB
  └─ Produce: ResultadoCadenaB por mes
  └─ Deps: ninguna (capa base)

CadenaCCalculator (Capa 6)
  └─ Recibe: ParametrosCadenaC, IParametrizationProvider
  └─ Produce: ResultadoCadenaC por mes
  └─ Deps: storage (tasa de financiación IA)

CostosTotalesCalculator (Capa 7)
  └─ Recibe: ResultadoNomina, ResultadoNoPayroll, ResultadoCadenaB, ResultadoCadenaC
  └─ Produce: CostosTotalMes por mes
  └─ Deps: Capas 2-6

CostosFinancierosCalculator (Capa 8)
  └─ Recibe: PanelDeControl, IParametrizationProvider
  └─ Produce: CostosFinancierosMes por mes
  └─ Deps: storage (ICA, GMF, pólizas, tasa financiación)

PyGCalculator (Capa 9)
  └─ Recibe: PanelDeControl, CostosTotalMes, CostosFinancierosMes, IParametrizationProvider
  └─ Produce: List[PyGMensual] (1 por mes)
  └─ Deps: Capa 7, Capa 8

KPIsCalculator (Capa 10)
  └─ Recibe: List[PyGMensual]
  └─ Produce: KPIsDeal (agregados de contrato)
  └─ Deps: Capa 9
```

### 4.4 Métodos Principales

```python
NexaPricingEngine.calcular(solicitud: PricingRequest) → PricingResult

Pasos:
  1. Instanciar todos los calculadores (Composition Root)
  2. Ejecutar PyGCalculator.calcular_contrato(perfiles_a)
     → Itera meses 1:N, acumula PyGMensual
  3. Ejecutar KPIsCalculator.calcular(pyg_contrato)
     → Calcula KPIs agregados (tarifa promedio, facturación total, etc.)
  4. Ejecutar CostToServeCalculator.calcular(pyg_contrato)
     → Desglose CTS por cadena y FTE
  5. Ejecutar VisionTarifasCalculator.calcular(pyg_contrato)
     → Tarifas por canal operativo
  6. Ejecutar VisionPyGBuilder.construir(pyg_contrato, kpis_deal)
     → Modelo estructurado para frontend
  7. Calcular Waterfall (promedio mensual de componentes)
  8. Calcular Reglas de Negocio (validación vs políticas)
  9. Ejecutar RiesgoCalculator.calcular(panel, kpis, pyg, perfiles, cadenas)
     → Evaluación de riesgo
  10. Empaquetar todo en PricingResult
```

---

## 5. Descripción de Calculadoras (Capa 2-10)

### 5.1 Capa 2: NominaCalculator

**Archivo**: `calculators/nomina.py`

**Responsabilidad**: Cálculo de nómina cargada mensual

**Entrada**:
- `ParametrosNomina` (tablas maestras: salarios, aportes, prestaciones)
- `ParametrosCalculo` (% rotación, ausentismo, examen anual)
- `PerfilCadenaA` (FTE, salario_base, comisión)

**Salida**: `ResultadoNomina`
```python
@dataclass
class ResultadoNomina:
    salario_fijo: float
    comisiones: float
    cap_inicial: float  # Capacitación inicial (si aplica)
    seguridad: float  # Exámenes médicos + seguridad
    # @property
    total: float = salario_fijo + comisiones + cap_inicial + seguridad
```

**Fuentes de datos**:
- Salarios por rol: `storage/parametrization/hr/nomina`
- Aportes (pensión, SENA, ARL, etc.): `storage/parametrization/hr/seg_social`
- Prestaciones (vacaciones, cesantías, prima): `storage/parametrization/hr/prestaciones`
- Costos exámenes: `storage/parametrization/hr/med_seg`
- FTE de exámenes: calculado en context_builder

**Fórmulas críticas**:
- Salario cargado = salario_base × (1 + aportes_patronales + prestaciones_proporcionales)
- Capacitación = (salario_base × dias_cap / 30) × FTE × % aplicable
- Exámenes = (costo_examen × FTE_examenes × 1/12)
- Seguridad = (costo_seguridad × FTE × % aplica)

### 5.2 Capa 3: NoPayrollCalculator

**Archivo**: `calculators/no_payroll.py`

**Responsabilidad**: Costos no salariales (infraestructura, TI, servicios generales)

**Entrada**:
- `ParametrosNoPayroll` (costos fijos por sede, utilidades, servicios)

**Salida**: `ResultadoNoPayroll`
```python
@dataclass
class ResultadoNoPayroll:
    costos_operativos: float  # Arriendo, servicios, etc.
    # Total mensual para Cadena A
```

**Fuentes de datos**:
- `storage/parametrization/hr/costo_fijo` (por sede)
- `storage/parametrization/hr/costos_operativos` (constantes)

### 5.3 Capas 4-5: CadenaBCalculator

**Archivo**: `calculators/cadena_b.py`

**Responsabilidad**: Cálculo de costos de plataforma digital

**Entrada**:
- `ParametrosCadenaB` (canales, OPEX items)

**Salida**: `ResultadoCadenaB`
```python
@dataclass
class ResultadoCadenaB:
    costo_opex_fijo: float  # Suma de items tipo "Fijo"
    costo_opex_consumo: float  # Suma de items tipo "Consumo"
    # Total mensual para Cadena B
```

**Fuentes de datos**:
- entrada_data/cadena_b.json (canales, OPEX)

**Campos ignorados** ⚠️:
- `ItemOpexConsumoB.producto` (se almacena en domain pero nunca se usa)
- `rubro`, `tipo_de_cobro`, `tipo_de_gasto` (no se mapean desde entry_data)

### 5.4 Capa 6: CadenaCCalculator

**Archivo**: `calculators/cadena_c.py`

**Responsabilidad**: Cálculo de costos de integración IA

**Entrada**:
- `ParametrosCadenaC` (canales IA, vol_mensual, costo_unitario)
- `IParametrizationProvider` (tasa de financiación IA desde storage)

**Salida**: `ResultadoCadenaC`
```python
@dataclass
class ResultadoCadenaC:
    costo_ia_variable: float  # Vol × costo_unitario
    costo_ia_fijo: float  # Contrato/licensing
    # Total mensual para Cadena C
```

**Fuentes de datos**:
- entry_data/cadena_c.json
- `storage/parametrization/op/` (tasas de IA, si aplican)

### 5.5 Capa 7: CostosTotalesCalculator

**Archivo**: `calculators/costos_totales.py`

**Responsabilidad**: Agregación de costos por mes

**Entrada**:
- `ResultadoNomina` (de Capa 2)
- `ResultadoNoPayroll` (de Capa 3)
- `ResultadoCadenaB` (de Capas 4-5)
- `ResultadoCadenaC` (de Capa 6)

**Salida**: `CostosTotalMes`
```python
@dataclass
class CostosTotalMes:
    costo_a: float = nomina + no_payroll
    costo_b: float = cadena_b
    costo_c: float = cadena_c
    # @property
    costo_total_operacional: float = costo_a + costo_b + costo_c
```

### 5.6 Capa 8: CostosFinancierosCalculator

**Archivo**: `calculators/costos_financieros.py`

**Responsabilidad**: Cálculo de costos financieros (ICA, GMF, pólizas, financiación)

**Entrada**:
- `PanelDeControl` (ciudad para ICA, período pago para GMF, etc.)
- `IParametrizationProvider` (tasas desde storage)

**Salida**: `CostosFinancierosMes`
```python
@dataclass
class CostosFinancierosMes:
    ica: float
    gmf: float
    polizas: float
    financiacion: float
    # @property
    total: float = ica + gmf + polizas + financiacion
```

**Fórmulas críticas**:
- ICA = (ingreso_bruto - descuentos) × tasa_ica / 100
- GMF = (flujos salida) × tasa_gmf
- Pólizas = (depende de saldo promedio y tasas)
- Financiación = Saldo Financiero × tasa_mensual (gross-up aplicado)

**Fuentes de datos**:
- `storage/parametrization/op/ICA` (por ciudad)
- `storage/parametrization/op/Poliza` (tasa, vigencia)
- `storage/parametrization/op/Config` (tasa_mensual_financiacion)

**Orden de aplicación** (crítico):
1. Calcular ingreso_bruto
2. Aplicar descuentos (markup, descuento)
3. Calcular ICA sobre base descuentada
4. Calcular GMF sobre flujos
5. Aplicar Gross-Up financiero (iterativo)

### 5.7 Capa 9: PyGCalculator

**Archivo**: `calculators/pyg.py`

**Responsabilidad**: Estado de Resultados mensual (PyG)

**Entrada**:
- `PricingRequest.perfiles_a` (para vol_cadena_a_mensual)
- `CostosTotalMes` (Capa 7)
- `CostosFinancierosMes` (Capa 8)
- `IParametrizationProvider` (para ramp-up, acumulación)

**Salida**: `List[PyGMensual]` (1 por mes)
```python
@dataclass
class PyGMensual:
    mes: int
    # Costos (almacenados)
    payroll_a: float
    no_payroll_a: float
    costo_b: float
    costo_c: float
    costo_financiero: float
    ica: float
    gmf: float
    polizas: float
    contingencia_op: float
    contingencia_com: float
    markup_ingreso: float
    descuento_ingreso: float
    
    # Acumulados (almacenados)
    costo_total_acumulado: float
    ingreso_bruto_acumulado: float
    
    # @property (derivadas)
    costo_total: float = sum(costos)
    ingreso_bruto: float = vol_base × tarifa_unitaria
    ingreso_neto: float = ingreso_bruto - descuentos
    contribucion: float = ingreso_neto - costo_total
    utilidad_neta: float = contribucion - ...
```

**Lógica por mes**:
1. Aplicar ramp-up (factor mensual de crecimiento de agentes)
2. Calcular volumen ajustado = vol_base × ramp_up[mes]
3. Calcular tarifa unitaria (KPI)
4. Calcular ingreso_bruto = volumen × tarifa_unitaria
5. Aplicar contingencias y markup/descuento
6. Calcular costos (nómina, no-payroll, cadena B/C, financiero)
7. Calcular PyG mensual
8. Acumular para KPIs

**Fuentes de datos**:
- `storage/parametrization/hr/campana` (ramp-up por mes y línea)
- entry_data (vol_cadena_a_mensual de perfiles)

### 5.8 Capa 10: KPIsCalculator

**Archivo**: `calculators/kpis.py`

**Responsabilidad**: KPIs agregados del deal (contrato completo)

**Entrada**:
- `List[PyGMensual]` (resultado de Capa 9)
- `PanelDeControl`
- `IParametrizationProvider`

**Salida**: `KPIsDeal`
```python
@dataclass
class KPIsDeal:
    tarifa_mensual_promedio: float
    tarifa_anualizada: float
    facturación_total: float
    costo_total: float
    utilidad_neta_total: float
    margen_neto_pct: float
    breakeven_mes: int  # Mes donde acumulado cruza 0
    # ... 20+ KPIs más
```

**Fórmulas críticas**:
- Tarifa promedio = ∑(PyG[i].ingreso_neto) / ∑(PyG[i].volumen) para meses activos
- Facturación = SUM(PyG[i].ingreso_neto)
- Costo = SUM(PyG[i].costo_total)
- Utilidad = Facturación - Costo
- Margen = Utilidad / Facturación

---

## 6. Visiones Complementarias

### 6.1 CostToServeCalculator

**Archivo**: `calculators/cost_to_serve.py`

**Responsabilidad**: Costo por servir desglosado por cadena

**Entrada**:
- `List[PyGMensual]` (del motor)
- Acceso a NominaCalculator, NoPayrollCalculator, CadenaBCalculator

**Salida**: `ResultadoCostToServe`
```python
@dataclass
class ResultadoCostToServe:
    desglose_a: DesgloseCTSCadenaA  # FTE, payroll, no-payroll, CTS
    desglose_b: DesgloseCTSCadenaB
    desglose_c: ...
    cts_por_fte: float  # Costo total / FTE
```

**Origen de datos**:
- Recalcula desde perfiles_a (FTE) y costos mensuales

### 6.2 VisionTarifasCalculator

**Archivo**: `calculators/vision_tarifas.py`

**Responsabilidad**: Tarifas desglosadas por canal operativo

**Entrada**:
- `List[PerfilCadenaA]` (agentes, canales)
- `List[PyGMensual]` (resultados mensales)
- Acceso a calculadores (NominaCalculator, NoPayrollCalculator)

**Salida**: `ResultadoVisionTarifas`
```python
@dataclass
class ResultadoVisionTarifas:
    canales: List[TarifaCanal]
    
@dataclass
class TarifaCanal:
    nombre_canal: str  # "WhatsApp", "Email", etc.
    fte: float
    volumen_mensual: float
    tarifa_unitaria: float
    # Desglose de costo:
    payroll_ch: float
    nomina_loaded_ch: float  # ⚠️ INCONSISTENCIA: calculado aquí sin modelo en domain
    salario_variable_ch: float  # ⚠️ Alias para "comisiones"
    estudios_seguridad_ch: float
    no_payroll_ch: float
    cadena_b_ch: float
```

**⚠️ Problemas Identificados**:
1. **nomina_loaded_ch** se calcula sin existir en `ResultadoNomina`
2. **salario_variable_ch** es alias innecesario de "comisiones"
3. **estudios_seguridad_ch** vs **seguridad** inconsistencia
4. **producto** (alias de canal) innecesario

### 6.3 VisionPyGBuilder

**Archivo**: `calculators/vision_pyg.py`

**Responsabilidad**: Construir modelo P&G estructurado para frontend

**Entrada**:
- `List[PyGMensual]`
- `KPIsDeal`

**Salida**: `VisionPyG` (modelo frontend)

**Operación**: Principalmente serialización estructurada, no cálculos adicionales

### 6.4 RiesgoCalculator

**Archivo**: `calculators/riesgo.py`

**Responsabilidad**: Evaluación de riesgo del deal

**Entrada**:
- `dict` riesgo_config (desde ParametrizationProvider.get_riesgo_config())
- `PanelDeControl`
- `KPIsDeal`
- `List[PyGMensual]`
- `List[PerfilCadenaA]`
- Cadenas B, C

**Salida**: `EvaluacionRiesgo`
```python
@dataclass
class EvaluacionRiesgo:
    criterios_evaluados: List[CriterioRiesgo]
    score_total: float
    clasificacion: str  # "Verde", "Amarillo", "Rojo"
    recomendaciones: List[str]
```

**⚠️ Problema de hardcodes**:
- `_DEFAULT_CRITERIOS_META` (hardcoded, línea 73)
- `_DEFAULT_RIESGO_CONFIG` (hardcoded, línea 86)
- Estos duplican datos en `config/business_rules/riesgo_config.json`

---

## 7. Reglas de Negocio

**Archivo**: `engine.py:_calcular_reglas_negocio()`

**Responsabilidad**: Validar parámetros del deal contra políticas comerciales

**Fuente de políticas**: `config/business_rules/reglas_negocio.json`

```json
{
  "politicas": [
    {
      "nombre": "margen_objetivo",
      "label": "Margen objetivo",
      "min": null,
      "max": null
    },
    {
      "nombre": "contingencia_operativa",
      "label": "Contingencia Operativa",
      "min": 0.05,
      "max": 0.08
    },
    {
      "nombre": "contingencia_comercial",
      "label": "Contingencia Comercial",
      "min": 0.04,
      "max": 0.07
    },
    {
      "nombre": "markup",
      "label": "Markup",
      "min": 0.02,
      "max": 0.08
    },
    {
      "nombre": "descuento",
      "label": "Descuento volumen",
      "min": 0.0,
      "max": 0.08
    }
  ]
}
```

**Salida**: `List[ReglaNegocios]`
```python
@dataclass
class ReglaNegocios:
    nombre: str
    label: str
    aplicado: float  # Valor en el deal
    min_valor: float | None
    max_valor: float | None
    status: str  # "dentro_rango", "bajo_minimo", "excede_maximo"
    monto: float | None  # COP (solo margen_objetivo)
```

---

## 8. Serialización y Salida (pricing_serializer.py)

### 8.1 Conversión a JSON

**Responsabilidad**: Convertir `PricingResult` (dataclasses) a dict JSON-serializable

**Archivo**: `adapters/pricing_serializer.py`

**Función principal**:
```python
def pricing_result_to_dict(result: PricingResult, result_id: str) -> dict
```

**Operación**:
1. Serializar cada `PyGMensual` incluyendo @property (ingreso_bruto, costo_total, etc.)
2. Serializar visiones (CostToServe, VisionTarifas, VisionPyG, etc.)
3. Serializar KPIs, ReglaNegocios, EvaluacionRiesgo
4. Generar `result_id` y timestamp
5. Almacenar en `storage/simulation_results/{result_id}.json`

### 8.2 Endpoints REST

**Archivo**: `api/v1/simulation/results_router.py`

**Rutas**:
```
GET /simulation/{result_id}/results
  → Retorna PricingResult completo

GET /simulation/{result_id}/results/kpis
  → Retorna KPIsDeal

GET /simulation/{result_id}/results/pyg
  → Retorna List[PyGMensual]

GET /simulation/{result_id}/results/cost-to-serve
  → Retorna ResultadoCostToServe

GET /simulation/{result_id}/results/vision-tarifas
  → Retorna ResultadoVisionTarifas

GET /simulation/{result_id}/results/vision-pyg
  → Retorna VisionPyG
```

**Validación**: Todos los endpoints leen desde `storage/simulation_results/` (datos recalculados).

---

## 9. Inconsistencias Identificadas

### 9.1 Campos Ignorados de entry_data

| Campo | Ubicación | Valor Típico | Impacto |
|-------|-----------|--------------|--------|
| `rubro` | `cadena_b.json` items | "Plataformas" | Se pierde capacidad de segmentar costos |
| `tipo_de_cobro` | `cadena_b.json` items | "Unitario", "Mensual" | Se pierde información de billing |
| `tipo_de_gasto` | `cadena_b.json` items | "Fijo", "Variable" | Se pierde clasificación CAPEX/OPEX |
| `ItemOpexConsumoB.producto` | domain/models | "Token IA", "Zendesk" | Se almacena pero no se usa en calculadora |

### 9.2 Nomenclatura Inconsistente

| Concepto | Excel | entry_data | Domain | Calculadora | Endpoint |
|----------|-------|-----------|--------|-------------|----------|
| Identificador Perfil | Perfil | `nombre` | `PerfilCadenaA.nombre` | — | `vision_tarifas.nombre_canal` |
| **Subcanal** | Canal | `canal` | `PerfilCadenaA.canal` | — | **`producto`** ⚠️ |
| Nómina Total | Payroll | (calc.) | `ResultadoNomina.total` | — | `payroll_ch` |
| **Nómina Cargada** | (derivado) | — | **(NO existe)** | — | `nomina_loaded_ch` ⚠️ |
| Salario Variable | Comisiones | (calc.) | `comisiones` | — | `salario_variable_ch` ⚠️ |
| **Seguridad** | Estudios Seg | (calc.) | **`seguridad`** | — | **`estudios_seguridad_ch`** ⚠️ |

### 9.3 Visiones con Lógica Desacoplada

| Visión | Problema | Ubicación |
|--------|----------|-----------|
| `vision_tarifas` | Calcula `nomina_loaded_ch` sin modelo base | `calculators/vision_tarifas.py:160` |
| `vision_tarifas` | Usa alias `producto` para canal | `calculators/vision_tarifas.py:142` |
| `vision_tarifas` | Rename `seguridad` → `estudios_seguridad_ch` ad-hoc | `calculators/vision_tarifas.py:168` |

---

## 10. Validación de Transformaciones

### 10.1 ¿Hay Precálculos Manuales?

**Búsqueda**: Verificar que ningún valor en endpoints sea precalculado (constante) en lugar de dinámico.

**Hallazgo**: ✓ NO se detectan precálculos evidentes. Todos los valores en endpoints derivan de `PricingResult`.

### 10.2 ¿Hay Hardcodes no Documentados?

**Búsqueda**: Grep por constantes en calculadoras.

**Hallazgos**:
- ⚠️ `riesgo.py:88` — SMMLV hardcodeado (1,423,500)
- ⚠️ `riesgo.py:73-105` — Criterios y umbrales de riesgo duplicados

Ver Fase 2 (Auditoría de Parametrización) para detalles.

### 10.3 ¿Se Respetan las Activaciones de Cadenas?

**Búsqueda**: Verificar `cadena_a_activa`, `cadena_b_activa`, `cadena_c_activa` en panel_de_control.

**Hallazgo**: ⚠️ No se encontró validación explícita en engine.py ni en adaptadores.

**Recomendación**: Ver Fase 4 (Validación de Activación de Cadenas).

---

## 11. Matriz de Trazabilidad: Entrada a Salida

```
entry_data/panel_de_control.json
  │
  ├─► panel.margen
  │     ├─ Almacenado en: PricingRequest.panel
  │     ├─ Usado por: KPIsCalculator, ReglaNegocios
  │     ├─ Output: KPIsDeal.margen_neto_pct
  │     └─ Endpoint: GET /results/kpis
  │
  ├─► panel.linea_negocio
  │     ├─ Almacenado en: PricingRequest.panel
  │     ├─ Usado por: context_builder (resolver defaults desde storage)
  │     ├─ Output: PanelDeControl.linea_negocio
  │     └─ Endpoint: GET /results
  │
  └─► panel.ciudad
        ├─ Almacenado en: PricingRequest.panel
        ├─ Usado por: context_builder (ICA desde storage)
        ├─ Output: PanelDeControl.ciudad
        └─ Endpoint: GET /results

entry_data/condiciones_cadena_a.json
  │
  └─► perfiles[].fte
        ├─ Almacenado en: PerfilCadenaA.fte
        ├─ Usado por: NominaCalculator, CostToServeCalculator
        ├─ Output: TarifaCanal.fte (vision_tarifas)
        ├─ Acumula a: KPIsDeal.fte_total
        └─ Endpoint: GET /results/vision-tarifas

storage/parametrization/hr/nomina
  │
  └─► salarios[rol]
        ├─ Cargado por: context_builder.get_salario_rol(rol)
        ├─ Almacenado en: PerfilCadenaA.salario_base
        ├─ Usado por: NominaCalculator
        ├─ Output: PyGMensual.payroll_a
        └─ Endpoint: GET /results/pyg
```

---

## 12. Conclusiones de Auditoría Fase 1

| Criterio | Estado | Evidencia |
|----------|--------|----------|
| ✓ Flujo documentado | OK | Pipeline de 10 capas bien definido |
| ✓ Sin precálculos manuales | OK | Todos los valores derivan de cálculos |
| ✓ Orquestación clara | OK | Composition Root en engine.py |
| ✓ Entrada/Salida trazables | OK | context_builder y pricing_serializer bien separados |
| ⚠️ Visiones con lógica desacoplada | ISSUE | nomina_loaded_ch calculada sin modelo |
| ⚠️ Nomenclatura inconsistente | ISSUE | canal/producto, seguridad/estudios_seguridad |
| ⚠️ Campos de entry_data perdidos | ISSUE | rubro, tipo_de_cobro, tipo_de_gasto ignorados |
| ⚠️ Activación de cadenas sin validar | ISSUE | No se verifican cadena_a_activa, etc. |
| ⚠️ Hardcodes en calculadoras | ISSUE | SMMLV, criterios de riesgo duplicados |

**Siguiente**: Fase 2 — Auditoría de Parametrización (config/ vs storage/)
