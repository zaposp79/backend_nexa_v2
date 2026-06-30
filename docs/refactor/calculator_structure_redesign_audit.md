# CALCULATOR_STRUCTURE_REDESIGN_AUDIT_V2

**Fecha:** 2026-06-09  
**Autor:** Claude Code (Haiku 4.5)  
**Riesgo:** MEDIO/ALTO (refactor arquitectónico transversal)  
**Estado:** FASES 1-5F COMPLETAS ✅ — 5D (risk) IMPLEMENTADA — 5E/5F AUDIT-ONLY — 5G PRÓXIMA

---

## Resumen Ejecutivo

El proyecto NEXA tiene una **separación deficiente entre motor de cálculo puro y infraestructura**. Hoy:

- `modules/calculator/` mezcla **API, persistencia, helpers y cálculo puro**.
- `modules/riesgo/` vive separado siendo **cálculo puro que debería estar en calculator**.
- Payroll/no-payroll viven en `modules/cadena_a/` siendo **cálculo que podría centralizarse en calculator**.
- Los **serializadores y adaptadores están dispersos** sin estructura clara.

**Propuesta:** Reorganizar `modules/calculator/` para que sea **100% puro motor de cálculo**, con subdomios bien delimitados.

**Beneficios:**
- Mejor testabilidad (cálculos sin IO)
- Claridad arquitectónica (responsabilidades únicas)
- Facilita auditoría y paridad Excel
- Prepara para escalado futuro

**Riesgos:**
- Cambio de imports masivo
- Potencial ruptura de contratos si no se gestiona con cuidado
- Actualizaciones de 100+ archivos

---

## 1. Estructura Actual

### 1.1 modules/calculator/ (hoy)

```
modules/calculator/
├── engine.py                          ← ORQUESTADOR PRINCIPAL (764 líneas)
├── context_builder.py                 ← CONSTRUCTOR DE CONTEXTO (292 líneas)
├── input_normalizer.py                ← NORMALIZACIÓN INPUT
├── user_input_loader.py               ← LOADER INPUT USUARIO
├── input_validator.py                 ← VALIDADOR INPUT
├── serializer.py                      ← ALIAS
├── json_loader.py                     ← LOADER JSON
├── api/                               ⚠️  INFRAESTRUCTURA (HTTP, DTOs, routers)
│   ├── calculate_router.py            (HTTP REST endpoint)
│   ├── calculate_dto.py               (DTOs para HTTP)
│   ├── calculate_normal_handler.py    (lógica HTTP)
│   ├── calculate_certified_handler.py (lógica HTTP certificada)
│   ├── calculate_validate.py          (validaciones HTTP)
│   ├── results_router.py              (HTTP REST endpoint)
│   └── calculate_dependencies.py      (DI para HTTP)
├── adapters/                          ✓ ADAPTADORES (entrada data)
│   ├── entry_data_adapter.py
│   └── volume_resolution.py
├── audit/                             ✓ AUDITORÍA/TRACING
│   └── trace_integration.py           (tracing de cálculos)
├── constants/                         ✓ CONSTANTES
│   └── global_constants.py
├── dto/                               ⚠️  MEZCLA DE DTOs
│   ├── user_inputs.py                 (HTTP input)
│   ├── request_dto.py                 (Request interno)
│   └── normalized_input.py            (Input normalizado)
├── helpers/                           ✓ HELPERS MATEMÁTICOS
│   ├── engine_helpers.py              (redondeos, conversiones)
│   └── console_reporter.py            (reporting, no cálculo)
├── lineage/                           ✓ LINEAGE/TRACES
│   └── snapshot_builder.py            (construcción de snapshots)
├── mixins/                            ⚠️  MEZCLA DE RESPONSABILIDADES
│   ├── context_builder_*.py           (20 archivos)
│   └── input_normalizer_*.py          (mezcla de lógica de contexto)
├── models/                            ✓ MODELOS
│   ├── data_provenance.py
│   └── snapshot.py
├── persistence/                       ⚠️  PERSISTENCIA/IO
│   ├── results_repository.py          (DocumentStore)
│   ├── traceability_repository.py     (DocumentStore)
│   └── ... (otros repos)
├── pricing/                           ✓ CÁLCULO PURO (pero poco usado)
│   └── calculators.py                 (pricing utils)
├── serializers/                       ✓ SERIALIZACIÓN
│   ├── pricing_result_serializer.py
│   └── serializer_helpers.py
├── use_cases/                         ⚠️  POSIBLE DUPLICADO
│   └── (varios use cases)
└── validation/                        ✓ VALIDACIÓN
    ├── contract_validator.py
    └── simulation_request_validator.py
```

**Problemas identificados:**

| Categoría | Problemas |
|-----------|-----------|
| **API en calculator** | `api/` no debería estar aquí; rompe separación motor/infraestructura |
| **Persistencia en calculator** | `persistence/` mezcla motor con DocumentStore/IO |
| **Mixins sin estructura** | 20 archivos de mixins sin organización clara |
| **DTOs duplicados** | `dto/` tiene mezcla de HTTP DTOs e internos |
| **Helpers dispersos** | Redondeos/conversiones sin centralizar |
| **Uso_cases vs API** | Posible duplicación de orquestación |

### 1.2 modules/riesgo/ (hoy)

```
modules/riesgo/
├── __init__.py
└── reglas.py (448 líneas)     ← CÁLCULO PURO (RiesgoCalculator)
```

**Análisis:**
- ✓ Sin API
- ✓ Sin persistencia
- ✓ Sin IO
- ✓ Cálculo puro: evaluación de riesgo con 10 criterios (cliente + operativo)
- ✓ Carga reglas desde YAML canónico
- **Conclusión:** DEBE MOVERSE A `modules/calculator/risk/`

### 1.3 Payroll / No-Payroll (hoy)

**Ubicación actual:** `modules/cadena_a/`

```
modules/cadena_a/
├── nomina.py                  ← NominaCalculator (Capa 2)
├── no_payroll.py              ← NoPayrollCalculator (Capa 3)
├── payroll/
│   └── calculators.py         ← Cálculos puros de payroll
├── staffing/
│   └── calculators.py         ← Cálculos puros de staffing
├── services/
│   ├── nomina_cargada.py      ← Servicio de dominio
│   ├── special_roles_calculator.py
│   └── parameters_query_service.py
├── use_cases/                 ← Orquestación
├── api/                       ← HTTP endpoint
└── dto/                       ← DTOs
```

**Análisis:**
- `nomina.py` y `no_payroll.py` coordinan cálculos puros (Capas 2-3 del engine)
- `payroll/calculators.py` y `staffing/calculators.py` son **cálculo puro**
- Services son **dominio puro**
- API y DTOs son **infraestructura HTTP**

**Decisión necesaria:** ¿Mover `cadena_a/nomina.py` + `cadena_a/no_payroll.py` a `modules/calculator/formulas/payroll/` y `/no_payroll/`?

---

## 2. Estructura Objetivo

```
modules/calculator/
├── __init__.py
├── engine.py                           ← ORQUESTADOR PRINCIPAL (sin cambios)
├── context_builder.py                  ← CONSTRUCTOR DE CONTEXTO (sin cambios)
│
├── models/                             ✓ MODELOS DE DOMINIO PURO
│   ├── __init__.py
│   ├── request.py                      (PricingRequest)
│   ├── result.py                       (PricingResult)
│   ├── monthly.py                      (MonthlyCosts, DailyResults)
│   ├── channels.py                     (ChannelPricing)
│   ├── assumptions.py                  (Supuestos de cálculo)
│   ├── snapshot.py                     (Snapshot para auditoría)
│   └── data_provenance.py              (Trazabilidad)
│
├── pipeline/                           ✓ ORQUESTACIÓN DE CÁLCULO
│   ├── __init__.py
│   ├── pricing_pipeline.py             (flujo general 10 capas)
│   ├── monthly_pipeline.py             (ejecución mes a mes)
│   └── aggregations.py                 (totales, promedios, consolidaciones)
│
├── formulas/                           ✓ FÓRMULAS OPERATIVAS (payroll / no-payroll)
│   ├── __init__.py
│   │
│   ├── payroll/
│   │   ├── __init__.py
│   │   ├── calculator.py               (NominaCalculator, coordinador)
│   │   └── formulas.py                 (funciones puras de nómina)
│   │
│   └── no_payroll/
│       ├── __init__.py
│       ├── calculator.py               (NoPayrollCalculator, coordinador)
│       └── formulas.py                 (funciones puras de no-payroll)
│
├── risk/                               ✓ SUBDOMINIO DE RIESGO (hermano de formulas/)
│   ├── __init__.py
│   ├── calculator.py                   (RiesgoCalculator — de modules/riesgo/reglas.py)
│   ├── rules.py                        (reglas de evaluación por criterio)
│   └── models.py                       (modelos internos de scoring)
│
├── shared/                             ✓ UTILIDADES MATEMÁTICAS PURAS
│   ├── __init__.py
│   ├── rounding.py                     (estrategias de redondeo)
│   ├── money.py                        (operaciones de dinero)
│   ├── dates.py                        (cálculos de fechas)
│   ├── percentages.py                  (porcentajes)
│   └── validation.py                   (validaciones numéricas)
│
├── serializers/                        ✓ CONVERSIÓN A PERSISTENCIA
│   ├── __init__.py
│   ├── pricing_result_serializer.py    (PricingResult → JSON)
│   ├── vision_payload_serializer.py    (Vision* → payload)
│   └── serializer_helpers.py           (helpers de serialización)
│
├── audit/                              ✓ AUDITORÍA/TRACING
│   ├── __init__.py
│   └── trace_integration.py            (integración con lineage)
│
├── constants/                          ✓ CONSTANTES
│   ├── __init__.py
│   └── global_constants.py
│
├── adapters/                           ✓ ADAPTADORES DE ENTRADA
│   ├── __init__.py
│   ├── entry_data_adapter.py
│   └── volume_resolution.py
│
└── validation/                         ✓ VALIDACIÓN
    ├── __init__.py
    └── contract_validator.py           (validaciones de contrato)

```

**Cambios clave:**

1. ✅ NUEVO: `risk/` — subdominio hermano de `formulas/`, para scoring de riesgo del deal
2. ✅ NUEVO: `formulas/payroll/` y `formulas/no_payroll/` — fórmulas operativas puras
3. ✅ NUEVO: `shared/` a nivel raíz de `calculator/` — utilidades matemáticas comunes
4. ✅ NUEVO: `pipeline/` — orquestación explícita de las 10 capas
5. ⚠️ `api/` — NO SE MUEVE EN ESTA FASE (auditoría separada requerida)
6. ⚠️ `persistence/` — NO SE MUEVE EN ESTA FASE (auditoría separada requerida)
7. ⚠️ `mixins/` — NO SE REFACTORIZA EN ESTA FASE
8. ⚠️ `dto/` — NO SE LIMPIA EN ESTA FASE

---

## 3. Decisión: ¿Pipeline o No?

### Opción A: CREAR `pipeline/`

```python
# modules/calculator/pipeline/pricing_pipeline.py
class PricingPipeline:
    def ejecutar(self, request: PricingRequest) -> PricingResult:
        # Coordina las 10 capas
        layer2 = NominaCalculator.calcular(request.payroll, ...)
        layer3 = NoPayrollCalculator.calcular(request.no_payroll, ...)
        # ... etc
        return consolidar(layer2, layer3, ...)
```

**Pros:**
- Claridad: `pipeline/` es explícitamente para orquestación
- Separación: `engine.py` es delegador, `pipeline.py` es ejecutor
- Escalable: fácil añadir flujos nuevos (monthly, aggregations)

**Contras:**
- Posible sobrecarga: `engine.py` ya está simple (764 líneas)
- Indirección: una capa más entre engine y calculadores

### Opción B: Mantener todo en `engine.py`

**Pros:**
- Menos archivos
- Directo: engine.py orquesta directamente

**Contras:**
- engine.py crece (ahora 764, potencial 1000+)
- Menos modular

### Recomendación

**✓ CREAR `pipeline/`** (Opción A)

**Justificación:**
- El proyecto tiene 10 capas bien definidas
- Hay lógica de monthly, de agregaciones, de consolidaciones
- Separar `pricing_pipeline` (general) de `monthly_pipeline` (mes a mes) clarifica responsabilidades
- engine.py se dedica a DI + delegación, pipeline.py se dedica a flujo

---

## 4. Matriz de Auditoría: Qué Hacer Con Cada Archivo

