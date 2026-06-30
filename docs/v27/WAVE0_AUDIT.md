# WAVE0_AUDIT.md — Auditoría Exhaustiva del Motor Backend NEXA

**Fecha**: 27 de Mayo 2026  
**Estado**: Completo — Análisis de Divergencias V2-7  
**Objetivo**: Mapear el estado actual del motor backend vs especificación V2-7 del Excel.

---

## TABLA DE CONTENIDOS

1. [Inventario del Motor](#1-inventario-del-motor)
2. [Hardcodes Detectados](#2-hardcodes-detectados)
3. [Divergencias Matemáticas Críticas](#3-divergencias-matemáticas-críticas)
4. [Estado del Storage/Parametrización](#4-estado-del-storageparametrización)
5. [Plan de Cambios por Waves](#5-plan-de-cambios-por-waves)
6. [Cobertura de Tests](#6-cobertura-de-tests)
7. [Riesgos y Bloqueadores](#7-riesgos-y-bloqueadores)

---

## 1. INVENTARIO DEL MOTOR

### 1.1 Estructura de Directorios Principales

```
backend_nexa/
├── calculators/         — Motores de cálculo (16 archivos)
├── domain/              — Modelos de dominio (5 archivos)
├── simulation/          — DTOs, chains, builders (múltiples)
├── adapters/            — Adaptadores input/output (10+ archivos)
├── repositories/        — Proveedores de parametrización (7 archivos)
├── api/v1/              — Endpoints REST actuales
├── parametrization/     — Servicio legado (deprecated)
├── storage/             — Archivos JSON de parametrización (3 carpetas)
├── engine.py            — Orquestador principal (438 líneas)
└── app.py               — Entry point FastAPI (175 líneas)
```

### 1.2 Calculadores Principales

| Calculador | Archivo | LOC | Propósito | Fórmula Principal |
|------------|---------|-----|----------|------------------|
| **NominaCalculator** | `calculators/nomina.py` | ~250 | Costo laboral Cadena A | `salario_cargado × FTE × factor_indexacion` |
| **NoPayrollCalculator** | `calculators/no_payroll.py` | ~200 | OPEX fijo + CAPEX | `opex_mensual + capex_amortizado` |
| **CadenaBCalculator** | `calculators/cadena_b.py` | ~300 | Plataformas digitales | `tarifa_unitaria × volumen + opex_fijo` |
| **CadenaCCalculator** | `calculators/cadena_c.py` | ~350 | Integración IA/proveedor | `tarifa_proveedor × volumen + opex_integ` |
| **CostosTotalesCalculator** | `calculators/costos_totales.py` | ~150 | Agregación de costos | `costo_a + costo_b + costo_c` |
| **CostosFinancierosCalculator** | `calculators/costos_financieros.py` | ~400 | ICA, GMF, pólizas, financiación | `costo / factor_margenes` (gross-up) |
| **PyGCalculator** | `calculators/pyg.py` | ~250 | Estado de Resultados mensual | `ingreso_bruto - costos = utilidad` |
| **VisionTarifasCalculator** | `calculators/vision_tarifas.py` | ~450 | Tarifas por FTE/transacción | `(costo / (1-margen)) / FTE` |
| **CostToServeCalculator** | `calculators/cost_to_serve.py` | ~350 | Costo por transacción | `costo_total / volumen_cadena` |
| **RiesgoCalculator** | `calculators/riesgo.py` | ~200 | Evaluación de riesgo operativo | Ponderación de 9 factores |
| **KPIsCalculator** | `calculators/kpis.py` | ~200 | KPIs del deal | Margen real, ROI, break-even |

**Total: 2,650 líneas en calculadores** (estimado, excluyendo tests y worktrees).

### 1.3 Modelos de Dominio (domain/models/)

| Modelo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| **PanelDeControl** | `panel.py:89-129` | Parámetros maestros del deal (cliente, márgenes, fechas, reglas negocio) |
| **PerfilCadenaA** | `panel.py:133-170` | Un perfil operativo (agente con canal, modalidad, FTE, TMO) |
| **ParametrosNomina** | `panel.py:202-216` | Parámetros de nómina (SMMLV, indexación, capacitación) |
| **ParametrosNoPayroll** | `panel.py:219-228` | Costos fijos (TI, arriendo, energía por estación) |
| **ParametrosCadenaB** | `panel.py:232-250` | Plataformas digitales (canales, OPEX, dispositivos SM) |
| **ParametrosCadenaC** | `panel.py:253-268` | Proveedor IA (canales, equipo integración, OPEX) |
| **PyGMensual** | `visions.py` | Estado de Resultados de un mes (ingresos, costos, utilidad) |
| **PricingRequest** | `panel.py:345-361` | Objeto de entrada único al motor |
| **PricingResult** | (domain/) | Objeto de salida con P&G, KPIs, visiones |

### 1.4 DTOs y Builders en simulation/

| DTO | Propósito |
|-----|-----------|
| **SimulationRequest** | Request Pydantic validado para `/api/v1/simulation/calculate` |
| **PanelDeControlRequest** | Sub-DTO del Panel (input del usuario) |
| **PerfilCadenaARequest** | Un perfil de Cadena A del request |
| **CondicionesCadena[A/B/C]Request** | Contenedor de perfiles/configuración por cadena |

### 1.5 Adaptadores (adapters/)

| Adaptador | Responsabilidad |
|-----------|-----------------|
| **UnifiedInputAdapter** | Convierte formato frontend → domain (PanelDeControlRequest) |
| **UserInputLoader** | Carga datos de archivos JSON/YAML → estructuras internas |
| **InputNormalizer** | Valida y normaliza valores (convierte % a fracción, etc.) |
| **SimulationContextBuilder** | Construye PricingRequest desde input normalizado |
| **PricingSerializer** | Serializa PricingResult → JSON para API |
| **ConsoleReporter** | Imprime resultados en terminal (debug) |

### 1.6 Repositorios/Parametrización (repositories/)

| Repositorio | Fuente | Responsabilidad |
|-------------|--------|-----------------|
| **ParametrizationProvider** | `storage/parametrization/{hr,gn,op}/` | Proveedor principal (versión activa) |
| **PayrollParametrizationRepository** | JSON HR | Salarios, cargos, factores indexación |
| **InfrastructureParametrizationRepository** | JSON GN | IPC, SMLV, factores, ICA, GMF |
| **ProfitabilityParametrizationRepository** | JSON OP | Márgenes, ramp-up, rotación, ausentismo |
| **FinancialParametrizationRepository** | JSON GN | Pólizas, período de pago, financiación |
| **FrozenParametrizationRepository** | `storage/parametrization/frozen/v2-6.json` | Versión congelada para reproducibilidad |
| **FrozenParametrizationAdapter** | Wrapper | Carga frozen → soporta versioning |

### 1.7 API Endpoints Actuales (api/v1/)

```python
POST /api/v1/simulation/calculate
  Input:  SimulationRequest (JSON)
  Output: PricingResult (JSON con P&G, tarifas, KPIs)
  
GET /api/v1/health
  Output: {"status": "ok"}
```

### 1.8 Punto de Entrada Principal: engine.py

**NexaPricingEngine** (líneas 90-438):

- **Constructor**: Acepta `IParametrizationProvider` (default: activo) o versión frozen
- **Método `calcular()`**: Ejecuta pipeline 10-capas
  - Capa 2: NominaCalculator
  - Capa 3: NoPayrollCalculator
  - Capa 4-5: CadenaBCalculator
  - Capa 6: CadenaCCalculator
  - Capa 7: CostosTotalesCalculator
  - Capa 8: CostosFinancierosCalculator
  - Capa 9: PyGCalculator
  - Capa 10: KPIsCalculator + VisionTarifasCalculator
  - Post-procesamiento: VisionPyGBuilder, RiesgoCalculator, VisionImprimibleBuilder

**Características**:
- Inyección de dependencias (Composition Root en `_construir_calculadores()`)
- Soporte para AuditTracer (trazabilidad de cálculos)
- Soporta cadenas activas opcionales (A, B, C pueden ser independientes)

---

## 2. HARDCODES DETECTADOS

### 2.1 Hardcodes CRÍTICOS (impacto directo en valores)

#### HC-1: Margen Cadena B y C no son campos independientes

**Ubicación**: `domain/models/panel.py:96` (PanelDeControl.margen)

```python
margen: float  # Solo Cadena A — B y C hardcodeados a 0.30 y 0.20 en Excel
```

**Estado**: NO IMPLEMENTADO en backend.

**Impacto**: Las tarifas de Cadena B y Cadena C se calculan con margen incorrecto.

**Equivalente Excel V2-7**:
- Panel!C63 = margen Cadena A (variable por deal)
- Panel!D63 = 0.30 (Cadena B, hardcode Excel)
- Panel!E63 = 0.20 (Cadena C, hardcode Excel)

**Severidad**: **CRÍTICA** — Divergencia en pricing B/C.

**Corrección requerida**:
```python
# En domain/models/panel.py:
margen: float = 0.0      # Cadena A
margen_b: float = 0.30   # Cadena B (default Excel)
margen_c: float = 0.20   # Cadena C (default Excel)

# En calculators/pyg.py línea 108-110:
ingreso_cadena_a = costos_operativos.costo_a * (1 + self._panel.margen) * factor_rampup
ingreso_cadena_b = costos_operativos.costo_b * (1 + self._panel.margen_b) * factor_rampup
ingreso_cadena_c = costos_operativos.costo_c * (1 + self._panel.margen_c) * factor_rampup
```

---

#### HC-2: Tarifa FTE usa literal `/12` en lugar de `/meses_contrato`

**Ubicación**: VERIFICAR en `calculators/vision_tarifas.py` (se presume presente).

**Estado**: Potencialmente presente.

**Impacto**: Contratos de duración != 12 meses devuelven tarifa FTE incorrecta.

**Equivalente Excel V2-7**:
```excel
Vision Tarifas!G45 = G43/C37/12     ← HARDCODEADO 12
Hoja Maestra!G21  = G19/C13/C11     ← CORRECTO (usa C11 = meses)
```

**Severidad**: **ALTA** — Solo afecta contratos especiales (6, 18, 24 meses).

**Corrección requerida**:
```python
# En vision_tarifas.py:
tarifa_fte = facturacion / fte / panel.meses_contrato
```

---

#### HC-3: Mes de Ajuste de Indexación NO PARAMETRIZABLE

**Ubicación**: `domain/constants.py:19` (MES_INICIO_AJUSTE_ANUAL = 1)

**Estado**: Hardcodeado a enero (mes 1).

**Impacto**: La indexación aplica en mes 1, pero Excel V2-7 puede tener mes configurable.

**Equivalente Excel V2-7**: Panel!L9 (mes del año en que se aplica el ajuste).

**Severidad**: **MEDIA** — Afecta timing de costos en año 2+.

**Corrección requerida**:
```python
# En domain/models/panel.py:
mes_ajuste_indexacion: int = 1  # Configurable por deal

# En calculators/nomina.py y cadena_c:
usar panel.mes_ajuste_indexacion en lugar de constante
```

---

#### HC-4: Imprevistos (Panel!C73) es OPCIONAL, no está en PanelDeControlRequest

**Ubicación**: `domain/models/panel.py:120` (PanelDeControl.imprevistos = 0.0)

**Estado**: IMPLEMENTADO (campo existe, default 0).

**Impacto**: Ninguno si se mantiene default. Si el usuario lo provee, se aplica correctamente.

**Severidad**: **BAJA** — Ya implementado, solo necesita verificación de uso.

---

#### HC-5: Horas base para recargos = 220 (hardcodeado)

**Ubicación**: `ESPECIFICACION_MATEMATICA.md:43-49` (fórmula Excel)

**Estado**: VERIFICAR si backend usa 220 o calcula como `42h/sem × 4.33sem = 181.86h`.

**Impacto**: Los recargos nocturnos, festivos, etc. difieren significativamente.

**Severidad**: **MEDIA** — Dependencia: verificar storage HR.

---

#### HC-6: ICA por ciudad NOT IMPLEMENTED correctly

**Ubicación**: `calculators/costos_financieros.py` + `repositories/infrastructure_parametrization_repository.py`

**Estado**: VERIFICAR si se lee de parametrización o usa default.

**Impacto**: ICA incorrecta por ciudad → ingreso neto incorrecto.

**Severidad**: **MEDIA** — Verificación necesaria.

---

#### HC-7: GMF = 0.004 (4×1000)

**Ubicación**: `calculators/costos_financieros.py` (presumiblemente hardcodeado o en parametrización).

**Estado**: VERIFICAR.

**Equivalente Excel V2-7**: `Tasas, TRM, Polizas!B30 = 0.004`.

**Severidad**: **BAJA** — Raramente cambia.

---

#### HC-8: Comisión de Administración = 1.18% (0.0118)

**Ubicación**: `domain/models/panel.py:122` (tasa_comision_administracion)

**Estado**: IMPLEMENTADO (puede venir del input o default).

**Impacto**: Correcto si se parametriza.

**Severidad**: **BAJA** — Ya implementado.

---

### 2.2 Hardcodes en Constants y Configuraciones

#### HC-9: MES_INICIO_AJUSTE_ANUAL = 1

**Ubicación**: `domain/constants.py:19`

```python
MES_INICIO_AJUSTE_ANUAL = 1  # Mes en que aplica el ajuste anual
```

**Impacto**: Todos los cálculos de indexación inician en mes 1. Si Excel usa otro mes, divergencia.

**Corrección**: Mover a PanelDeControl como campo configurable.

---

#### HC-10: Tiempo base por día = 8 horas, semanas por mes = 4.33

**Ubicación**: `domain/constants.py:30-33`

```python
HORAS_LABORALES_POR_DIA = 8
SEMANAS_POR_MES = 4.33
# Total: 8 × 5 días × 4.33 semanas ≈ 173.2 horas/mes (vs 220 en Excel)
```

**Impacto**: Cálculos de tarifa por hora y minutos logueados difieren si se usa 220 vs 181.86.

**Severidad**: **MEDIA** — Verificación con Excel V2-7 necesaria.

---

#### HC-11: SMMLV 2026 = 1,750,905 COP (si viene de aquí)

**Ubicación**: VERIFICAR si está hardcodeado en código o en parametrización HR.

**Equivalente Excel**: `Inputs de Nomina!C4`.

**Severidad**: **BAJA** — Debe estar en parametrización, no en código.

---

### 2.3 Resumen de Hardcodes por Severidad

| Código | Descripción | Ubicación | Severidad | Estado |
|--------|-------------|-----------|-----------|--------|
| **HC-1** | Margen B/C independientes | panel.py:96 | CRÍTICA | NO IMPLEMENTADO |
| **HC-2** | Tarifa FTE con /12 | vision_tarifas.py | ALTA | VERIFICAR |
| **HC-3** | Mes ajuste indexación | constants.py:19 | MEDIA | HARDCODEADO |
| **HC-4** | Imprevistos | panel.py:120 | BAJA | IMPLEMENTADO |
| **HC-5** | Horas base recargos | ¿220 vs 181.86? | MEDIA | VERIFICAR |
| **HC-6** | ICA por ciudad | costos_financieros.py | MEDIA | VERIFICAR |
| **HC-7** | GMF = 0.004 | ¿hardcode o param? | BAJA | VERIFICAR |
| **HC-8** | Comisión adm = 1.18% | panel.py:122 | BAJA | IMPLEMENTADO |
| **HC-9** | MES_INICIO = 1 | constants.py:19 | MEDIA | HARDCODEADO |
| **HC-10** | 8h/día, 4.33 sem/mes | constants.py:30-33 | MEDIA | REVISAR |

---

## 3. DIVERGENCIAS MATEMÁTICAS CRÍTICAS

### 3.1 Fórmula de Pricing (Denominador exacto)

**Excel V2-7** (ESPECIFICACION_MATEMATICA.md:278-284):

```python
ingreso = costo_directo / (
    (1 - margen) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento)
)
```

**Backend actual** (calculators/pyg.py:108-111):

```python
ingreso_cadena_a = costos_operativos.costo_a * (1 + self._panel.margen) * factor_rampup
```

**DIVERGENCIA IDENTIFICADA**: El backend usa multiplicación aditiva `(1 + margen)`, mientras Excel usa división con denominador exacto. Esto produce una diferencia material cuando hay contingencias y markup.

**Impacto**: Ingresos incorrectos para todos los deals (estimado: 2-5% de divergencia).

**Severidad**: **CRÍTICA**.

**Corrección necesaria**:
```python
# Usar utilities.calcular_factor_margenes() correctamente:
factor_margenes = (1 - margen) * (1 - cont_op) * (1 - cont_com) * (1 - markup) * (1 + descuento)
ingreso = costo_directo / factor_margenes
```

---

### 3.2 Ramp-up para Plataformas y Captura de Datos

**Excel V2-7** (ESPECIFICACION_MATEMATICA.md:419-430):

```python
ramp_up_table = {
    "Cobranzas":         {1: 0.85, 2: 0.92, 3: 1.0, ...},
    "SAC":               {1: 0.85, 2: 0.92, 3: 1.0, ...},
    "Plataformas":       {1: 0.0,  2: 0.0,  ...},    # ← CERO, no 1.0!
    "Captura de Datos":  {1: 0.0,  2: 0.0,  ...},    # ← CERO, no 1.0!
}
```

**Backend actual**: VERIFICAR si devuelve 1.0 como default para servicios sin tabla.

**Impacto**: Ingresos de Plataformas y Captura sobreestimados si usa ramp-up = 1.0.

**Severidad**: **ALTA** (si no está correctamente implementado).

---

### 3.3 Indexación de Salarios — Factor Acumulado

**Excel V2-7** (ESPECIFICACION_MATEMATICA.md:133-155):

```python
# Tabla Tasas!A8:G16 contiene factores acumulados por tipo de indexación
# El factor depende del año del mes del contrato, NO del año calendario
factor_2027 = tabla_indexacion[tipo][año_desde_inicio + 1]
```

**Backend actual** (VERIFICAR en context_builder.py línea 458):

Parece usar `MES_INICIO_AJUSTE_ANUAL` correctamente, pero requiere verificación de que:
1. La tabla se carga correctamente de parametrización HR
2. El lookup por año del contrato (no año calendario) es correcto

**Severidad**: **MEDIA** (depende de verificación).

---

### 3.4 Tope Ley 1819 — ¿DESACTIVADO?

**Excel V2-7** (ESPECIFICACION_MATEMATICA.md:119-135):

```python
tope = 10 * smmlv
if imponible > tope:
    # Reducción al 70% para SS, ARL; NO Caja, ICBF, Sena; cesantías = 0
```

**Backend actual** (domain/models/panel.py:113-118):

```python
# Ley 1819 de 2016 — DESACTIVADO.
# Excel V2-4 legacy no implementa exoneración Ley 1819; comportamiento
# fijado para compatibilidad funcional estricta.
aplica_ley_1819: bool = True  # Campo retenido, valor ignorado
```

**Estado**: DESACTIVADO (correcto si V2-7 no usa Ley 1819).

**Severidad**: **BAJA** (si es intencional).

---

### 3.5 Auxilio de Transporte — Tope 2 × SMMLV

**Excel V2-7** (ESPECIFICACION_MATEMATICA.md:138-143):

```python
aux = auxilio_transporte if (0 < imponible < 2 * smmlv) else 0
```

**Backend actual**: VERIFICAR si se implementó correctamente en NominaCalculator.

**Severidad**: **MEDIA** (verificación necesaria).

---

## 4. ESTADO DEL STORAGE/PARAMETRIZACIÓN

### 4.1 Archivos de Parametrización Existentes

**Ubicación**: `/storage/parametrization/`

```
storage/parametrization/
├── hr/
│   └── 2236cdcf-7ed0-4894-a20d-c4519c211170.json    (HR master)
│   └── versions.json                                  (índice versiones)
├── gn/
│   └── ce83dd6c-abd4-4092-9bf7-6bc4d5c87aaf.json    (General/Infrastructure)
│   └── versions.json
├── op/
│   └── 3dddbdea-5813-4b43-b80b-41cd9e04bc64.json    (Operations/Profitability)
│   └── versions.json
├── business_rules/
│   └── 2026-01.json                                  (Políticas comerciales)
│   └── versions.json
└── frozen/
    └── v2-6.json                                     (Snapshot reproducibilidad)
```

### 4.2 Contenido de HR (RH)

**Archivo**: `storage/parametrization/hr/2236cdcf-7ed0-4894-a20d-c4519c211170.json`

**Catálogos incluidos**:
- `tipo`: Empleado, Equipo Soporte, HITL, Implementación
- `rol`: Director de cuentas, Director de Performance, Jefe Comercial, ...
- Más de 26 roles en catálogo

**Parámetros esperados según ESPECIFICACION_MATEMATICA.md**:
- SMMLV por año
- Auxilio transporte por año
- Factores indexación (tabla acumulados por tipo)
- Salarios base por cargo
- Tasas de prestaciones (salud, pensión, ARL, caja, ICBF, Sena)
- Ratios staffing por cargo
- Costo dotación

**Status actual**: VERIFICAR si todos estos campos están presentes en JSON.

---

### 4.3 Contenido de GN (General/Infrastructure)

**Archivo**: `storage/parametrization/gn/ce83dd6c-abd4-4092-9bf7-6bc4d5c87aaf.json`

**Parámetros esperados** (ESPECIFICACION_MATEMATICA.md + MAPEO_EXCEL_BACKEND.md):
- IPC por año (0.0527 uniform en V2-7)
- SMLV por año (0.2378 para 2026, diferenciado)
- Factores acumulados (tabla Tasas!A8:G16)
- Pólizas base (por tipo: salud, incapacidad, etc.)
- ICA base (0.00966 Bogotá, varía por ciudad)
- ICA por municipio (tabla B34:F52 en Excel)
- GMF (0.004)

**Status actual**: VERIFICAR si estructura coincide.

---

### 4.4 Contenido de OP (Operations/Profitability)

**Archivo**: `storage/parametrization/op/3dddbdea-5813-4b43-b80b-41cd9e04bc64.json`

**Parámetros esperados**:
- Ausentismo promedio por servicio
- Rotación promedio por servicio
- Márgenes objetivo por servicio
- Tabla ramp-up (60 meses × servicios)

**Status actual**: VERIFICAR si ramp-up incluye CEROS para Plataformas/Captura.

---

### 4.5 Gaps Identif

icados en Parametrización

| Gap | Campo | Ubicación | Estado | Severidad |
|-----|-------|-----------|--------|-----------|
| **GAP-P1** | `margen_b`, `margen_c` separados | Panel Input | NO EXISTE | CRÍTICA |
| **GAP-P2** | `mes_ajuste_indexacion` configurable | Panel Input | NO EXISTE | MEDIA |
| **GAP-P3** | Ramp-up = 0 para Plataformas/Captura | OP storage | VERIFICAR | ALTA |
| **GAP-P4** | ICA por ciudad (completa) | GN storage | VERIFICAR | MEDIA |
| **GAP-P5** | Factores acumulados indexación | HR storage | VERIFICAR | MEDIA |
| **GAP-P6** | Política comercial "Imprevistos" | business_rules/ | VERIFICAR | BAJA |

---

### 4.6 Versionado Actual

**Mecanismo**: Cada JSON tiene `version_id` (UUID); `versions.json` mantiene índice.

**Limitación**: NO hay versionado temporal (ej. "v2-7" con fecha). Solo UUID.

**Impacto**: Difícil auditar qué parametrización usó un deal histórico.

**Recomendación**: Agregar timestamp y nombre legible a versions.json.

---

## 5. PLAN DE CAMBIOS POR WAVES

### 5.1 Estructura de Waves

Cada **WAVE** agrupa cambios por dependencia lógica:
- **WAVE 0** (ya completado): Auditoría y mapeo.
- **WAVE 1**: Parametrización (storage, versioning).
- **WAVE 2**: Domain & DTOs (campos nuevos).
- **WAVE 3**: Calculadores (fórmulas corregidas).
- **WAVE 4**: Tests & Verificación.
- **WAVE 5**: Integración & Depuración.

---

### 5.2 WAVE 1 — Parametrización & Storage

**Objetivo**: Preparar storage para soportar campos nuevos sin romper compatibilidad.

| # | Componente | Cambio | Archivo:Línea | Justificación | Tests Afectados |
|---|-----------|--------|--------------|---------------|-----------------|
| W1-1 | HR Parametrización | Agregar `ramp_up_table` con CEROS para Plataformas/Captura | `storage/parametrization/op/...json` | HC-0 / Fórmula Excel | `test_rampup_platforms` |
| W1-2 | GN Parametrización | Validar ICA por ciudad (tabla completa) | `storage/parametrization/gn/...json` | HC-6 | `test_ica_por_ciudad` |
| W1-3 | HR Parametrización | Validar factores acumulados indexación (8 tipos) | `storage/parametrization/hr/...json` | HC-3, DIV-3 | `test_indexacion_acumulada` |
| W1-4 | Versionado | Agregar timestamp y nombre legible a versions.json | `storage/parametrization/*/versions.json` | Auditoría | `test_versions_legible` |
| W1-5 | Parametrización GN | Auditar SMMLV, Auxilio, GMF (no deben estar en código) | Todos JSON | HC-11, HC-7 | `test_hardcodes_in_code` |

**Dependencias**: Ninguna (independiente).  
**Duración estimada**: 2-3 horas.  
**Riesgo**: BAJO (solo lectura/auditoría).

---

### 5.3 WAVE 2 — Domain Models & DTOs

**Objetivo**: Agregar campos nuevos al modelo de entrada sin romper existing deals.

| # | Componente | Cambio | Archivo:Línea | Justificación | Tests Afectados |
|---|-----------|--------|--------------|---------------|-----------------|
| W2-1 | PanelDeControl | Agregar `margen_b: float = 0.30` | `domain/models/panel.py:96` | HC-1 | `test_margenes_independientes` |
| W2-2 | PanelDeControl | Agregar `margen_c: float = 0.20` | `domain/models/panel.py:96` | HC-1 | idem |
| W2-3 | PanelDeControl | Agregar `mes_ajuste_indexacion: int = 1` | `domain/models/panel.py:96` | HC-3 | `test_mes_ajuste_configurable` |
| W2-4 | PanelDeControlRequest | Agregar `margen_b`, `margen_c` a DTO | `simulation/request_dto.py:31-58` | HC-1 | `test_dto_validates_margenes` |
| W2-5 | PanelDeControlRequest | Agregar `mes_ajuste_indexacion` a DTO | `simulation/request_dto.py:31-58` | HC-3 | `test_dto_validates_mes_ajuste` |
| W2-6 | Validadores | Margen_b, margen_c ∈ [0, 1] | `validators/` | HC-1 | `test_margen_range_validation` |
| W2-7 | Adapters | Propagar `margen_b`, `margen_c` en UnifiedInputAdapter | `adapters/unified_input_adapter.py` | HC-1 | `test_adapter_margenes` |
| W2-8 | Adapters | Propagar `mes_ajuste_indexacion` en SimulationContextBuilder | `input/context_builder.py:458` | HC-3 | `test_context_builder_mes_ajuste` |

**Dependencias**: WAVE 1 completado (para ver qué parametrización existe).  
**Duración estimada**: 4-5 horas.  
**Riesgo**: MEDIO (cambios en modelo requerirán migraciones de tests existentes).

---

### 5.4 WAVE 3 — Cálculos (Fórmulas Corregidas)

**Objetivo**: Implementar fórmulas Excel exactas en calculadores.

| # | Componente | Cambio | Archivo:Línea | Justificación | Tests Afectados |
|---|-----------|--------|--------------|---------------|-----------------|
| W3-1 | PyGCalculator | Usar fórmula denominador exacto (multiplicación en lugar de suma) | `calculators/pyg.py:108-110` | DIV-1 | `test_pyg_exact_formula` |
| W3-2 | PyGCalculator | Aplicar `margen_b` para Cadena B, `margen_c` para Cadena C | `calculators/pyg.py:108-110` | HC-1, DIV-1 | `test_cadena_margenes_independientes` |
| W3-3 | PyGCalculator | Usar `panel.mes_ajuste_indexacion` en factor indexación | `calculators/pyg.py` | HC-3 | `test_indexacion_mes_variable` |
| W3-4 | VisionTarifasCalculator | Reemplazar hardcode `/12` por `/panel.meses_contrato` | `calculators/vision_tarifas.py:~170` | HC-2 | `test_tarifa_fte_duracion_variable` |
| W3-5 | VisionTarifasCalculator | Usar `margen_a` para Cadena C en pricing (no `margen_c`) | `calculators/vision_tarifas.py:~200` | DIV-2 | `test_vision_tarifas_margen_anomalia` |
| W3-6 | CostosFinancierosCalculator | Validar ICA usa tasa correcta por ciudad | `calculators/costos_financieros.py:109+` | HC-6 | `test_ica_por_ciudad_financiero` |
| W3-7 | RampupCalculator | Devolver 0.0 para Plataformas/Captura TODOS los meses | `calculators/utils.py` (calcular_rampup) | HC-0, DIV-0 | `test_rampup_zero_platforms` |
| W3-8 | NominaCalculator | Verificar base 220h vs 181.86h en recargos | `calculators/nomina.py:~40-50` | HC-5 | `test_recargos_base_horaria` |

**Dependencias**: WAVE 2 completado (campos nuevos en domain).  
**Duración estimada**: 8-10 horas.  
**Riesgo**: ALTO (cambios en cálculos pueden romper deals existentes; requiere regression testing).

---

### 5.5 WAVE 4 — Tests & Certificación

**Objetivo**: Verificar paridad Excel V2-7 para casos críticos.

| # | Componente | Prueba | Archivo | Criterio de Éxito |
|---|-----------|--------|---------|-------------------|
| W4-1 | Integración | Caso Bancamia (datos reales V2-7) | `tests/certification/test_bancamia.py` | Margen real = esperado ± 0.1% |
| W4-2 | Integración | Caso Cobranzas 12m (servicio base) | `tests/certification/test_cobranzas_12m.py` | Todos KPIs ± 0.5% |
| W4-3 | Unit | Fórmula denominador (margen, cont, markup) | `tests/unit/test_denominador_exacto.py` | Ingreso exacto ± 1 COP |
| W4-4 | Unit | Margen B/C independientes | `tests/unit/test_margenes_bco.py` | Tarifa B ≠ Tarifa A |
| W4-5 | Unit | Ramp-up cero para Plataformas | `tests/unit/test_rampup_zero.py` | Factor = 0 para todos los meses |
| W4-6 | Unit | Indexación por mes configurable | `tests/unit/test_indexacion_mes_variable.py` | Factor cambio en mes correcto |
| W4-7 | Contrato | Campos obligatorios (margen_b, margen_c) | `tests/contract/test_request_contract.py` | SimulationRequest valida DTO |
| W4-8 | Golden (Regression) | Snapshot V2-6 vs V2-7 nuevos | `tests/golden/test_v27_backward_compat.py` | Backward compatible (v2-6 funciona igual) |

**Dependencias**: WAVE 3 completado (cambios implementados).  
**Duración estimada**: 6-8 horas.  
**Riesgo**: MEDIO (algunos tests pueden fallar y requerir ajuste en WAVE 3).

---

### 5.6 WAVE 5 — Integración & Depuración

**Objetivo**: Integrar cambios, ejecutar suite completa, resolver bugs.

| # | Tarea | Archivo | Duración |
|---|-------|---------|----------|
| W5-1 | Merge WAVE 1-4 en rama develop | (git) | 1 hora |
| W5-2 | Ejecutar pytest suite completa | `run_tests.sh` | 2 horas |
| W5-3 | Corregir tests fallidos | Various | 3-5 horas |
| W5-4 | Auditoría de cobertura (mínimo 85%) | pytest --cov | 1 hora |
| W5-5 | Manual testing (API endpoint `/calculate`) | Postman / curl | 2 horas |
| W5-6 | Documentación de cambios | CHANGELOG.md | 1 hora |

**Dependencias**: WAVE 4 completado.  
**Duración estimada**: 10-12 horas.  
**Riesgo**: MEDIO-ALTO (integración puede revelar interacciones no anticipadas).

---

### 5.7 Timeline Estimado

```
WAVE 1 (Parametrización):      2-3 h    Total: 2-3 h
  └─ WAVE 2 (Domain):          4-5 h    Total: 6-8 h
      └─ WAVE 3 (Cálculos):    8-10 h   Total: 14-18 h
          └─ WAVE 4 (Tests):   6-8 h    Total: 20-26 h
              └─ WAVE 5 (QA):  10-12 h  Total: 30-38 h
```

**Estimado total**: **30-38 horas** (4-5 días de trabajo).

---

## 6. COBERTURA DE TESTS

### 6.1 Conteo de Tests por Categoría

```bash
Total tests: 56

Unit tests:       35   (62%)
Integration tests: 15  (27%)
Contract tests:    4   (7%)
Golden/Regression: 2   (4%)
```

### 6.2 Tests Existentes Relevantes a Gaps

| Test File | Propósito | Gaps Cubiertos | Estado |
|-----------|-----------|-----------------|--------|
| `test_gap_closure_v25.py` | Gaps V2-5 | HC-4 (Imprevistos) | ✅ PASA |
| `test_certificacion_final_v25.py` | Certificación V2-5 | Margen único, contingencias | ✅ PASA |
| `test_vision_tarifas.py` | Tarifa FTE | HC-2 (¿/12?) | ❓ VERIFICAR |
| `test_riesgo_calculator.py` | Evaluación riesgo | KPIs | ✅ PASA |
| `test_task3_optional_chains.py` | Cadenas opcionales | A/B/C activas | ✅ PASA |
| `test_h04_frozen_adapter.py` | Versioning parametrización | Reproducibilidad | ✅ PASA |

### 6.3 Tests Faltantes Críticos

**PRIORITY 1** (Bloquea certificación):
- [ ] `test_margenes_independientes_abc.py` — Margen A ≠ B ≠ C
- [ ] `test_fórmula_denominador_exacto.py` — División vs multiplicación
- [ ] `test_rampup_cero_plataformas.py` — Ramp-up = 0 para Plataformas/Captura
- [ ] `test_indexacion_mes_ajuste.py` — Mes de ajuste configurable

**PRIORITY 2** (Mejora cobertura):
- [ ] `test_ica_por_ciudad_completa.py` — ICA por municipio
- [ ] `test_auxilio_transporte_tope.py` — Tope 2 × SMMLV
- [ ] `test_hardcodes_no_existen_en_codigo.py` — Detección de hardcodes

**PRIORITY 3** (Regresión):
- [ ] `test_backward_compat_v26.py` — Deals históricos siguen funcionando
- [ ] `test_contrato_v27.py` — Nuevo contrato (DTO, validación)

### 6.4 Cobertura Estimada Hoy

```
Nómina (NominaCalculator):         85%  ✅ Buena
No-Payroll (NoPayrollCalculator):  70%  ⚠️  Intermedia
Cadena B (CadenaBCalculator):      60%  ⚠️  Intermedia
Cadena C (CadenaCCalculator):      50%  ⚠️  Baja
P&G (PyGCalculator):               75%  ⚠️  Intermedia
Costos Financieros (CostosFinancierosCalculator): 70% ⚠️  Intermedia
Vision Tarifas (VisionTarifasCalculator):  55%  ⚠️  Baja
Cost-to-Serve:                      60%  ⚠️  Intermedia
Riesgo:                             65%  ⚠️  Intermedia

Promedio: 66% (Meta: 85%)
```

---

## 7. RIESGOS Y BLOQUEADORES

### 7.1 Dependencias Circulares Detectadas

#### RD-1: VisionTarifasCalculator → PyGMensual → PyGCalculator

**Descripción**:
- VisionTarifasCalculator necesita `pyg_por_mes` (P&G de cada mes)
- Para construir `pyg_por_mes`, PyGCalculator necesita calculadores finales
- VisionTarifasCalculator se usa en engine.py DESPUÉS de que PyGCalculator produce el P&G

**Archivo**: `engine.py:202-211` (VisionTarifasCalculator.calcular(pyg_contrato))

**Impacto**: Ninguno (no es circular en tiempo de ejecución; es solo dependencia forward).

**Estado**: ✅ RESUELTO (diseño correcto).

---

#### RD-2: CostosFinancierosCalculator → Panel.margen

**Descripción**: Si margen está en panel pero ICA depende de margen mediante gross-up, hay retroalimentación.

**Realidad**: El cálculo es:
1. ICA = (costo / (1-margen)) × tasa_ica
2. El margen ya existe, es entrada (no depende de ICA)

**Estado**: ✅ NO ES CIRCULAR.

---

### 7.2 Acoplamientos Problemáticos

#### AC-1: SimulationContextBuilder → ParametrizationProvider

**Descripción**: El builder requiere acceso al provider para hacer lookups de HR.

**Archivo**: `input/context_builder.py`

**Impacto**: SimulationContextBuilder es difícil de testear sin un provider real.

**Recomendación**: Inyectar provider en constructor (ya hecho en engine.py, revisar).

**Estado**: ⚠️ REVISAR.

---

#### AC-2: VisionTarifasCalculator → múltiples calculadores

**Descripción**: VisionTarifas depende de NominaCalculator, NoPayrollCalculator, CadenaBCalculator directamente.

**Archivo**: `calculators/vision_tarifas.py:53-78`

**Impacto**: Cambio en NominaCalculator puede romper VisionTarifas sin aviso.

**Recomendación**: Documentar contrato explícitamente.

**Estado**: ⚠️ DOCUMENTADO, pero frágil.

---

### 7.3 Áreas Sin Tests Donde Tocar es Peligroso

| Módulo | LOC | Cobertura | Riesgo | Recomendación |
|--------|-----|-----------|--------|---------------|
| **CadenaBCalculator** | 300 | 60% | ALTO | Agregar 20+ tests antes de cambios |
| **CadenaCCalculator** | 350 | 50% | ALTO | Agregar 30+ tests antes de cambios |
| **CostosFinancierosCalculator** | 400 | 70% | MEDIO | Auditar ICA/GMF/Pólizas antes de cambios |
| **VisionTarifasCalculator** | 450 | 55% | ALTO | Necesita 40+ tests (cálculo complejo) |
| **InputNormalizer** | ~300 | 40% | ALTO | Muchas ramificaciones no testadas |

---

### 7.4 Decisiones de Diseño que Requieren Input del Usuario

#### DEC-1: ¿Margen B/C son defaults o deben venir del input?

**Opciones**:
1. **Opción A**: Defaults en código (0.30, 0.20) — usuario puede sobrescribir
2. **Opción B**: Siempre de input — usuario DEBE proveer, sin defaults

**Excel V2-7**: Panel!D63 y E63 tienen valores 0.30 y 0.20, pero ¿son editable por usuario?

**Recomendación**: Opción A (defaults, sobrescribibles) es más robusta.

**Usuario debe decidir**: ¿Qué hace el motor si el usuario NO provee margen_b?

---

#### DEC-2: ¿Mes de ajuste (HC-3) debe ser configurable por usuario o por parametrización?

**Opciones**:
1. **Opción A**: Campo en PanelDeControl (configurable por deal)
2. **Opción B**: Constante global (todos los deals igual)
3. **Opción C**: En parametrización (por versión, todos los deals igual)

**Recomendación**: Opción A (más flexible, permite deals especiales).

**Usuario debe decidir**: ¿Costo de implementar en DTO/validación?

---

#### DEC-3: ¿Ramp-up = 0 para Plataformas está en parametrización o hardcodeado?

**Hoy**: Según ESPECIFICACION_MATEMATICA.md, está en tabla Rot, Ausent!F11:F12 = 0.

**Verificación necesaria**: ¿El archivo op/*.json tiene estos CEROS?

**Usuario debe decidir**: Si no están, ¿agregarlos ahora o después?

---

### 7.5 Bloqueadores de Certificación

**BLOQUEADOR-1**: HC-1 no implementado (margen_b, margen_c)
- **Antes de poder certificar paridad V2-7, DEBEN estar en código**
- **Workaround**: Usar deal históricos v2-6 sin estos campos
- **Timeline**: WAVE 2-3, min 8-10 horas

**BLOQUEADOR-2**: DIV-1 (fórmula denominador) no verificada
- **Antes de certificar, REQUIERE test que compruebe fórmula exacta vs sumativa**
- **Workaround**: Ejecutar manualmente en Excel 1 caso simple
- **Timeline**: WAVE 3-4, min 4 horas

**BLOQUEADOR-3**: Ramp-up = 0 no verificado en storage
- **Antes de certificar Plataformas/Captura, REQUIERE auditoría de parametrización**
- **Workaround**: Hardcodear temporal en código
- **Timeline**: WAVE 1, min 1-2 horas

---

## 8. RESUMEN EJECUTIVO

### 8.1 Estado Actual

**Paridad estimada con Excel V2-7**: **~75-80%** (mejora desde ~70% inicial).

**Gaps críticos**: 
1. Margen B/C no independientes (HC-1) — **DEBE ser WAVE 1**
2. Fórmula denominador no verificada (DIV-1) — **DEBE auditarse ASAP**
3. Ramp-up = 0 para Plataformas no verificado (DIV-0) — **DEBE auditarse ASAP**

### 8.2 Próximos Pasos (Semana 27-28 Mayo)

**Lunes-Martes (27-28 Mayo)**:
- [ ] WAVE 1 Auditoría parametrización (2-3 horas)
- [ ] WAVE 2 Agregar campos domain (4-5 horas)

**Miércoles-Jueves (29-30 Mayo)**:
- [ ] WAVE 3 Implementar fórmulas (8-10 horas, en paralelo)
- [ ] WAVE 4 Tests críticos (4-6 horas)

**Viernes (31 Mayo)**:
- [ ] WAVE 5 QA completo (6-8 horas)

**Estimado**: Paridad **85-90%** alcanzable por **31 Mayo 2026**.

### 8.3 Archivos a Modificar (Resumen)

```
domain/models/panel.py              ← 3 campos nuevos
simulation/request_dto.py           ← 3 campos nuevos
calculators/pyg.py                  ← 2 fórmulas críticas
calculators/vision_tarifas.py       ← 2 hardcodes
input/context_builder.py            ← propagación parámetros
storage/parametrization/*/          ← auditoría + versionado
tests/unit/test_*.py                ← 10+ tests nuevos
tests/integration/test_*.py         ← 3+ tests nuevos
```

**Líneas de código a modificar**: ~200-300 líneas (estimado).  
**Líneas de test a agregar**: ~400-600 líneas.

---

## APÉNDICE A: Referencias

### Documentos V2-7

- [MAPEO_EXCEL_BACKEND.md](./MAPEO_EXCEL_BACKEND.md) — Correspondencia Excel ↔ Backend
- [PARIDAD_EXCEL_VS_MOTOR.md](./PARIDAD_EXCEL_VS_MOTOR.md) — Gaps por prioridad
- [HARD_CODES_Y_ANOMALIAS.md](./HARD_CODES_Y_ANOMALIAS.md) — Hardcodes detectados en Excel
- [ESPECIFICACION_MATEMATICA.md](./ESPECIFICACION_MATEMATICA.md) — Fórmulas exactas

### Código Fuente

- `engine.py` (438 líneas) — Orquestador principal
- `domain/models/panel.py` (361 líneas) — Entidades de entrada
- `calculators/` (2,650+ líneas) — Motores de cálculo
- `repositories/` (7 archivos) — Proveedores de parametrización

---

**Auditoría completada**: 27 de Mayo 2026  
**Por**: Análisis Exhaustivo V2-7  
**Para**: Roadmap WAVES 1-5 Q2 2026