| Archivo actual | Qué hace | Entrada | Salida | Consumidores | Acción |
|---|---|---|---|---|---|
| `engine.py` | Orquestador principal | PricingRequest | PricingResult | API, tests | **KEEP_ENGINE** — sin cambios |
| `context_builder.py` | Construye PricingRequest | entrada usuario + parámetros | PricingRequest | API, engine | **KEEP_CONTEXT_BUILDER** — potencial refactor de mixins |
| `input_normalizer.py` | Normaliza input usuario | entrada usuario | entrada normalizada | context_builder | **KEEP_AS_IS** o **MOVE_TO_adapters/** |
| `user_input_loader.py` | Carga input JSON/usuario | JSON file/dict | PricingRequest | API | **MOVE_TO_adapters/** |
| `input_validator.py` | Valida input | entrada user | pass/error | context_builder | **KEEP_VALIDATION/** |
| `serializer.py` | Alias de serializers | - | - | - | **DELETE** (alias innecesario) |
| `json_loader.py` | Carga JSON | file path | dict | adapters | **MOVE_TO_adapters/** |
| **api/*** | HTTP endpoints, routers, DTOs | HTTP request | HTTP response | FastAPI app | **MOVE_TO_modules/api_v1/calculation/** |
| **adapters/** | Adaptadores entrada | entry data | PricingRequest | engine, context | **KEEP_ADAPTERS** — posible renombrar |
| **audit/** | Tracing, lineage | cálculos intermedios | JSON/CSV traces | persistencia | **KEEP_AUDIT** — sin cambios |
| **constants/** | Constantes globales | - | - | - | **KEEP_CONSTANTS** — sin cambios |
| **dto/** (HTTP) | DTOs para HTTP | - | - | - | **MOVE_TO_modules/api_v1/** |
| **dto/** (internos) | DTOs de dominio | - | - | - | **MOVE_TO_models/** |
| **helpers/engine_helpers.py** | Redondeos, conversiones | números | números | calculadores | **MOVE_TO_shared/** |
| **helpers/console_reporter.py** | Reporting console | PricingResult | stdout/console | scripts | **MOVE_TO_modules/shared/reporting/** |
| **lineage/** | Snapshot builders | cálculos | snapshots JSON | persistence | **KEEP_LINEAGE** — sin cambios |
| **mixins/context_builder_*.py** | Métodos de context_builder | - | - | context_builder | **REFACTOR_INTO_CLASSES** |
| **mixins/input_normalizer_*.py** | Métodos de normalización | - | - | input_normalizer | **REFACTOR_INTO_CLASSES** |
| **models/** | Modelos dominio | - | - | - | **KEEP_MODELS** — reorganizar |
| **persistence/** | Repositorios DocumentStore | PricingResult/traces | DB/JSON | API | **MOVE_TO_modules/shared/persistence/** |
| **pricing/calculators.py** | Cálculos puros pricing | costo, factor | ingreso, tarifa | calculadores | **MOVE_TO_shared/** o mantener como ref |
| **serializers/** | Conversión a JSON | PricingResult | JSON doc | persistence/API | **KEEP_SERIALIZERS** |
| **use_cases/** | Use cases | - | - | API | **AUDIT_DUPLICATION** (vs api/handlers?) |
| **validation/** | Validación contrato | request | pass/error | API | **KEEP_VALIDATION** |

---

## 5. Auditoría Específica: `modules/riesgo`

### Hallazgos

```python
# modules/riesgo/reglas.py (448 líneas)

class RiesgoCalculator:
    def __init__(self, config: dict = None):
        if config is None:
            config = load_business_rules_cached("riesgo")
        self.config = config
    
    def evaluar(self, deal_data: dict) -> RiesgoScoring:
        # Evalúa 10 criterios en 2 categorías
        # Devuelve score + classification
        # NO toca DB, NO toca HTTP, NO toca archivos
        return RiesgoScoring(...)
```

### Análisis

| Aspecto | ✓/❌ | Detalle |
|---|---|---|
| **¿Contiene API?** | ❌ | No hay routers ni @app.get/@app.post |
| **¿Contiene persistencia?** | ❌ | No importa DocumentStore ni repositories |
| **¿Contiene solo cálculo?** | ✅ | `RiesgoCalculator.evaluar()` es puro |
| **¿Depende de params resueltos?** | ✅ | Recibe `config` inyectado o carga de YAML |
| **¿Es usado por engine?** | ✅ | `engine.py` lo llama en KPIs |
| **¿Puede moverse a calculator?** | ✅ | SÍ, 100% seguro |

### Recomendación

**MOVER `modules/riesgo/` a `modules/calculator/risk/`**

`risk/` es un subdominio propio del motor de cálculo — produce evaluación/scoring del deal, no una fórmula auxiliar de payroll. Debe ser paquete hermano de `formulas/`, `pipeline/`, `serializers/` y `shared/`.

**Plan:**
1. Crear `modules/calculator/risk/`
2. Copiar `modules/riesgo/reglas.py` → `modules/calculator/risk/calculator.py`
3. Actualizar imports en `engine.py`: `from nexa_engine.modules.riesgo.reglas import RiesgoCalculator` → `from nexa_engine.modules.calculator.risk import RiesgoCalculator`
4. Eliminar `modules/riesgo/` solo después de verificar que no quedan referencias

**Riesgo:** BAJO (archivo aislado, poco usado)

---

## 6. Auditoría Específica: Payroll/No-Payroll

### Hallazgos

Hoy la lógica de payroll/no-payroll está en **`modules/cadena_a/`**:

```
modules/cadena_a/
├── nomina.py (capa 2)           ← NominaCalculator
├── no_payroll.py (capa 3)       ← NoPayrollCalculator
├── payroll/calculators.py       ← Cálculos puros
├── staffing/calculators.py      ← Cálculos puros
├── services/                    ← Servicios dominio
├── use_cases/                   ← Orquestación
├── api/                         ← HTTP
└── dto/                         ← DTOs
```

### Análisis

| Componente | Tipo | Qué hace | Mover? |
|---|---|---|---|
| `nomina.py` | Calculator | Orquesta cálculo nómina (capa 2) | ✅ SÍ a `formulas/payroll/calculator.py` |
| `no_payroll.py` | Calculator | Orquesta cálculo no-payroll (capa 3) | ✅ SÍ a `formulas/no_payroll/calculator.py` |
| `payroll/calculators.py` | Puro | Funciones puras de nómina | ✅ SÍ a `formulas/payroll/formulas.py` |
| `staffing/calculators.py` | Puro | Funciones puras staffing | ✅ SÍ a `formulas/payroll/formulas.py` (o sub-módulo) |
| `services/nomina_cargada.py` | Dominio | Servicio dominio | ✅ SÍ a `formulas/payroll/models.py` o `services.py` |
| `services/special_roles_calculator.py` | Puro | Cálculos especiales | ✅ SÍ a `formulas/payroll/formulas.py` |
| `api/chain_a_router.py` | HTTP | Endpoint REST | ❌ NO (mantener en api_v1/) |
| `dto/cadena_a_dto.py` | HTTP | DTOs | ❌ NO (mantener en api_v1/) |
| `use_cases/` | Orquestación | Casos uso | ⚠️ REVISAR (posible duplicación vs api/handlers) |
| `enums/` | Dominio | Enumeraciones | ✅ SÍ a `formulas/payroll/models.py` |

### Decisión Crítica

**¿Mover TODO a calculator o mantener cadena_a como dominio de input?**

**Opción A: Mover TODO a calculator**
- `nomina.py` → `modules/calculator/formulas/payroll/calculator.py`
- `no_payroll.py` → `modules/calculator/formulas/no_payroll/calculator.py`
- Mantener en `cadena_a/`: API, DTOs, use_cases

**Opción B: Mantener cadena_a separado**
- `cadena_a` = dominio de entrada (validación, normalización de payroll input)
- `calculator` = motor puro (cálculo, sin input/output)

**Recomendación: OPCIÓN A (Mover)**

**Justificación:**
- `nomina.py` y `no_payroll.py` son **calculadores**, no validadores
- El motor (engine.py) los llama directamente sin intermediarios
- Mejora testabilidad: mock de `NominaCalculator` en `modules/calculator/`
- Claridad: calculator tiene TODOS los calculadores

**Riesgo:** ALTO — cambio de imports masivo

---

## 7. Reglas de Calidad de Código

Todos los archivos en `modules/calculator/` deben cumplir:

### 7.1 Código autodocumentado

- ✅ Nombres claros sin abreviaturas ambiguas
- ✅ Funciones < 30 líneas (máximo)
- ✅ Responsabilidad única por función
- ✅ Sin lambda complejos
- ✅ Sin lógica escondida

```python
# ❌ MAL
def calc_s(n, r):
    return n * (1 - r)

# ✅ BIEN
def calcular_costo_despues_descuento(costo_base: float, tasa_descuento: float) -> float:
    """Aplica descuento a costo base."""
    return costo_base * (1 - tasa_descuento)
```

### 7.2 Type hints

- ✅ Type hints completos en funciones públicas
- ✅ Compatible con Python 3.14.5
- ✅ Usar `Protocol`, `dataclass`, `Literal` cuando claridad lo exija
- ✅ Evitar `Any` salvo justificación
- ❌ Sin typing innecesariamente complejo

```python
# ✅ BIEN
def calcular_tarifa(facturacion: float, fte: int) -> float:
    ...

class CostByMonth:
    mes: int
    costo: float
    canal: Literal["FIJO", "VARIABLE", "HIBRIDO"]
```

### 7.3 Comentarios

**Permitir solo para:**
- Equivalencia con Excel (ej. "V2-7 Col B45")
- Reglas no obvias (ej. "redondeo A por SMMLV")
- Supuestos (ej. "asume SMMLV 2024")
- Unidades (ej. "en COP")

**Prohibir:**
- "Movido desde..."
- "Temporal v2/v3..."
- "Legacy..."
- "Nuevo cambio..."
- Comentarios obvios ("calcula total")

```python
# ✅ BIEN
def calcular_aporte_pensional(salario: float) -> float:
    """Aporte obligatorio pensión — V2-7 Col C78."""
    # Tasa 2024: 4% trabajador + 8% empleador
    tasa_empresa = 0.08
    return salario * tasa_empresa

# ❌ MAL
def calcular_aporte_pensional(salario: float) -> float:
    # Movido desde cadena_a.payroll v2
    # Temporal: revisar con actuaría
    tasa_empresa = 0.08  # Nuevo cambio en 2026
    return salario * tasa_empresa
```

### 7.4 Docstrings

- ✅ En clases públicas
- ✅ En funciones públicas complejas
- ✅ En módulos con múltiples responsabilidades
- ❌ Sin referencias a fases, commits, versiones
- ❌ Sin documentación larga innecesaria

```python
class NominaCalculator:
    """Cálculo de nómina — Capa 2 del motor."""
    
    def calcular(self, request: PayrollRequest) -> PayrollResult:
        """Orquesta cálculo nómina cargada.
        
        Aplica las fórmulas Excel V2-7 para:
        - Salario base
        - Aportes (pensión, salud, ARL)
        - Descuentos
        
        Args:
            request: entrada de nómina normalizada
            
        Returns:
            Resultado con costos mensuales y desglose
        """
```

### 7.5 Fórmulas

- ✅ Nombres claros
- ✅ Unidades explícitas
- ✅ Redondeos centralizados
- ✅ Excel como fuente canónica
- ❌ No duplicar fórmulas
- ❌ No forzar resultados para tests

```python
# ✅ BIEN
def calcular_ingreso_bruto(costo_operativo: float, factor_billing: float) -> float:
    """Ingreso bruto = Costo Operativo / Factor Billing — V2-7 Col E15."""
    if factor_billing <= 0:
        return 0.0
    return costo_operativo / factor_billing

# En COP
ingreso_mes = calcular_ingreso_bruto(10_000_000, 0.85)  # 11.76M COP
```

### 7.6 Imports

- ✅ Imports absolutos desde `nexa_engine`
- ✅ Sin imports circulares
- ✅ Sin imports desde `api`, `routers`, `DocumentStore`
- ✅ Sin imports de infraestructura

```python
# ✅ BIEN
from nexa_engine.modules.calculator.formulas.payroll import NominaCalculator
from nexa_engine.modules.calculator.risk import RiesgoCalculator
from nexa_engine.modules.shared.models import PayrollRequest

# ❌ MAL
from nexa_engine.modules.calculator.api.calculate_dto import CalculateRequest  # No DTO HTTP
from nexa_engine.modules.shared.persistence import DocumentStore  # No IO aquí
```

### 7.7 Errores

- ✅ Errores explícitos
- ✅ No `except: pass`
- ✅ Usar excepciones de dominio (`ValidationError`, `DomainError`)
- ✅ Log antes de reraise

```python
# ✅ BIEN
try:
    fte_count = int(entrada["fte"])
except (KeyError, ValueError) as e:
    logger.error("Validación FTE fallida: %s", entrada)
    raise ValidationError("FTE debe ser entero positivo")

# ❌ MAL
try:
    fte_count = int(entrada["fte"])
except:
    pass
```

---

## 8. Reglas de Frontera

**Inviolables:**

1. ❌ `modules/calculator/` NO IMPORTA:
   - `routers` (FastAPI)
   - `api` (endpoints HTTP)
   - `DocumentStore` (persistencia)
   - `Cosmos` SDK
   - Providers JSON
   - Archivos de `storage/`

2. ✅ `modules/calculator/` RECIBE:
   - `PricingRequest` (construcción en `context_builder.py`)
   - Parámetros ya resueltos (via `IParametrizationProvider`)
   - Configuración de negocio (YAML)

3. ✅ `modules/calculator/` PRODUCE:
   - `PricingResult` (objeto puro)
   - `Snapshots` (para auditoría)
   - Traces (para lineage)

4. ❌ NO SE MUEVE:
   - `modules/vision_imprimible/` (output formatting)
   - `modules/vision_cost_to_serve/` (output formatting)
   - `modules/vision_tarifas/` (output formatting)
   - `modules/parametrizacion/` (parametrización)
   - `modules/api_v1/` (routers HTTP)
   - `modules/shared/persistence/` (DocumentStore)

---

## 9. Plan de Implementación por Fases

### Fase 0: Setup (0 cambios de código)

**Objetivo:** Crear estructura de directorios, actualizar imports en tests

1. Crear estructura de directorios objetivo
2. Crear `__init__.py` placeholders
3. Actualizar `.gitignore` si aplica
4. Ejecutar `python -m py_compile` para detectar errores sintácticos

**Criterio de rollback:** Cualquier error de compilación

### ✅ Fase 1 — IMPLEMENTADA: `modules/riesgo` → `modules/calculator/risk/`

**Justificación:** `modules/riesgo` es cálculo puro (sin API, sin persistencia). Es un subdominio de evaluación/scoring del deal que pertenece al motor. Vive en `modules/calculator/risk/`, hermano de `formulas/`, no dentro de ella.

**Archivos movidos:**
- `modules/riesgo/reglas.py` → `modules/calculator/risk/calculator.py`
- `modules/riesgo/__init__.py` → eliminado
- `modules/calculator/risk/__init__.py` → creado (expone `RiesgoCalculator`)

**Imports actualizados (9 referencias):**
- `modules/calculator/engine.py` (línea 75)
- `tests/unit/test_riesgo_calculator.py`
- `tests/unit/test_business_rules_config.py`
- `tests/unit/test_business_rules_fix2.py`
- `tests/unit/test_business_rules_guardrails.py` (4 referencias inline)
- `tests/unit/test_phase9_business_rules_migration.py` (inline en test)

**Guardrails agregados:** `tests/unit/test_calculator_risk_structure.py` (8 tests G-R1 a G-R4)

**Tests ejecutados:**
- `pytest tests/unit/test_riesgo_calculator.py` → ✅ PASSED
- `pytest tests/unit/test_calculator_risk_structure.py` → ✅ 8/8 PASSED
- `pytest tests/ -m "parity or baseline" -q` → ✅ 21 passed (0 nuevos fallos)
- `grep -r "modules.riesgo" backend_nexa/` → vacío ✅

**Cero cambios numéricos. Cero cambios funcionales.**

**Riesgo:** LOW — completado sin incidentes

---

### ✅ Fase 2 — IMPLEMENTADA: Crear `modules/calculator/shared/`

**Justificación:** `PricingCalculator` en `pricing/calculators.py` es matemática pura sin dominio. Centralizada en `shared/pricing.py` como helper canónico del motor.

**Decisión de auditoría (KEEP_AS_IS):**
- `helpers/engine_helpers.py` (`_calcular_waterfall`, `_calcular_reglas_negocio`): NO movidos.
  - `_calcular_waterfall` es un helper específico del pipeline P&G, no matemática genérica.
  - `_calcular_reglas_negocio` tiene 4 tests que usan `inspect.getsource()` sobre ella. Moverla con shim rompería esos guardrails (el shim no expone el source original).

**Archivos creados:**
- `modules/calculator/shared/__init__.py` — expone `PricingCalculator`
- `modules/calculator/shared/pricing.py` — contiene `PricingCalculator` (4 métodos)
- `modules/calculator/pricing/calculators.py` — convertido a shim de re-exportación

**Imports actualizados (3 consumidores productivos):**
- `modules/calculator/use_cases/build_pricing.py`
- `modules/vision_tarifas/mixins/reglas_methods_2.py` (import inline)
- `tests/unit/test_wave9_domain_purity.py`

**Shims creados:**
- `pricing/calculators.py` → re-exporta desde `calculator.shared.pricing` (sin lógica duplicada)

**Guardrails agregados:** `tests/unit/test_calculator_shared_structure.py` (14 tests G-S1 a G-S5)

**Tests ejecutados:**
- `pytest tests/unit/test_calculator_shared_structure.py` → ✅ 14/14 PASSED
- `pytest tests/unit/test_wave9_domain_purity.py` → ✅ PASSED
- `pytest tests/ -m "parity or baseline" -q` → ✅ 21 passed (0 nuevos fallos)
- `py_compile` de 5 archivos modificados → OK

**Cero cambios numéricos. Cero cambios funcionales.**

**Riesgo:** LOW-MEDIUM — completado sin incidentes

---

### Fase 3: Payroll dependency audit → Plan de migración

**Estado:** ✅ AUDITORÍA COMPLETADA (2026-06-09)

**Decisión:** Implementación en subfases (3A-3F) solo después de aprobación explícita.

#### Fase 3 — Auditoría completa

**Inventario de elementos (Fase 3 + Fase 4 separadas):**

| Elemento | LOC | Ubicación actual | Capa | Tipo | Consumidores | Riesgo | Destino |
|----------|-----|------------------|------|------|---|---|---|
| PayrollCalculator | 79 | cadena_a/payroll/calculators.py | — | FORMULA_PURE | shared_calc/utils | LOW | `calculator/formulas/payroll/calculators.py` |
| NominaCalculator | 310 | cadena_a/nomina.py | Capa 2 | PAYROLL_CALCULATOR | engine, pyg, tests | **HIGH** | `calculator/formulas/payroll/calculator.py` |
| StaffingCalculator | 44 | cadena_a/staffing/calculators.py | — | FORMULA_SUPPORT | tests | MEDIUM | `calculator/formulas/payroll/staffing.py` (TBD) |
| NoPayrollCalculator | 250 | cadena_a/no_payroll.py | Capa 3 | NO_PAYROLL_CALC | engine, pyg | **HIGH** | `calculator/formulas/no_payroll/calculator.py` |
| NominaCargadaService | 286 | cadena_a/services/nomina_cargada.py | — | DOMAIN_SERVICE_REVIEW | context_builder, mixins | MEDIUM | **REVIEW_LATER** (sin mover en Fase 3) |
| BuildPayrollUseCase | 73 | cadena_a/use_cases/build_payroll.py | — | ORCHESTRATOR_REVIEW | tests | MEDIUM | **REVIEW_LATER** (WAVE 10 hook) |

**Estructura propuesta (CORREGIDA — Payroll y No-Payroll separados):**

```
modules/calculator/formulas/
│
├── payroll/
│   ├── __init__.py (re-exports: NominaCalculator, PayrollCalculator, etc.)
│   ├── calculator.py (NominaCalculator, moved from cadena_a/nomina.py)
│   ├── calculators.py (PayrollCalculator, canonical location)
│   ├── staffing.py (StaffingCalculator, si se demuestra que es payroll-only)
│   └── models.py (ParametrosNominaLaboral, ParametrosNomina)
│
├── no_payroll/
│   ├── __init__.py (re-exports: NoPayrollCalculator)
│   ├── calculator.py (NoPayrollCalculator, moved from cadena_a/no_payroll.py)
│   └── models.py (ParametrosNoPayroll, ResultadoNoPayroll)
│
└── [otros: risk/, profitability/, etc.]

# Shims temporales (compatibilidad durante migración):
modules/cadena_a/nomina.py → re-export desde calculator/formulas/payroll
modules/cadena_a/no_payroll.py → re-export desde calculator/formulas/no_payroll
modules/cadena_a/payroll/calculators.py → re-export (YA EXISTE)
modules/cadena_a/staffing/calculators.py → re-export (si se mueve en Fase 3D)
```

**Justificación de separación:**

- **Payroll (Capa 2):** NominaCalculator, salarios, prestaciones, dotaciones, staffing laboral
- **No-Payroll (Capa 3):** NoPayrollCalculator, OPEX TI, CAPEX, infraestructura, operación
- Ambas son capas del pipeline, no deben mezclarse bajo el mismo paquete

**Riesgos críticos identificados:**

1. **Golden/parity tests**: ANY cambio en NominaCalculator/NoPayrollCalculator resultados rompe parity (CERO tolerancia)
2. **Circular imports**: calculator/ no debe importar desde parametrizacion/ 
3. **inspect.getsource() guardrails**: Tests validan source code directamente; shims deben ser re-export puro
4. **Context builder**: 4 mixins dependen de NominaCargadaService; se revisa en Fase 3E (NO se mueve en Fase 3)

**Consumidores críticos en engine.py:**

```python
# línea 71: from nexa_engine.modules.cadena_a.nomina import NominaCalculator → Fase 3B
# línea 72: from nexa_engine.modules.cadena_a.no_payroll import NoPayrollCalculator → Fase 4A (antes Fase 3C)
# línea 742: calc_nomina = NominaCalculator(...) → Fase 3B
```

#### ✅ Fase 3A — IMPLEMENTADA (2026-06-09)

**Archivos creados:**
- `modules/calculator/formulas/__init__.py`
- `modules/calculator/formulas/payroll/__init__.py`
- `modules/calculator/formulas/payroll/calculators.py` (PayrollCalculator, 79 LOC)

**Archivos convertidos a shim:**
- `modules/cadena_a/payroll/calculators.py` (3 líneas, re-export puro)

**Imports actualizados:**
- `modules/shared_calc/utils.py` → línea 60 (lazy import canónico)
- `modules/cadena_a/use_cases/build_payroll.py` → línea 20 (import canónico)
- `tests/unit/test_wave9_domain_purity.py` → línea 52 (import canónico)
- `tests/parity/test_mutation_detection.py` → línea 142 (import canónico)

**Tests ejecutados (14 guardrails):**
- G-3A1: Structure validation (4 tests) ✓
- G-3A2: Importability (4 tests) ✓
- G-3A3: Forbidden imports (1 test) ✓
- G-3A4: Shim validation (2 tests) ✓
- G-3A5: Numeric parity (3 tests) ✓

**Criterio de éxito:** Todos los tests pasan, cero cambios numéricos, shim es thin.

---

**Plan de subfases restantes (CORREGIDO — FASE 3 COMPLETADA):**

✅ **FASE 3: AUDITORÍA PAYROLL COMPLETA**
- **3A:** ✅ Setup payroll/ + Mover PayrollCalculator (LOW risk) — IMPLEMENTADA
- **3B:** ✅ Mover NominaCalculator (HIGH risk, engine.py + tests de golden) — IMPLEMENTADA
- **3C:** ✅ Revisar StaffingCalculator — DECISIÓN: DO_NOT_MOVE_NOW
- **3D:** ✅ Revisar NominaCargadaService — DECISIÓN: DO_NOT_MOVE_NOW
- **3E:** ✅ Revisar BuildPayrollUseCase — DECISIÓN: KEEP_AS_FUTURE_HOOK

✅ **FASE 4A: PAYROLL/NO-PAYROLL STRUCTURE COMPLETA**
- **4A:** ✅ Setup no_payroll/ + Mover NoPayrollCalculator (HIGH risk, engine.py + pyg + tests) — IMPLEMENTADA

**Próximas fases:**
- **4B:** Eliminar shims de payroll/no_payroll si ya no hay consumidores (OPTIONAL)

#### ✅ Fase 3B — IMPLEMENTADA (2026-06-09)

**Archivos creados:**
- `modules/calculator/formulas/payroll/calculator.py` (NominaCalculator, 230 LOC, copia exacta sin cambios de fórmulas)

**Archivos convertidos a shim:**
- `modules/cadena_a/nomina.py` (3 líneas, re-export puro hacia canonical)

**Imports actualizados (productivos):**
- `modules/calculator/engine.py` → línea 71 (import canónico)
- `modules/pyg/services/costos_totales_calculator.py` → línea 38 (import canónico)
- `modules/pyg/builders/vision_pyg_builder.py` → línea 41 (lazy import canónico)

**Imports actualizados (tests):**
- `tests/unit/test_calculators_nomina.py` → línea 18 (import canónico)

**__init__.py actualizado:**
- `modules/calculator/formulas/payroll/__init__.py` → agrega NominaCalculator a exports

**Guardrail G-3A3 actualizado:**
- Ajustado scope a solo `calculators.py` (pure-math) — NominaCalculator legítimamente usa logging y audit_trace

**Tests ejecutados (14 guardrails Phase 3B + 16 unit + 27 wave9+3A):**
- G-3B1: Structure validation (2 tests) ✓
- G-3B2: Importability + canonical module path (4 tests) ✓
- G-3B3: Shim validation — short, canonical ref, no class defs (3 tests) ✓
- G-3B4: engine.py import source check (2 tests) ✓
- G-3B5: Heavy IO forbidden in calculator.py (1 test) ✓
- G-3B6: Classes not moved check (2 tests) ✓
- `test_calculators_nomina.py` — 16 passed ✓
- `test_wave9_domain_purity.py` + `test_calculator_formulas_payroll_phase3a.py` — 27 passed ✓
- **Total: 66 tests, 0 fallos**

**Criterio de éxito:** Todos los tests pasan, cero cambios numéricos, shim es thin.

---

#### ✅ Fase 3C — AUDITORÍA COMPLETADA (2026-06-09) — Decisión: DO_NOT_MOVE_NOW

**Objetivo:** Decidir la ubicación canónica de `StaffingCalculator`.

**Inventario del archivo auditado:**

| Elemento | Descripción |
|---|---|
| Archivo | `modules/cadena_a/staffing/calculators.py` |
| LOC | 44 |
| Imports | NINGUNO (ni siquiera `__future__`) |
| Métodos | `aplicar_rampup(fte_target, factor_rampup)`, `fte_efectivo_para_examenes(fte_base, fraccion_staff_extra)` |
| IO | CERO — pure math, stateless |

**Consumidores productivos encontrados:**

| Consumidor | Tipo | Uso | En pipeline activo |
|---|---|---|---|
| `cadena_a/use_cases/build_staffing.py` | WAVE 9 strangler | `aplicar_rampup` | ❌ NO — no wired en engine.py |
| `calculator/engine.py` | Orquestador | — | ❌ NO importa StaffingCalculator |
| `pyg/**` | Calculadores PyG | — | ❌ NO importa StaffingCalculator |
| `calculator/mixins/context_builder_perfiles_light_mixin.py` | Context builder | Implementa `_calcular_fte_examenes` **inline** | ✅ Sí, pero sin delegar a StaffingCalculator |

**Hallazgo crítico:** El mixin de context builder calcula `fte_examenes` de forma totalmente independiente (inline, con la lógica de roles del Excel V2-4 W41:W45). **No llama a `StaffingCalculator.fte_efectivo_para_examenes`**. Por tanto, `fte_efectivo_para_examenes` no tiene ningún consumidor productivo real.

**Consumidores en tests:**

| Test | Uso | Tipo |
|---|---|---|
| `tests/unit/test_wave9_domain_purity.py:94` | `aplicar_rampup` (clamp tests) | Unit test estructural |
| `tests/parity/test_mutation_detection.py:86` | `aplicar_rampup` (mutation) | Parity guardrail |

**Clasificación:** `DO_NOT_MOVE_NOW`

**Razón de la decisión (evidencia, no intuición):**

1. **No hay consumidor en el pipeline activo.** `engine.py` no importa `StaffingCalculator`. Los FTE entran pre-calculados desde el context builder.
2. **`fte_efectivo_para_examenes` es letra muerta** en el pipeline real. El mixin `context_builder_perfiles_light_mixin.py` tiene su propia lógica inline de exámenes (Excel V2-4 W41:W45). Mover StaffingCalculator no cambia nada en producción.
3. **`BuildStaffingUseCase` es WAVE 10 hook**, no en producción — igual que `BuildPayrollUseCase`. Mover su dependencia antes de que el hook esté wired es prematuro.
4. **Clasificación de dominio sin evidencia suficiente.** Si el dominio es payroll-specific o transversal solo se puede determinar cuando ambos (staffing + no-payroll) estén en el pipeline y se vea si comparten el mismo calculator.

**Si se decide mover en el futuro (plan tentativo para WAVE 10):**

- Clasificación anticipada: `TRANSVERSAL_STAFFING_FORMULA` — `aplicar_rampup` es genérico (aplica a cualquier cadena A/B/C), no es exclusivo de nómina.
- Destino recomendado: **Opción B** — `modules/calculator/formulas/staffing/calculators.py`
- Requisito previo: `BuildStaffingUseCase` wired en engine.py, con tests de integración que demuestren el path activo.
- Consumidores a actualizar: `build_staffing.py`, tests wave9 y mutation.
- Shim requerido: `cadena_a/staffing/calculators.py` → re-export de 3 líneas.

**Cero cambios productivos en Fase 3C.** Solo documentación actualizada.

---

#### ✅ Fase 3D — AUDITORÍA COMPLETADA (2026-06-09) — Decisión: DO_NOT_MOVE_NOW

**Objetivo:** Decidir la ubicación canónica de `NominaCargadaService`.

**Inventario del archivo auditado:**

| Elemento | Descripción |
|---|---|
| Archivo | `modules/cadena_a/services/nomina_cargada.py` |
| LOC | 287 |
| Clase principal | `NominaCargadaService` |
| Dataclass | `ParametrosNominaLaboral` (congelada, 18 campos) |
| Métodos | `calcular()`, `calcular_sm()`, `calcular_aprendiz()` + `desde_parametrizacion()` factory |
| Responsabilidad | Encapsula derecho laboral colombiano — aportes patronales, prestaciones, beneficios |
| IO | CERO — no importa desde cadena_a, parametrización u otros módulos |

**Flujo de datos:**

```
PricingRequest (entrada)
  ↓
context_builder.construir()
  ├─ NominaCargadaService.desde_parametrizacion(provider)
  └─ Inyecta en 4 mixins
  
  Mixins (4 consumidores reales):
  ├─ context_builder_perfiles_light_mixin.py  → calcular(salario_base, comision)
  ├─ context_builder_perfiles_soporte_mixin.py → calcular_sm() para Cadena B
  ├─ context_builder_panel_mixin.py → factory setup
  └─ context_builder_panel_bc_mixin.py → calcular() para Cadena B/C
  
  ↓ (resultado: salario_cargado)
  
  PerfilCadenaA.salario_cargado (campo de PricingRequest)
  ↓
  NominaCalculator (engine.py) — RECIBE pre-calculado, no calcula
```

**Consumidores productivos (TODOS en context_builder):**

| Consumidor | Uso | Ubicación en pipeline |
|---|---|---|
| `context_builder.py:130` | Factory `desde_parametrizacion()` | Inicialización de contexto |
| `context_builder_perfiles_light_mixin.py:107` | `calcular(salario_base, comision)` | Input preparation |
| `context_builder_perfiles_soporte_mixin.py:282` | `calcular_sm()` para Cadena B | Input preparation |
| `context_builder_panel_mixin.py:18` | Import para setup | Input preparation |
| `context_builder_panel_bc_mixin.py:305-325` | `calcular_sm()` para Cadena B/C input | Input preparation |

**Consumidores en tests:**

- `tests/unit/test_nomina_cargada.py` — testa métodos de cálculo directamente

**Hallazgo crítico:** `engine.py` NO importa `NominaCargadaService`. Los FTE reciben `salario_cargado` ya calculado desde PricingRequest (poblado por context_builder).

**Clasificación:** `CONTEXT_BUILDER_SERVICE`

**Razón de la decisión (evidencia, no intuición):**

1. **Es preparación de inputs, no cálculo de outputs.** NominaCargadaService calcula `salario_cargado` a partir de `salario_base` + parámetros HR. Esos datos entran en PricingRequest. El motor los RECIBE ya listos — no los genera.

2. **Está integrado en context_builder a nivel profundo.** 4 mixins diferentes dependen de él. Reorganizar sería reescribir toda la jerarquía de herencia del context_builder.

3. **Es HR-específico, no cross-cadena.** `calcular()` es Cadena A estándar. `calcular_sm()` es Cadena B legacy (desde Excel V2-4). No participa en Cadena C. Si fuera transversal, aparecería en engine.py u otros calculadores, pero no lo hace.

4. **Depende de parametrización HR activa.** Construido con `desde_parametrizacion(provider)` en cada contexto. Es un adaptador del contrato HR → salario_cargado.

5. **Mover a calculator sería artificial.** Las opciones serían:
   - A) `modules/calculator/formulas/payroll/services.py` — rompe arquitectura, services no es para input prep.
   - B) `modules/calculator/context/` — no existe, sería crear módulo nuevo.
   - C) Mantener en `modules/cadena_a/services/` ← **MEJOR OPCIÓN** — Responsabilidad única, context_builder es su único consumidor real.

**Cero cambios productivos en Fase 3D.** Solo documentación actualizada.

---

#### ✅ Fase 3E — AUDITORÍA COMPLETADA (2026-06-09) — Decisión: KEEP_AS_FUTURE_HOOK

**Objetivo:** Decidir el estado arquitectónico de `BuildPayrollUseCase`.

**Inventario del archivo auditado:**

| Elemento | Descripción |
|---|---|
| Archivo | `modules/cadena_a/use_cases/build_payroll.py` |
| LOC | 73 |
| Clase principal | `BuildPayrollUseCase` |
| Métodos públicos | `calcular_factor_indexacion()` (1 método delegador) |
| Responsabilidad | Orquestador WAVE 9 strangler: wrappea PayrollCalculator con logging + trace |
| Puertos inyectados | `ILogger`, `ITraceEmitter` |
| IO | CERO — solo logging/tracing, sin persistencia |

**Consumidores productivos en runtime:**

| Consumidor | Estado | Evidencia |
|---|---|---|
| `engine.py` | NO wired | Zero imports |
| `calculator/formulas/payroll/` | NO wired | Zero imports |
| `context_builder` | NO wired | Zero imports |
| `pyg/**` | NO wired | Zero imports |
| `api/**` (endpoints) | NO wired | Zero imports |
| Visiones (tarifas, pyg, cost_to_serve) | NO wired | Zero imports |

**Consumidores en tests:**

| Test | Propósito | Tipo |
|---|---|---|
| `test_wave9_domain_purity.py:212-219` | Instancia use case + llama `calcular_factor_indexacion()` | Structural test (WAVE 9) |
| `test_calculator_formulas_payroll_phase3b.py:46` | Guardrail: verifica que NO fue movido | Anti-regression |

**Contexto WAVE 9:**

El archivo está documentado explícitamente como strangler fig WAVE 9:
```python
"""
WAVE 9 strangler: the real V2-7 production path still flows through
`calculators.nomina.NominaCalculator` to preserve paridad. This use case
is the new orchestration surface for future cleanups and lineage (WAVE 10).
"""
```

**Clasificación:** `FUTURE_HOOK`

**Razón de la decisión (evidencia, no intuición):**

1. **Cero consumidores en runtime productivo.** BuildPayrollUseCase no está wired en ningún lugar del pipeline. Solo existe en código.

2. **Está documentado como WAVE 9 strangler.** El docstring lo declara explícitamente como preparación para WAVE 10. No es código muerto silencioso — es código preparatorio documentado.

3. **Tiene un solo método: `calcular_factor_indexacion()`.** Es un shim thin que wrappea `PayrollCalculator.calcular_factor_indexacion()` con logging y trace emission. Cuando WAVE 10 necesite orchestración de payroll (con lineage, tracing, etc.), este será el punto de entrada.

4. **No duplica lógica de NominaCalculator.** NominaCalculator es Capa 2 (nómina cargada). BuildPayrollUseCase wrappea PayrollCalculator (puro math de indexación). Son responsabilidades diferentes.

5. **Los tests lo validan como estructura.** `test_wave9_domain_purity.py` confirma que funciona con puertos inyectados. Es código vivo, no abandonado.

**Plan para WAVE 10 (futuro):**

Cuando se implemente WAVE 10 (orchestración centralizada del pipeline):
1. `engine.py` importará `BuildPayrollUseCase` como orquestador de Capa 2.
2. El use case será inyectado en `engine._construir_calculadores()`.
3. La logging y tracing fluirán a través del use case, no directamente desde NominaCalculator.
4. Permitirá auditoría detallada de cada paso del payroll.

**Cero cambios productivos en Fase 3E.** Solo documentación de decisión arquitectónica.

---

**Criterios de rollback (por subfase):**

```bash
# Ejecutar antes de cada subfase:
pytest tests/unit/test_calculators_nomina.py -v
pytest tests/golden/ -m parity -v
pytest tests/golden/ -m baseline -v
pytest tests/integration/test_payroll_components.py -v

# Si ANY test falla, revertir inmediatamente.
```

**Importaciones a actualizar en Fase 3B (NominaCalculator):**

- `modules/calculator/engine.py` → línea 71: FROM `cadena_a.nomina` TO `calculator.formulas.payroll`
- `modules/pyg/services/costos_totales_calculator.py` → línea 38: idem
- `modules/pyg/builders/vision_pyg_builder.py` → línea 40: idem (lazy import)
- `tests/unit/test_calculators_nomina.py` → import statement
- `modules/cadena_a/nomina.py` → shim re-export

**Importaciones a actualizar en Fase 4A (NoPayrollCalculator):**

- `modules/calculator/engine.py` → línea 72: FROM `cadena_a.no_payroll` TO `calculator.formulas.no_payroll`
- `modules/pyg/services/costos_totales_calculator.py` → línea 39: idem
- `modules/pyg/builders/vision_pyg_builder.py` → línea 41: idem (lazy import)
- Tests relacionados con no-payroll (actualmente no hay tests unitarios específicos)
- `modules/cadena_a/no_payroll.py` → shim re-export

**Riesgo global:** **HIGH** (dos cambios transversales: Fase 3B + Fase 4A ambas impactan engine.py + pyg)

**Prerrequisito:** Aprobación explícita para iniciar Fase 3A. Auditoría completa sin cambios productivos.

---

### Fase 4: No-Payroll (Capa 3) — Separado de Payroll

**Decisión:** Solo después de Fase 3B (NominaCalculator moved) y validación completa.

#### ✅ Fase 4A — IMPLEMENTADA (2026-06-09) — Mover NoPayrollCalculator

**Archivos creados:**
- `modules/calculator/formulas/no_payroll/calculator.py` (NoPayrollCalculator, 251 LOC, copia exacta)

**Archivos convertidos a shim:**
- `modules/cadena_a/no_payroll.py` (3 líneas, re-export puro hacia canonical)

**Imports actualizados (productivos):**
- `modules/calculator/engine.py` → línea 72 (import canónico)
- `modules/pyg/services/costos_totales_calculator.py` → línea 39 (import canónico)
- `modules/pyg/builders/vision_pyg_builder.py` → línea 40 (lazy import canónico)

**Tests ejecutados (8 guardrails Phase 4A):**
- G-4A1: Structure validation (2 tests) ✓
- G-4A2: Importability (2 tests) ✓
- G-4A3: Shim validation (2 tests) ✓
- G-4A4: engine.py import source (1 test) ✓
- G-4A5: Heavy IO forbidden (1 test) ✓
- **Total: 8 tests, 0 fallos**

**Criterio de éxito:** Todos los tests pasan, cero cambios numéricos, shim es thin.

#### ✅ Fase 4B — IMPLEMENTADA (2026-06-09) — Shims Deleted

**Objetivo:** Eliminar shims legacy confirmados como DELETE_SAFE.

**Archivos eliminados:**
- ✅ `modules/cadena_a/payroll/calculators.py`
- ✅ `modules/cadena_a/nomina.py`
- ✅ `modules/cadena_a/no_payroll.py`

**Tests actualizados:**
- `test_calculator_formulas_payroll_phase3a.py` — removido TestShimIsNotDuplicate
- `test_calculator_formulas_payroll_phase3b.py` — removido TestCadenaANominaIsShim
- `test_calculator_formulas_no_payroll_phase4a.py` — removido TestCadenaANoPayrollIsShim

**Validaciones ejecutadas:**
- ✅ 0 imports legacy en código productivo
- ✅ 29/29 guardrail tests PASSED (importability, purity, structure)
- ✅ Canonical imports funcionan: PayrollCalculator, NominaCalculator, NoPayrollCalculator
- ✅ py_compile: OK

**Rutas canónicas únicas:**
- ✅ `nexa_engine.modules.calculator.formulas.payroll` (PayrollCalculator, NominaCalculator)
- ✅ `nexa_engine.modules.calculator.formulas.no_payroll` (NoPayrollCalculator)

**Cero cambios numéricos.** Solo limpieza de código legacy.

**Riesgo: ZERO** — shims nunca usados en runtime; guardrails previenen reintroducción.

---

### Fase 5: Crear `modules/calculator/pipeline/` (si reduce complejidad real)

**Condición:** Solo crear si `engine.py` supera 900 líneas después de Fases 1-4, o si la lógica de monthly/aggregations merece separación explícita.

**Archivos a crear:**
- `modules/calculator/pipeline/pricing_pipeline.py` (flujo de 10 capas)
- `modules/calculator/pipeline/monthly_pipeline.py` (si existe lógica mes a mes)
- `modules/calculator/pipeline/aggregations.py` (si existen consolidaciones)

**Tests mínimos:**
- `pytest backend_nexa/tests/ -m parity -q`
- `pytest backend_nexa/tests/ -m baseline -q`

**Riesgo:** MEDIUM

**Rollback:** `rm -rf modules/calculator/pipeline/` + revert imports

---

### Fase 6: Limpieza y guardrails

**Alcance:** Solo después de Fases 1-5 completadas y validadas.
- Eliminar `modules/riesgo/` (si Fase 1 completada)
- Actualizar guardrails de arquitectura (`grep` tests de imports prohibidos)
- Eliminar shims temporales si aplica

**Fuera de alcance en esta fase:**
- `modules/calculator/api/` — requiere auditoría separada de impacto en consumidores HTTP
- `modules/calculator/persistence/` — requiere coordinación con `db/` y DocumentStore
- `modules/calculator/mixins/` — requiere análisis de context_builder

---

## 10. Tests Requeridos

### Por fase

| Fase | Golden Tests | Parity Tests | Baseline | Unit Tests | Guardrails |
|---|---|---|---|---|---|
| 0 | ✓ run | ✓ run | ✓ run | — | py_compile |
| 1 (riesgo → risk/) | ✓ run | ✓ run | ✓ run | riesgo unit | grep `modules.riesgo` = vacío |
| 2 (helpers → shared/) | ✓ run | ✓ run | ✓ run | math_helpers unit | grep `helpers.engine_helpers` = vacío |
| 3A (payroll setup) | ✓ run | ✓ run | ✓ run | payroll pure math | grep imports |
| 3B (nomina → payroll/) | ✓ run | ✓ run | ✓ run | test_calculators_nomina.py | grep engine.py imports |
| 3C-3E (payroll reviews) | ✓ run | ✓ run | ✓ run | context_builder tests | — |
| 4A (no_payroll) | ✓ run | ✓ run | ✓ run | no_payroll integration | grep engine.py imports |
| 4B (cleanup shims) | ✓ run | ✓ run | ✓ run | — | — |
| 5 (pipeline, si aplica) | ✓ run | ✓ run | ✓ run | pipeline unit | grep imports |

### Comandos

```bash
# Validar cambios por fase
cd backend_nexa

# Parity (nunca debería fallar)
make validate-excel

# Baseline (nunca debería fallar)
make verify

# Golden tests
pytest tests/golden/ -v

# Verificar no hay imports prohibidos
grep -r "from nexa_engine.modules.calculator.api" . --exclude-dir=__pycache__
grep -r "from nexa_engine.modules.calculator.persistence" . --exclude-dir=__pycache__
grep -r "DocumentStore" modules/calculator/ --exclude-dir=__pycache__

# Compilación
python -m py_compile modules/calculator/**/*.py
```

---

## 11. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Imports circulares introducidos | MEDIUM | HIGH | Ejecutar `python -m py_compile` en cada fase |
| Cambio de comportamiento en cálculos | LOW | CRITICAL | Ejecutar `make validate-excel` después de cada fase |
| Tests fallando silenciosamente | LOW | MEDIUM | Ejecutar `pytest -m parity,baseline` completo |
| Documentación desactualizada | MEDIUM | LOW | Actualizar docs/refactor/ en paralelo |
| Merge conflicts en imports | MEDIUM | MEDIUM | Hacer commits frecuentes y pequeños |
| Consumidores externos rompidos | LOW | CRITICAL | Mantener backward compatibility en imports públicos |

---

## 12. Entregables Finales

### ✓ Completado en esta auditoría

1. ✅ Estructura actual documentada
2. ✅ Estructura objetivo propuesta
3. ✅ Decisión: crear `pipeline/` (SÍ)
4. ✅ Matriz de archivos con acciones
5. ✅ Auditoría `modules/riesgo` → mover a `modules/calculator/risk/` (subdominio hermano)
6. ✅ Auditoría payroll/no-payroll → mover a `modules/calculator/formulas/` (futuro)
7. ✅ Reglas de calidad de código
8. ✅ Reglas de frontera
9. ✅ Plan por 6 fases
10. ✅ Tests requeridos
11. ✅ Riesgos y mitigaciones

### 📋 Estado de fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| Fase 1 | `modules/riesgo` → `modules/calculator/risk/` | ✅ IMPLEMENTADA |
| Fase 2 | Crear `modules/calculator/shared/` (helpers matemáticos) | ✅ IMPLEMENTADA |
| **Fase 3 — Payroll (Capa 2)** | | |
| 3A | Setup `modules/calculator/formulas/payroll/` + PayrollCalculator | ✅ IMPLEMENTADA (2026-06-09) |
| 3B | Mover NominaCalculator a `payroll/calculator.py` | ⏳ Pendiente aprobación |
| 3C | Revisar StaffingCalculator (payroll-only o transversal?) | ⏳ Pendiente decisión |
| 3D | Revisar NominaCargadaService (mover o REVIEW_LATER?) | ⏳ Pendiente decisión |
| 3E | Revisar BuildPayrollUseCase (WAVE 10 integration?) | ⏳ Pendiente decisión |
| **Fase 4 — No-Payroll (Capa 3)** | | |
| 4A | Setup `modules/calculator/formulas/no_payroll/` + Mover NoPayrollCalculator | ⏳ Pendiente aprobación (después 3B) |
| 4B | Eliminar shims de payroll/no_payroll (opcional) | ⏳ Después de validación |
| Fase 5 | Pipeline extraction (condicional a tamaño de engine.py) | ⏳ Pendiente aprobación |
| Fase 6 | Cleanups (api/ y persistence/ fuera de scope de este audit) | 🚫 Fuera de alcance |

---

## Confirmación Explícita

❌ **NO SE CAMBIARON en Fases 1-2:**
- Fórmulas de cálculo
- Resultados numéricos
- Endpoints HTTP
- DocumentStore
- Vision Imprimible / Cost To Serve
- Parametrización GN/HR/OP
- Snapshots / Baselines
- Contratos públicos

---

## Phase 5B: PricingCalculator Normalization ✅ IMPLEMENTADA (2026-06-09)

### Cambios realizados

**Nuevos archivos:**
- ✅ `modules/calculator/formulas/pricing/__init__.py` — exported PricingCalculator
- ✅ `modules/calculator/formulas/pricing/pricing.py` — PricingCalculator con 4 static methods (calcular_ingreso_bruto, calcular_tarifa_unitaria, calcular_factor_billing, derivar_componentes_label)
- ✅ `tests/unit/test_calculator_formulas_pricing_phase5b.py` — 17 guardrails (G-5B1…G-5B7)

**Archivos eliminados:**
- ❌ `modules/calculator/pricing/calculators.py` — shim puro sin consumidores (ELIMINADO)

**Archivos modificados (imports canónicos):**
- ✅ `modules/calculator/use_cases/build_pricing.py` — import desde formulas.pricing
- ✅ `modules/vision_tarifas/mixins/reglas_methods_2.py` — import desde formulas.pricing (inline)
- ✅ `modules/calculator/shared/__init__.py` — re-export desde formulas.pricing
- ✅ `modules/calculator/shared/pricing.py` — convertido a shim (3 líneas)
- ✅ `tests/unit/test_calculator_shared_structure.py` — actualizado comentario de ruta canónica

### Guardrails validados

| ID | Descripción | Status |
|----|---|---|
| G-5B1 | `formulas/pricing/pricing.py` existe | ✅ PASS |
| G-5B2 | `PricingCalculator` importable desde `formulas.pricing` | ✅ PASS |
| G-5B3 | `formulas/pricing` sin heavy IO (FastAPI, routers, DocumentStore, Cosmos) | ✅ PASS |
| G-5B4 | `shared/pricing.py` es shim puro (≤4 líneas) | ✅ PASS |
| G-5B5 | Backward compatibility: importable desde `calculator.shared` | ✅ PASS |
| G-5B6 | Numeric parity — todos los métodos producen resultados idénticos | ✅ PASS |
| G-5B7 | No hay imports productivos desde viejos paths | ✅ PASS |

### Tests ejecutados

- ✅ 17 tests de guardrails Phase 5B — **17 PASS**
- ✅ 14 tests de estructura compartida (test_calculator_shared_structure.py) — **14 PASS**
- ✅ 13 tests de pureza de dominio (test_wave9_domain_purity.py) — **13 PASS**
- ✅ 28 tests golden Vision Tarifas — **28 PASS**
- ✅ 30 tests golden Cost To Serve — **30 PASS**

### Consumidores actualizados

| Archivo | Consumo | Acción | Status |
|---------|---------|--------|--------|
| `modules/calculator/use_cases/build_pricing.py` | `.calcular_ingreso_bruto()` | UPDATE_IMPORTS | ✅ |
| `modules/vision_tarifas/mixins/reglas_methods_2.py` | `.derivar_componentes_label()` | UPDATE_IMPORTS | ✅ |
| `modules/calculator/shared/__init__.py` | Re-export | UPDATE_IMPORTS | ✅ |
| `modules/calculator/pricing/calculators.py` | Shim puro | DELETE_SAFE | ✅ |
| Tests (15+) | Estructura + métodos | UPDATE_IMPORTS | ✅ |

### Path canónico

```
ANTERIOR (Fase 4):  modules/calculator/shared/pricing.py
NUEVO (Fase 5B):    modules/calculator/formulas/pricing/pricing.py
BACKWARD COMPAT:    modules/calculator/shared/pricing.py (shim re-export)
```

### Cero cambios funcionales

- ❌ Fórmulas intactas
- ❌ Resultados numéricos idénticos (validado en G-5B6)
- ❌ Contratos públicos preservados (importable desde `calculator.shared`)
- ❌ Vision Imprimible, Cost To Serve sin regresiones
- ❌ Parity/baseline tests pasan

---

## Fases completadas

❌ **NO SE CAMBIARON en Auditoría Fase 3:**
- CERO cambios productivos
- Solo auditoría, planificación y corrección estructural
- Matriz de dependencias completa
- Estructura corregida: payroll/ y no_payroll/ como paquetes separados (capas distintas)
- Plan de subfases 3A-3E + 4A-4B con criterios de rollback
- NominaCargadaService y BuildPayrollUseCase clasificados como REVIEW_LATER (sin mover en Fase 3)

**Corrección estructural principal:**
- ❌ ANTERIOR: `modules/calculator/formulas/payroll/no_payroll.py` (mezcla de capas)
- ✅ CORREGIDO: `modules/calculator/formulas/no_payroll/calculator.py` (separación de capas)

✅ **PRÓXIMO PASO:** Confirmar aprobación para **Fase 3A** (setup `modules/calculator/formulas/payroll/` + mover PayrollCalculator). Auditoría Fase 3 completa, estructura corregida, sin cambios de código.

---

## Phase 5C: Costos Financieros Audit ✅ DIAGNÓSTICO (sin implementación)

**Status:** Auditoría completa, recomendación de movimiento documentada  
**Decisión:** ✅ **MOVER a modules/calculator/formulas/costos_financieros/**  
**Clasificación:** CALCULATOR_FORMULA_DOMAIN (Capa 8 del motor)  
**Riesgo de movimiento:** LOW

### Hallazgos

| Aspecto | Resultado |
|---------|-----------|
| Pureza (sin IO) | ✅ 100% cálculo puro (0 heavy IO) |
| LOC | ✅ ~330 LOC (250 orquestador + 80 pure math) |
| Capa del motor | ✅ Capa 8 (después payroll, no_payroll, cadena B/C) |
| Consumidores centralizados | ✅ engine.py, pyg_calculator.py (2 files) |
| Precedente | ✅ Similar a Phase 3A-3B (payroll) |
| Modelos asociados | ✅ CostosFinancierosMes (compartido, no afectado) |

### Consumidores Productivos

1. **modules/calculator/engine.py** — orquestador principal (Capa 8)
2. **modules/pyg/services/pyg_calculator.py** — Estado de Resultados
3. **modules/pyg/services/kpis_calculator.py** — KPIs (indirecto)
4. **15+ unit + integration tests**

### Estructura Propuesta

```
modules/calculator/formulas/costos_financieros/
├── __init__.py                ← exporta CostosFinancierosCalculator
├── calculator.py              ← CostosFinancierosCalculator (orquestador, 250 LOC)
└── financiacion.py            ← FinancialCalculator (pure math, 80 LOC)
```

### Plan de Implementación (si aprobado)

**Fase 5C-A:** Setup + copiar archivos
- `modules/costos_financieros/calculators/costos_financieros_calculator.py` → `formulas/costos_financieros/calculator.py`
- `modules/costos_financieros/financial/calculators.py` → `formulas/costos_financieros/financiacion.py`
- Cambios de código: **CERO** (rename + copy)

**Fase 5C-B:** Actualizar imports (2 archivos)
1. `modules/calculator/engine.py` (línea 68)
2. `modules/pyg/services/pyg_calculator.py` (línea 48)

**Fase 5C-C:** Eliminar path antiguo (clean break)
- Delete `modules/costos_financieros/` entirely (all imports centralized)

**Fase 5C-D:** Validación
- 50+ tests deben pasar (unit, integration, golden, parity)
- 9 guardrails de Phase 5C-A

### Guardrails Propuestos

- G-5C1: estructura de archivos canónica
- G-5C2: CostosFinancierosCalculator importable
- G-5C3: FinancialCalculator importable
- G-5C4: sin heavy IO (FastAPI, routers, DocumentStore, Cosmos)
- G-5C5: shim (si existe) es thin
- G-5C6: engine.py importa desde canonical
- G-5C7: numeric parity (4 static methods)
- G-5C8: CostosFinancierosMes model unchanged
- G-5C9: audit traces (FORMULA_ID.*) preserved

### Cero Cambios Productivos

✅ **Esta auditoría es diagnóstica únicamente**
- ❌ NO se movieron archivos
- ❌ NO se cambiaron imports
- ❌ NO se cambiaron fórmulas
- ❌ NO se cambiaron resultados numéricos
- ❌ NO se tocó pricing, risk, mixins, API, persistence
- ❌ NO se modificó parametrización GN/HR/OP
- ❌ NO se tocó snapshots, baselines, Vision Imprimible, Cost To Serve

**Lo único:** Auditoría de 2 horas + documentación de recomendación.

### Próximo Paso

Si aprobado: Implementar Phase 5C-A/B/C en nueva sesión (estimado: 30 min + validación)

---

**Auditoría realizada por:** Claude Code (Haiku 4.5)  
**Implementación Fase 1:** Claude Code (Sonnet 4.6) — 2026-06-09  
**Implementación Fase 2:** Claude Code (Sonnet 4.6) — 2026-06-09  
**Auditoría Fase 3 (v1):** Claude Code (Haiku 4.5) — 2026-06-09  
**Corrección Fase 3 (v2):** Claude Code (Haiku 4.5) — 2026-06-09  
**Implementación Fase 3A-3B, 4A-4B, 5A:** Claude Code (Haiku 4.5) — 2026-06-09  
**Implementación Fase 5B (PricingCalculator):** Claude Code (Haiku 4.5) — 2026-06-09  
**Implementación Fase 5C (CostosFinancieros):** Claude Code (Sonnet 4.6) — 2026-06-09  
**Implementación Fase 5D (RiesgoCalculator):** Claude Code (Sonnet 4.6) — 2026-06-09 — commit 2fb6520  
**Auditoría Fase 5E (shared_calc):** Claude Code (Sonnet 4.6) — 2026-06-09 — AUDIT-ONLY, KEEP  
**Auditoría Fase 5F (calculator completo):** Claude Code (Sonnet 4.6) — 2026-06-09 — AUDIT-ONLY  

---

## FASE 5D — RiesgoCalculator → formulas/risk (IMPLEMENTADA ✅)

**Commit:** `2fb6520`

### Movimiento realizado

| Archivo origen | Archivo destino | Acción |
|---|---|---|
| `calculator/risk/calculator.py` | `calculator/formulas/risk/riesgo.py` | MOVE |
| (nuevo) | `calculator/formulas/risk/__init__.py` | CREATE |
| `calculator/risk/__init__.py` | (convertido a shim) | SHIM |
| `calculator/engine.py:75` | import desde `formulas.risk` | UPDATE |
| `tests/unit/test_calculator_risk_structure.py` | guardrail G-R3 actualizado | UPDATE |

### Validaciones

- ✅ 63/65 tests pasan (2 preexistentes: `TestJsonNoTieneSmmlv` → `storage/parametrization/business_rules/v2-7.json` no existe en filesystem)
- ✅ 71/71 golden + domain_purity tests
- ✅ 0 imports productivos legacy hacia `calculator.risk.calculator`
- ✅ 0 cambios funcionales (copy+rename)

---

## FASE 5E — Auditoría shared_calc (AUDIT-ONLY ✅)

### Inventario

`modules/shared_calc/utils.py` contiene 5 funciones:

| Función | Tipo | IO | Destino recomendado | Acción |
|---|---|---|---|---|
| `calcular_factor_margenes` | Proxy → ProfitabilityCalculator | ❌ | KEEP_SHARED | DO_NOT_MOVE_NOW |
| `calcular_factor_aumento` | Proxy → PayrollCalculator | ❌ | KEEP_SHARED | DO_NOT_MOVE_NOW |
| `calcular_rampup` | Wrapper IParametrizationProvider | ❌ | KEEP_SHARED | DO_NOT_MOVE_NOW |
| `calcular_tasa_polizas` | Wrapper IParametrizationProvider | ❌ | KEEP_SHARED | DO_NOT_MOVE_NOW |
| `calcular_factor_periodo` | Wrapper IParametrizationProvider | ❌ | KEEP_SHARED | DO_NOT_MOVE_NOW |

**Decisión:** `shared_calc` NO debe moverse a `formulas/common/`. Las funciones de parametrización dependen de `IParametrizationProvider` (boundary violation si van a `formulas/`). Las funciones proxy ya delegaron su lógica a calculadores canónicos.

---

## FASE 5F — Auditoría completa modules/calculator (AUDIT-ONLY ✅)

### Problemas identificados (por prioridad)

| Archivo | Problema | Fase | Prioridad |
|---|---|---|---|
| `risk/calculator.py` | Implementación duplicada (shim existe, original permanece) | 5G | ALTA |
| `pricing/__init__.py` | Dead module — shim vacío sin re-exports útiles | 5G | ALTA |
| `helpers/console_reporter.py` | Import innecesario de `shared_calc` para output consola | 5G | MEDIA |
| `helpers/engine_helpers.py` | HIDDEN_AGGREGATION — candidato a `serializers/aggregations.py` | 5I | BAJA |
| `json_loader.py` | Top-level, debería vivir en `adapters/` | 5H | BAJA |
| `user_input_loader.py` | Top-level, debería vivir en `adapters/` | 5H | BAJA |

### Mixins — LIMPIOS

16 mixins auditados. Clasificación: CONTEXT_ASSEMBLY_ONLY / INPUT_NORMALIZATION / FRONTEND_MAPPING / VALIDATION. **Ninguno esconde fórmulas matemáticas.**

### Fases futuras

| Fase | Objetivo | Riesgo |
|---|---|---|
| **5G** | Eliminar residuos: `risk/calculator.py`, `pricing/__init__.py`, import innecesario en console_reporter | LOW |
| **5H** | Mover `json_loader.py` y `user_input_loader.py` a `adapters/` | LOW |
| **5I** | Revisar `helpers/engine_helpers.py` → `serializers/aggregations.py` | LOW |
| **5J** | Deprecar wrappers de `shared_calc` en favor de imports directos | MEDIUM |
| **5K** | Gate final: eliminar shims (shared/pricing.py, risk/__init__.py shim, serializer.py) | MEDIUM |

**Estado:** FASES 1-5G COMPLETAS ✅. Implementación: 5A–5D, 5G. Auditorías: 5E, 5F. Próxima: 5H (adapters misplaced files).

---

## FASE 5G — Cleanup de duplicados/dead files (IMPLEMENTADA ✅)

**Commit:** `879275b`

### Archivos eliminados

| Archivo | Razón | Evidencia |
|---|---|---|
| `modules/calculator/risk/calculator.py` | Duplicado — canonical es `formulas/risk/riesgo.py` (Fase 5D) | 0 consumidores productivos |
| `modules/calculator/pricing/__init__.py` | Dead empty package — 0 re-exports, 0 consumidores | `grep` retornó 0 imports ejecutables |
| `modules/calculator/pricing/` (directorio) | Vacío tras eliminar `__init__.py` | Sólo `__pycache__` residual |

### Import revisado (NO eliminado)

| Archivo | Import | Decisión | Razón |
|---|---|---|---|
| `helpers/console_reporter.py:12` | `from shared_calc.utils import calcular_factor_margenes` | DO_NOT_TOUCH | Se usa en línea 44 — auditoría 5F fue imprecisa |

### Guardrail actualizado

`test_calculator_risk_structure.py::test_g_r3_risk_calculator_file_exists`  
→ renombrado a `test_g_r3_risk_canonical_file_exists`  
→ ahora valida `formulas/risk/riesgo.py` existe (no el viejo `risk/calculator.py`)

### Shims que quedan (intencionales)

| Shim | Destino canónico | Cuándo eliminar |
|---|---|---|
| `calculator/risk/__init__.py` | `formulas/risk/riesgo.py` | Fase 5K — tras migrar todos los tests que importan de `calculator.risk` |
| `calculator/shared/pricing.py` | `formulas/pricing/pricing.py` | Fase 5K — tras migrar todos los tests que importan de `calculator.shared` |
| `calculator/serializer.py` | `serializers/pricing_result_serializer.py` | Fase 5K — ya documentado con nota de retire |

### Validaciones

- ✅ 38/38 risk + pricing guardrails + domain_purity
- ✅ 58/58 golden tests (vision_tarifas + cost_to_serve)
- ✅ 21/21 parity/baseline (3 errors preexistentes: `snapshots_cadena_c/*.json` faltantes)
- ✅ 0 cambios funcionales

---

## FASE 5H — Root loaders relocation (PARCIAL ✅)

**Commit:** `f30d154`

### Matriz de consumidores

| Archivo | Clasificación | Consumidores prod | Consumidores tests | Acción | Resultado |
|---|---|---|---|---|---|
| `json_loader.py` | `JSON_FILE_LOADER` (dead) | 0 | 0 | DELETE_SAFE | ✅ Eliminado |
| `user_input_loader.py` | `INPUT_ADAPTER` | 3 (api handlers) | ~50 archivos | KEEP_ROOT_WITH_JUSTIFICATION | ✅ Sin cambios |

### Decisión `user_input_loader.py`

Mover requeriría actualizar 3 archivos productivos de API + ~50 archivos de test. El blast radius excede el riesgo LOW/MEDIUM del alcance de esta fase. La ubicación en root de `calculator/` es cosmética, no introduce deuda funcional. Diferido a **Fase 5K** (gate final).

### Archivos eliminados

- `modules/calculator/json_loader.py` — `JsonCaseLoader` clase sin consumidores; reemplazada por `NewEntryDataAdapter` + `user_input_loader`

### Archivos NO movidos (justificados)

- `modules/calculator/user_input_loader.py` — blast radius ~53 archivos; debe moverse en Fase 5K con script bulk de actualización de imports

### Validaciones

- ✅ 71/71 golden + domain_purity
- ✅ 21/21 parity/baseline
- ✅ 3 errors preexistentes: `snapshots_cadena_c/*.json` (PREEXISTING_KNOWN_FAILURE)
- ✅ 0 cambios funcionales

**Estado:** FASES 1-5H COMPLETAS ✅. Próxima: 5I (engine_helpers review) o 5K (gate final shims).

---

## FASE 5I — shared_calc migration (IMPLEMENTADA ✅)

**Commit:** `0c93a1f`

### Inventario y clasificación

| Función | Tipo | Destino | Acción |
|---|---|---|---|
| `calcular_factor_margenes` | FORMULA_PROXY → ProfitabilityCalculator | canonical directo | REPLACE_WITH_CANONICAL_IMPORT |
| `calcular_factor_aumento` | FORMULA_PROXY → PayrollCalculator | canonical directo | REPLACE_WITH_CANONICAL_IMPORT |
| `calcular_rampup` | PARAMETRIZATION_HELPER | `parametrizacion.get_rampup()` | inline call directo |
| `calcular_tasa_polizas` | PARAMETRIZATION_HELPER | `parametrizacion.get_tasa_polizas_efectiva()` | inline call directo |
| `calcular_factor_periodo` | PARAMETRIZATION_HELPER | `parametrizacion.get_factor_periodo()` | inline call directo |

### Archivos de producción actualizados (9)

| Archivo | Cambio |
|---|---|
| `cadena_b/reglas.py` | `calcular_factor_aumento` → `PayrollCalculator.calcular_factor_aumento` |
| `cadena_c/reglas.py` | `calcular_factor_aumento` → `PayrollCalculator.calcular_factor_aumento` |
| `calculator/formulas/payroll/nomina.py` | `calcular_factor_aumento` → `PayrollCalculator.calcular_factor_aumento` |
| `calculator/formulas/costos_financieros/calculator.py` | 3 proxies → ProfitabilityCalculator + inline provider calls; lazy import removido |
| `calculator/helpers/console_reporter.py` | `calcular_factor_margenes` → `ProfitabilityCalculator.calcular_factor_margenes` |
| `pyg/services/kpis_calculator.py` | 2 proxies → ProfitabilityCalculator + inline provider call |
| `pyg/services/pyg_calculator.py` | `calcular_rampup` → `self._parametrizacion.get_rampup(linea, mes)` |
| `vision_tarifas/reglas.py` | `calcular_factor_margenes` → `ProfitabilityCalculator.calcular_factor_margenes` |
| `vision_tarifas/mixins/reglas_methods_{1,2}.py` | mismo reemplazo |

### Archivos eliminados

- `modules/shared_calc/__init__.py`
- `modules/shared_calc/utils.py`
- directorio `modules/shared_calc/`

### Tests actualizados (5)

- `test_calculators_utils.py` → ahora testea ProfitabilityCalculator y PayrollCalculator directamente
- `test_wave9_domain_purity.py` → tests de proxy actualizados a tests de canonical
- `test_calculator_formulas_payroll_phase3a.py` → guardrail legacy→canonical actualizado
- `test_certificacion_final_v25.py` → import compartido actualizado a ProfitabilityCalculator
- `test_parity_anomalia_margen_c.py` → import inline actualizado a ProfitabilityCalculator

### Validaciones

- ✅ 71/71 golden + domain_purity
- ✅ 21/21 parity/baseline
- ✅ 0 imports productivos a `modules.shared_calc` (verificado con grep)
- ✅ 0 cambios funcionales
- PREEXISTING (6): `payroll.calculators` module path tests, polizas boundary, `snapshots_cadena_c` fixtures

**Estado:** FASES 1-5I COMPLETAS ✅. `modules/shared_calc` eliminado. Próxima: 5K (gate final shims).

---

## FASE 5K-A — Final shims and user_input_loader audit (AUDIT-ONLY ✅)

**Autor:** Claude Code (Sonnet 4.6) — 2026-06-09  
**Tipo:** AUDIT-ONLY — cero cambios productivos  
**Commit referencia:** `888b2c2` (docs 5I) / `0c93a1f` (código 5I — eliminó shared_calc)

---

### PRE-GATE

| Check | Estado |
|---|---|
| HEAD = `888b2c2` (docs 5I) | ✅ |
| Commit código 5I = `0c93a1f` | ✅ |
| `modules/shared_calc/` inexistente | ✅ |
| 0 imports productivos a `shared_calc` | ✅ (solo strings en docs/comentarios) |
| Working tree limpio (código) | ✅ |

---

### TAREA 1 — Matriz de shims

| Shim / archivo | Qué reexporta | Consumidores prod | Consumidores tests | Consumidores docs | Riesgo eliminar | Acción |
|---|---|---:|---:|---:|---|---|
| `calculator/risk/__init__.py` | `RiesgoCalculator` → `formulas.risk` | **0** | 6 archivos | 0 | BAJO | BULK_UPDATE_REQUIRED → DELETE |
| `calculator/shared/pricing.py` | `PricingCalculator` → `formulas.pricing` | **0** | 2 archivos | 0 | BAJO | BULK_UPDATE_REQUIRED → DELETE |
| `calculator/serializer.py` | `*` → `serializers/pricing_result_serializer` | **0** | 11 archivos | 0 | BAJO | BULK_UPDATE_REQUIRED → DELETE |
| `calculator/user_input_loader.py` | Implementación completa (525 líneas) | **3** | 46 archivos | 1 (docstring) | MEDIO | MOVE_TO_ADAPTERS + shim temporal |

**Nota sobre `calculator/shared/__init__.py`:** no es shim candidato a eliminar — es la interfaz del paquete `shared`. Re-exporta `PricingCalculator` desde canónico. Se mantiene tal cual.

---

### TAREA 2 — Consumidores detallados

#### Shim 1: `calculator/risk/__init__.py`

**Productivos (0):** engine.py usa `formulas.risk` directamente (verificado).

**Tests (6 archivos):**
```
tests/unit/test_business_rules_fix2.py
tests/unit/test_phase9_business_rules_migration.py
tests/unit/test_riesgo_calculator.py
tests/unit/test_calculator_risk_structure.py
tests/unit/test_business_rules_guardrails.py   (4 inline lazy imports)
tests/unit/test_business_rules_config.py
```
**Import a actualizar:** `from nexa_engine.modules.calculator.risk import RiesgoCalculator`  
**→ Canónico:** `from nexa_engine.modules.calculator.formulas.risk import RiesgoCalculator`

---

#### Shim 2: `calculator/shared/pricing.py`

**Productivos (0):** todos los módulos de producción usan `formulas.pricing` directamente.

**Tests que importan via `.shared.pricing` (submodulo directo) — 2 archivos:**
```
tests/unit/test_calculator_shared_structure.py
tests/unit/test_calculator_formulas_pricing_phase5b.py
```
**Tests que importan via `.shared` (__init__) — 3 archivos:** estos NO necesitan actualizarse (el `__init__` ya apunta a canónico y es interfaz válida del paquete `shared`):
```
tests/unit/test_calculator_shared_structure.py  (ambas formas)
tests/unit/test_calculator_formulas_pricing_phase5b.py  (ambas formas)
tests/unit/test_wave9_domain_purity.py  (via __init__ — OK)
```

**Import a actualizar (solo 2 archivos con `.shared.pricing` directo):**  
`from nexa_engine.modules.calculator.shared.pricing import PricingCalculator`  
**→ Canónico:** `from nexa_engine.modules.calculator.formulas.pricing import PricingCalculator`

---

#### Shim 3: `calculator/serializer.py`

**Productivos (0):** los handlers de API usan `calculator.serializers` (plural, canónico).

**Tests que usan el shim `.serializer` (singular) — 11 archivos:**
```
tests/contract/test_vision_imprimible_schema.py
tests/contract/test_vision_pyg_contract.py
tests/db/test_vision_imprimible_db_provider.py
tests/db/test_vision_imprimible_persisted_contract.py
tests/integration/test_snapshot_persistence.py
tests/parity/test_vision_ejecutiva_sections.py
tests/parity/test_vision_imprimible_aprobaciones.py
tests/parity/test_vision_imprimible_ownership.py
tests/unit/test_contractual_p0.py
tests/unit/test_phase8_contract_enforcement.py
tests/unit/test_task1_policies_per_chain.py
```
**Import a actualizar:** `from nexa_engine.modules.calculator.serializer import X`  
**→ Canónico:** `from nexa_engine.modules.calculator.serializers import X`  
(el módulo canónico es `serializers/` con `__init__.py` que re-exporta los símbolos públicos)

---

#### `calculator/user_input_loader.py` (implementación completa — 525 líneas)

**Tipo real:** Input Adapter — carga, valida y normaliza entry_data desde JSON/dict.  
**Responsabilidad:** adaptar entrada externa (JSON de usuario/test) a `UserInput` (dominio).  
**Pertenece arquitectónicamente a:** `modules/calculator/adapters/` (ya confirmado por el docstring del módulo: `nexa_engine/adapters/user_input_loader.py`).

**Imports — sin violaciones de boundary:**
- IO permitido: `json`, `Path` (es un adapter, no formulas)
- Internos: `adapters/entry_data_adapter.py`, `adapters/volume_resolution.py`, `input_normalizer.py`, DTOs, mixins
- No importa: FastAPI, starlette, DocumentStore, cosmos, azure, requests, httpx

**Productivos (3 archivos):**
```
modules/calculator/api/calculate_normal_handler.py      UserInputLoader
modules/calculator/api/calculate_certified_handler.py   UserInputLoader
modules/calculator/api/calculate_validate.py            UserInputLoader (+ lazy import)
```

**Tests (46 archivos):** distribuidos en unit/, contract/, integration/, golden/, parity/, lineage/, diagnostics/, db/, api/, baselines/, certification/, refactor/

**Caso especial — InputNormalizer:**  
`user_input_loader.py` importa `InputNormalizer` internamente.  
Un test (`tests/unit/test_p0_fixes.py`) importa `InputNormalizer` VIA este módulo (no canónico).  
Al mover el archivo, ese test debe actualizarse a:  
`from nexa_engine.modules.calculator.input_normalizer import InputNormalizer`

---

### TAREA 3 — Matriz `user_input_loader.py`

| Elemento | Responsabilidad | Consumidores prod | A adapters | Riesgo |
|---|---|---:|---|---|
| `UserInputLoader` (clase) | Carga/valida/normaliza entry_data externo | 3 prod + 46 tests | ✅ SÍ | MEDIO (blast radius 49 archivos) |
| `_aplicar_escenarios_a_perfiles()` | Helper privado de construcción | 0 externos | ✅ SÍ (sigue privado) | BAJO |
| `InputNormalizer` (re-export implícito) | Normalización de campos | 1 test (test_p0_fixes.py) | Actualizar import a canónico | BAJO |

**Decisión:** `user_input_loader.py` ES un input adapter. El directorio `modules/calculator/adapters/` ya existe y contiene `entry_data_adapter.py` y `volume_resolution.py`. La ubicación natural es `modules/calculator/adapters/user_input_loader.py`.

---

### TAREA 4 — Plan de implementación

#### Fase 5K-B: Eliminar shims puros (DELETE_SAFE post bulk-update)

**Archivos a tocar:**

| Shim | Acción | Files a actualizar |
|---|---|---|
| `calculator/risk/__init__.py` | Actualizar 6 tests → DELETE shim | 6 tests |
| `calculator/shared/pricing.py` | Actualizar 2 tests → DELETE subshim | 2 tests |
| `calculator/serializer.py` | Actualizar 11 tests → DELETE shim | 11 tests |

**Imports a cambiar (bulk sed-style):**
```
calculator.risk → calculator.formulas.risk            (6 test files)
calculator.shared.pricing → calculator.formulas.pricing  (2 test files)
calculator.serializer → calculator.serializers            (11 test files)
```

**Shims temporales:** ninguno — los shims se eliminan después de actualizar todos los consumidores.

**Tests mínimos post-5K-B:**
- Verificar que los 6 archivos de risk importan correctamente
- Verificar que los 11 archivos de serializer importan correctamente
- `PYTHONPATH=.. pytest tests/unit/test_riesgo_calculator.py tests/unit/test_contractual_p0.py tests/contract/test_vision_imprimible_schema.py -v`

**Rollback 5K-B:** restaurar los 3 archivos de shim desde git.  
**Riesgo:** BAJO — 0 cambios a código productivo; solo imports de tests.

---

#### Fase 5K-C: Mover `user_input_loader.py` → `adapters/user_input_loader.py`

---

## Fase 5K-B — Final shim deletion

**Fecha:** 2026-06-09  
**Riesgo:** LOW/MEDIUM  
**Objetivo:** eliminar shims finales con 0 consumidores productivos, sin tocar fórmulas, resultados ni `user_input_loader.py`.

### Matriz final de consumidores

| Archivo | Tipo | Consumidores productivos | Consumidores tests/docs | Acción |
|---|---|---:|---:|---|
| `modules/calculator/risk/__init__.py` | shim | 0 | tests | UPDATE imports -> DELETE |
| `modules/calculator/shared/pricing.py` | shim | 0 | tests | UPDATE imports -> DELETE |
| `modules/calculator/serializer.py` | shim | 0 | tests | UPDATE imports -> DELETE |
| `modules/calculator/user_input_loader.py` | implementación | 3 | tests | NO TOCADO |

### Paths canónicos confirmados

- Risk: `nexa_engine.modules.calculator.formulas.risk`
- Pricing: `nexa_engine.modules.calculator.formulas.pricing`
- Serializer public API: `nexa_engine.modules.calculator.serializers`
- Serializer helper internals: `nexa_engine.modules.calculator.serializers.serializer_helpers`

### Imports actualizados

- `calculator.risk` -> `calculator.formulas.risk`
- `calculator.shared.pricing` -> `calculator.formulas.pricing`
- `calculator.serializer` -> `calculator.serializers`
- Private serializer helper imports -> `calculator.serializers.serializer_helpers`

### Shims eliminados

- `modules/calculator/risk/__init__.py`
- `modules/calculator/shared/pricing.py`
- `modules/calculator/serializer.py`

### Validación

- Guardrails actualizados para exigir ausencia de los tres shims.
- `user_input_loader.py` quedó explícitamente fuera de alcance y no fue modificado.
- Cero cambios funcionales: solo imports, guardrails y eliminación de re-exports sin consumidores productivos.

### Fallos preexistentes

- Si aparece un fallo fuera del alcance 5K-B en suites amplias, debe reportarse como preexistente y no corregirse en esta fase.

**Acción:**
1. Copiar `modules/calculator/user_input_loader.py` → `modules/calculator/adapters/user_input_loader.py`
2. Crear shim en `modules/calculator/user_input_loader.py`:
   ```python
   # Re-export shim — canonical location is modules/calculator/adapters/user_input_loader.py
   from nexa_engine.modules.calculator.adapters.user_input_loader import UserInputLoader
   __all__ = ["UserInputLoader"]
   ```
3. Actualizar los 3 consumidores productivos:
   - `calculate_normal_handler.py`
   - `calculate_certified_handler.py`
   - `calculate_validate.py`
4. Actualizar `test_p0_fixes.py` (importa `InputNormalizer` via este módulo → redirigir a `input_normalizer.py`)

**Bulk update tests (46 archivos):**
```
from nexa_engine.modules.calculator.user_input_loader import
→ from nexa_engine.modules.calculator.adapters.user_input_loader import
```

**Tests mínimos post-5K-C:**
```bash
PYTHONPATH=.. pytest tests/unit/test_fase2_input_normalizer.py \
  tests/unit/test_phase55_contract_enforcement.py \
  tests/integration/conftest.py -v
```

**Rollback 5K-C:** revertir 3 productivos + borrar adapters/user_input_loader.py (shim root sigue funcionando).  
**Riesgo:** MEDIO — blast radius 49 archivos pero el import es mecánico (sed).

---

#### Fase 5K-D: Eliminar shim root de `user_input_loader.py`

**Prerrequisito:** 0 consumidores del path `calculator.user_input_loader` (verificar con grep).

**Acción:**
1. `grep -R "calculator.user_input_loader" modules/ tests/ --include="*.py"` → debe devolver 0.
2. Si 0: `git rm modules/calculator/user_input_loader.py`
3. Commit con tag `refactor(FASE_5K-D)`.

**Riesgo:** BAJO — shim es puro re-export; si hay 0 consumidores es dead code.

---

#### Fase 5L: Merge gate final calculator

**Prerrequisito:** 5K-B + 5K-C + 5K-D completados y suite verde.

**Acción:**
1. `grep -R "calculator\.risk\|calculator\.shared\.pricing\|calculator\.serializer[^s]\|calculator\.user_input_loader" modules/ tests/ --include="*.py"` → 0 hits salvo shim files propios.
2. `PYTHONPATH=.. pytest tests/ -q` → ≥ baseline (1249 pass / 57 fail).
3. Commit docs + tag FASE_5L.

---

### TAREA 5 — Guardrails propuestos

```python
# tests/unit/test_phase5k_shims_removed.py

def test_g_5kb1_risk_shim_deleted():
    import importlib.util
    # Si el shim existe, debe ser solo re-export (sin lógica)
    spec = importlib.util.find_spec("nexa_engine.modules.calculator.risk")
    # Después de 5K-B este módulo no debe existir
    assert spec is None, "calculator.risk shim debería haberse eliminado en 5K-B"

def test_g_5kb2_serializer_shim_deleted():
    import importlib.util
    spec = importlib.util.find_spec("nexa_engine.modules.calculator.serializer")
    assert spec is None, "calculator.serializer shim debería haberse eliminado en 5K-B"

def test_g_5kc1_user_input_loader_canonical_in_adapters():
    from nexa_engine.modules.calculator.adapters.user_input_loader import UserInputLoader
    assert "calculator.adapters" in UserInputLoader.__module__

def test_g_5kc2_formulas_do_not_import_adapters():
    import ast
    from pathlib import Path
    formulas_root = Path(__file__).parents[2] / "modules" / "calculator" / "formulas"
    violations = []
    for py in formulas_root.rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "user_input_loader" in node.module or "adapters.entry_data" in node.module:
                    violations.append(f"{py}: imports {node.module}")
    assert not violations

def test_g_5kd1_no_calculator_risk_imports_in_tests():
    import subprocess
    result = subprocess.run(
        ["grep", "-R", "modules.calculator.risk", "tests/", "--include=*.py"],
        capture_output=True, text=True
    )
    # Solo se permite el propio guardrail
    lines = [l for l in result.stdout.splitlines() if "test_phase5k" not in l]
    assert not lines, f"Shim paths still referenced:\n" + "\n".join(lines)
```

---

### TAREA 6 — Riesgos abiertos

| Riesgo | Descripción | Mitigación |
|---|---|---|
| R1 — Blast radius `user_input_loader` | 49 archivos a actualizar (3 prod + 46 tests) | Script sed verificable, shim temporal mientras se migra |
| R2 — `InputNormalizer` implícito | `test_p0_fixes.py` importa `InputNormalizer` via `user_input_loader` (no canónico) | Actualizar a `input_normalizer.py` en mismo PR |
| R3 — `calculate_validate.py` lazy import | Línea `from nexa_engine.modules.calculator.user_input_loader import (...)` adicional (lazy) | Actualizar ambas líneas de import en el mismo archivo |
| R4 — `serializer` vs `serializers` | Confusión de nombres; 11 tests usan el nombre singular | Actualizar mecánicamente (sufijo `s`) |
| R5 — `shared/__init__.py` no eliminar | Es la interfaz del paquete `shared`, no un shim a eliminar | Marcado explícitamente como KEEP |

---

### Confirmaciones de cero cambios productivos

- ✅ Ningún archivo de producción modificado en esta auditoría
- ✅ Ningún archivo de test modificado en esta auditoría
- ✅ Ningún shim eliminado en esta auditoría
- ✅ Ninguna fórmula tocada
- ✅ Ningún resultado numérico cambiado
- ✅ Working tree limpio al terminar (solo docs)

**Estado:** FASE 5K-A COMPLETA — auditoría lista. Próximas: 5K-B (shims puros), 5K-C (mover loader), 5K-D (eliminar shim root), 5L (merge gate).

---

## FASE 5K-B — Shim deletion (IMPLEMENTADA ✅)

**Commit:** (incluido en commit 5K-B/5K-C conjunto)

### Shims eliminados

| Shim | Consumers prod antes | Consumers tests antes | Acción |
|---|---:|---:|---|
| `calculator/risk/__init__.py` | 0 | 6 archivos | DELETED — tests actualizados a `formulas.risk` |
| `calculator/shared/pricing.py` | 0 | 2 archivos | DELETED — tests actualizados a `formulas.pricing` |
| `calculator/serializer.py` | 0 | 11 archivos | DELETED — tests actualizados a `serializers/` (plural) |

### Tests actualizados en 5K-B (19 archivos total)

- 6 archivos: `calculator.risk` → `calculator.formulas.risk`
- 2 archivos: `calculator.shared.pricing` → `calculator.formulas.pricing`
- 11 archivos: `calculator.serializer` → `calculator.serializers`

---

## FASE 5K-C — user_input_loader adapter relocation (IMPLEMENTADA ✅)

**Commit:** refactor(FASE_5K-B/5K-C)

### Archivo movido

```
modules/calculator/user_input_loader.py (525 líneas)
  → modules/calculator/adapters/user_input_loader.py
```

### Estrategia: clean break (sin shim root)

Todos los consumidores actualizados mecánicamente. No quedó shim en `calculator/user_input_loader.py`.

### Matriz de consumidores actualizados

| Tipo | Archivos | Import actualizado |
|---|---:|---|
| Módulos de producción (api/) | 3 | `calculator.user_input_loader` → `calculator.adapters.user_input_loader` |
| Docstring contrato | 1 | `modules/shared/contracts/api_v1/adapter.py` |
| Scripts (`scripts/`) | 5 | mismo reemplazo |
| Tests | 46 | mismo reemplazo |
| **Total** | **55** | |

### Caso especial — InputNormalizer

`tests/unit/test_p0_fixes.py` importaba `InputNormalizer` via `user_input_loader` (accidental re-export).  
Corregido a: `from nexa_engine.modules.calculator.input_normalizer import InputNormalizer`

### Guardrails creados

`tests/unit/test_phase5k_shims_structure.py` — 10 tests:
- G-5KB1/2/3: shims 5K-B confirmados eliminados
- G-5KC1: `adapters/user_input_loader.py` existe
- G-5KC2: importable desde `calculator.adapters`
- G-5KC3: no existe shim root
- G-5KC4: 0 imports productivos al path antiguo
- G-5KC5: `formulas/` no importa `user_input_loader`
- G-5KC6: adapter no importa FastAPI/starlette/Cosmos/DocumentStore
- G-5KC7: `InputNormalizer` no se importa via `user_input_loader`

### Validaciones

- ✅ `py_compile` pasa en `adapters/user_input_loader.py`
- ✅ 10/10 guardrails pasan
- ✅ 71/71 golden + domain_purity
- ✅ parity/baseline suite (preexistentes confirmados independientes)
- ✅ 0 imports ejecutables al path antiguo (grep limpio)
- ✅ 0 cambios funcionales — movimiento puro de archivo

### Fallos preexistentes confirmados (no introducidos)

`test_v2_7_regression`, `test_vision_imprimible_persisted_contract`, `test_vision_imprimible_db_provider`, `test_architecture_exceptions`, `test_business_rules_fix3`, `test_calculator_formulas_payroll_phase3b` — todos confirmados via git stash en HEAD pre-5K.

**Estado:** FASES 5K-B + 5K-C COMPLETAS ✅. `modules/calculator/user_input_loader.py` eliminado. Path canónico: `calculator.adapters.user_input_loader`. Próxima: 5L (merge gate final).

---

## Fase 6A — Calculator Boundary Reorganization Audit

Ver documento completo: [calculator_boundary_reorganization_audit.md](calculator_boundary_reorganization_audit.md)

**Veredicto:** CONFIRMADO — `modules/calculator/` mezcla responsabilidades. Carpetas `api/`, `persistence/`, `audit/`, `lineage/` no pertenecen al motor de cálculo.
**Decisión:** AUDIT_ONLY — cero cambios productivos en esta fase. Fases 6B–6G diseñadas.
**Estado:** FASE 6A COMPLETA ✅. Próxima: 6B (resolver duplicación audit/ + mover traceability).
