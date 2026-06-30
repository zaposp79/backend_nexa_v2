# CHAPTER 2: "Arquitectura de Software"

**Extensión:** 8–10 páginas (2,200–2,800 palabras)

---

## SECTION 2.1: Estilo Arquitectónico

### Clean Architecture + Domain-Driven Design

NEXA utiliza **Clean Architecture (Ports & Adapters)** con principios de **Domain-Driven Design (DDD)**. Esta estructura garantiza:

- **Independencia de frameworks**: el motor de cálculo no depende de FastAPI, pytest ni ninguna otra librería específica
- **Testabilidad**: cada calculador puede probarse con datos simulados sin necesidad de IO
- **Escalabilidad**: capas parallelizables (Layers 2–5) pueden ejecutarse concurrentemente
- **Mantenibilidad**: responsabilidades claras, bajo acoplamiento

### Estructura en Capas

```
┌──────────────────────────────────────────────────────────────┐
│    REST API v1 (contracts/ + api/v1/)                        │
│    Contratos congelados (aditivo-only)                       │
│    ├─ EntryDataV1 (request payload frozen)                  │
│    ├─ SimulationResultV1 (vision payloads fixed)            │
│    └─ Versioning metadata                                    │
├──────────────────────────────────────────────────────────────┤
│    Application Layer (application/)                          │
│    Orquestación, flujos de negocio                          │
│    ├─ Use Cases: BuildPayroll, BuildStaffing, BuildPricing │
│    ├─ Orchestrators: PricingPipeline                        │
│    ├─ Ports: IParametrizationProvider                       │
│    ├─ Versioning: VersionRegistry, VersionMetadata          │
│    └─ Lineage: LineageBuilder, LineageGraph                 │
├──────────────────────────────────────────────────────────────┤
│    Domain Layer (domain/)                                    │
│    Lógica pura, sin dependencias externas                   │
│    ├─ Models: Panel, Resultado*, Vision*                   │
│    ├─ Services: CargoClassifier, SENACalculator            │
│    ├─ Calculators: Nomina, Payroll, CadenaB/C, Financiero │
│    ├─ Value Objects: CargoTipo, ModeloCobroLiteral         │
│    └─ Subdomains: profitability/, payroll/, financial/     │
├──────────────────────────────────────────────────────────────┤
│    Infrastructure Layer (infrastructure/ + repositories/)    │
│    Implementaciones concretas de puertos                     │
│    ├─ ParametrizationProvider                              │
│    ├─ FrozenParametrizationAdapter (versiones locked)      │
│    ├─ LineageSnapshotRepository                            │
│    ├─ CertificationRepository                              │
│    └─ HR/GN/OP loaders (JSON → domain objects)             │
└──────────────────────────────────────────────────────────────┘
```

### Principios Clave

**1. Inversión de Dependencias**
- Calculadores dependen de `IParametrizationProvider` (interfaz), no de `ParametrizationProvider` (implementación)
- Tests inyectan `MockParametrizationProvider` sin modificar código de producción
- Certified Mode inyecta `FrozenParametrizationAdapter` para reproducibilidad

**2. Ausencia de Estado Mutable**
- Todos los calculadores son **stateless** (sin estado interno)
- Input: domain models + parámetros
- Output: resultado determinístico
- Implicación: thread-safe, parallelizable sin locks

**3. Inmutabilidad**
- Domain models usan `frozen=True` (dataclasses)
- Result models frozen donde es crítico (LineageNode, VersionMetadata)
- Una vez emitido un resultado, nunca cambia

**4. Separación de Responsabilidades**
- Calculador no conoce API (JSON serialization, HTTP status codes)
- API no conoce detalles del calculador (acceso a variables internas)
- Adapter (`pricing_serializer.py`) traduce Domain ↔ DTO

**5. Testabilidad Total**
- Cada calculator tiene unit tests con datos ficticios
- Todas las rutas de decisión cubiertas (roles, modelos de cobro, escenarios)
- Integration tests validan pipeline completo (10 capas)

---

## SECTION 2.2: Desglose por Capas

### Domain Layer (`domain/`)

**Responsabilidad:** Contiene la lógica de negocio pura, sin acoplamiento a frameworks, bases de datos o web.

**Estructura:**

```
domain/
├─ models/
│  ├─ __init__.py          (exports: PerfilCadenaA, Panel, Resultado*, Vision*)
│  ├─ panel.py             (Panel class, enums: CargoTipo, ModeloCobroLiteral)
│  ├─ results.py           (ResultadoNomina, ResultadoCadenaB, etc.)
│  └─ visions.py           (Vision*, VersionMetadata embeddings)
├─ services/
│  ├─ cargo_classifier.py  (CargoClassifier: role classification logic)
│  ├─ especialista_calc.py (SENACalculator, EspecialistaCalculator)
│  └─ inclusion_calc.py    (InclusionCalculator: rate + benefit logic)
├─ calculators/
│  ├─ __init__.py
│  ├─ nomina.py           (NominaCalculator: Layer 2, payroll per cargo)
│  ├─ no_payroll.py       (NoPayrollCalculator: Layer 3, infrastructure+IT)
│  ├─ cadena_b.py         (CadenaBCalculator: Layer 4, platform costs)
│  ├─ cadena_c.py         (CadenaCCalculator: Layer 5, AI integration)
│  ├─ costos_totales.py   (CostosTotalesCalculator: Layer 6, aggregation)
│  ├─ costos_financieros.py (CostosFinancierosCalculator: Layer 7, interest+fees)
│  ├─ pyg.py              (PyGCalculator: Layer 8, P&L statement)
│  ├─ kpis.py             (KPIsCalculator: Layer 9, deal KPIs)
│  ├─ vision_tarifas.py   (VisionTarifasCalculator: tariff rates)
│  ├─ cost_to_serve.py    (CostToServeCalculator: fully-loaded cost)
│  ├─ riesgo.py           (RiesgoCalculator: risk metrics)
│  ├─ vision_pyg.py       (VisionPyGBuilder: P&L by month/scenario)
│  ├─ vision_datasets.py  (VisionDatasetsBuilder: detail tables)
│  ├─ vision_imprimible.py (VisionImprimibleBuilder: printable format)
│  └─ frozen_parametrization.py (FrozenParametrizationV26: immutable snapshot)
├─ subdomains/
│  ├─ profitability/      (margin calculations, breakeven)
│  ├─ payroll/            (salary bands, roles, SENA)
│  ├─ financial/          (interest rates, fees, financing)
│  ├─ staffing/           (headcount ramp-up, FTE models)
│  ├─ pricing/            (rate cards, unit economics)
│  └─ risk/               (credit risk, operational risk)
└─ models/enums.py        (CargoTipo, ModeloCobroLiteral, TipoCarga, Indexacion)
```

**Ejemplo: NominaCalculator (Layer 2)**

```python
class NominaCalculator:
    """
    Calcula nomina total (base + prestaciones + aportes) por rol.
    
    Input:  PricingRequest + IParametrizationProvider
    Output: ResultadoNomina (frozen)
    """
    
    def calcular(
        self,
        request: PricingRequest,
        provider: IParametrizationProvider,
    ) -> ResultadoNomina:
        # Descomponer por rol y escalafón
        # Aplicar SMMLV, factores de indexación, prestaciones
        # Agregar aportes (SENA, ICBF, ARP)
        # Retornar costo mensual total
        ...
```

**Características:**
- Zero side effects (no DB writes, no file IO, no logging)
- Deterministic (f(input, params) siempre retorna lo mismo)
- Testeable in isolation (sin mocks de bases de datos)

### Application Layer (`application/`)

**Responsabilidad:** Orquestar calculadores, inyectar dependencias, capturar lineage, manejar versioning.

**Estructura:**

```
application/
├─ use_cases/
│  ├─ calculate_simulation.py      (BuildPayrollUseCase, BuildPricingUseCase)
│  ├─ audit_simulation.py           (AuditSimulationUseCase: fetch lineage)
│  ├─ certified_calculation.py      (CertifiedCalculationUseCase: frozen mode)
│  ├─ build_visions.py              (VisionBuildingUseCase)
│  └─ build_scenarios.py            (ScenarioConstructionUseCase)
├─ orchestrators/
│  ├─ __init__.py
│  └─ pricing_pipeline.py           (PricingPipeline: compone 10 capas)
├─ ports/
│  ├─ __init__.py
│  ├─ i_parametrization_provider.py (Protocol: interfaz de parámetros)
│  ├─ i_logger.py                   (Protocol: logging)
│  └─ i_trace_emitter.py            (Protocol: lineage capture)
├─ versioning/
│  ├─ __init__.py
│  ├─ version_registry.py           (VersionRegistry: central version source)
│  └─ version_metadata.py           (VersionMetadata: immutable snapshot)
└─ lineage/
   ├─ __init__.py
   ├─ models.py                     (LineageGraph, LineageNode, LineageRef)
   ├─ lineage_builder.py            (LineageBuilder: construye graph)
   └─ query.py                      (LineageQuery: busca nodes por criterios)
```

**Ejemplo: PricingPipeline (Composition Root)**

```python
class PricingPipeline:
    """
    Orquestra el pipeline de 10 capas + visions.
    
    Inyecta dependencias a cada calculador.
    Captura lineage (traceability) de cada paso.
    """
    
    def __init__(self, provider: IParametrizationProvider):
        self._provider = provider
        self._lineage_builder = LineageBuilder()
    
    def execute(self, request: PricingRequest) -> PricingResult:
        # Layer 2
        nomina_result = NominaCalculator().calcular(request, self._provider)
        self._lineage_builder.register_stage("PAYROLL_BUILD", nomina_result)
        
        # Layer 3
        no_payroll_result = NoPayrollCalculator().calcular(request, self._provider)
        self._lineage_builder.register_stage("NO_PAYROLL_BUILD", no_payroll_result)
        
        # Layers 4–5 can run in parallel
        cadena_b_result = self._parallel_cadena_b(request)
        cadena_c_result = self._parallel_cadena_c(request)
        
        # Layers 6–10 sequential (dependencies)
        ...
        
        # Post-pipeline: visions
        visions = self._build_visions(aggregated_result)
        
        return PricingResult(
            simulations=[nomina_result, cadena_b_result, ...],
            visions=visions,
            lineage_graph=self._lineage_builder.build()
        )
```

### Infrastructure Layer (`infrastructure/` + `repositories/`)

**Responsabilidad:** Implementaciones concretas de puertos (IO, persistencia, parametrización).

**Estructura:**

```
infrastructure/
├─ parametrization/
│  ├─ __init__.py
│  ├─ hr_loader.py              (Carga payroll roles, salarios, beneficios)
│  ├─ gn_loader.py              (Carga general configs, ramp-up curves)
│  └─ op_loader.py              (Carga reglas operacionales, márgenes)
└─ repositories/
   ├─ __init__.py
   ├─ i_parametrization_provider.py  (Protocol — abstracción)
   ├─ parametrization_provider.py    (Implementación: Lee storage/parametrization/)
   ├─ frozen_parametrization_repository.py  (Carga snapshots frozen)
   ├─ frozen_parametrization_adapter.py     (Inyecta valores frozen + base)
   ├─ lineage_snapshot_repository.py       (Persiste graph → JSON)
   └─ certification_repository.py          (Maneja ExecutionCertificates)
```

**Ejemplo: ParametrizationProvider (Concrete Implementation)**

```python
class ParametrizationProvider(IParametrizationProvider):
    """
    Lee parametrización activa de storage/parametrization/{hr,gn,op}/.
    
    Métodos:
    - get_nomina_laboral_params() → HR data (SMMLV, aportes, roles)
    - get_gmf() → GMF rate (Banco de la República)
    - get_ica() → ICA tax by city
    - get_factor_indexacion() → Indexing factors (IPC, SMMLV, mix)
    - get_ramp_up_curve() → Ramp-up profile (months 1–24)
    """
    
    @classmethod
    def build() -> "ParametrizationProvider":
        """Factory: carga versión activa automáticamente."""
        version = VersionRegistry().get_active_parametrization_version()
        return cls._load_from_version(version)
```

### API Layer (`api/v1/` + `contracts/`)

**Responsabilidad:** Traducir HTTP ↔ Domain, exponer REST endpoints.

**Estructura:**

```
api/
├─ v1/
│  ├─ __init__.py
│  ├─ routers/
│  │  ├─ simulation.py            (POST /calculate, GET /results)
│  │  ├─ audit.py                 (GET /audit/{sim_id})
│  │  ├─ parametrization.py       (GET /parametrization/versions)
│  │  └─ certification.py         (POST /certification/verify)
│  └─ dependencies.py             (FastAPI dependency injection)
└─ contracts/
   ├─ api_v1/
   │  ├─ request/
   │  │  ├─ entry_data.py         (EntryDataV1 — frozen request schema)
   │  │  └─ __init__.py
   │  ├─ response/
   │  │  ├─ simulation_result.py   (SimulationResultV1)
   │  │  ├─ vision_tarifas.py      (VisionTarifasV1)
   │  │  ├─ vision_pyg.py          (VisionPyGV1)
   │  │  └─ __init__.py
   │  ├─ schema/
   │  │  ├─ *.schema.json          (JSON Schema specs, frozen)
   │  │  └─ README.md              (Contract versioning policy)
   │  └─ adapter.py                (pricing_serializer: Domain → DTO)
   └─ README.md
```

**Ejemplo: POST /api/v1/simulate/calculate**

```python
@router.post("/calculate", response_model=CalculationResponse, status_code=201)
async def calculate(
    request: EntryDataV1,
    mode: Literal["standard", "certified"] = "standard",
    provider: IParametrizationProvider = Depends(get_provider),
) -> CalculationResponse:
    """
    Inicia cálculo de simulación.
    
    1. Validar EntryDataV1 contra schema
    2. BuildPayrollUseCase(provider).execute(request) → PricingResult
    3. Capturar lineage + version metadata
    4. Guardar a storage/simulations/{sim_id}.json
    5. Retornar {simulation_id, status, visions_ready}
    """
    builder = SimulationContextBuilder(provider)
    pricing_request = builder.construir(request)
    
    engine = NexaPricingEngine(parametrizacion=provider)
    result = engine.calcular(pricing_request)
    
    # Persist
    repo = LineageSnapshotRepository()
    repo.save(result.lineage_graph)
    
    return CalculationResponse(
        simulation_id=result.simulation_id,
        status="complete",
        visions_ready=True
    )
```

---

## SECTION 2.3: Dependencias entre Módulos

### Dependency Graph

**Engine Orchestration Flow:**

```
engine.py (NexaPricingEngine.calcular)
│
├─ Layer 2: NominaCalculator.calcular
│  ├→ domain/services/cargo_classifier.py (classify role)
│  ├→ domain/services/especialista_calc.py (SENA logic)
│  └→ provider.get_nomina_laboral_params()
│
├─ Layer 3: NoPayrollCalculator.calcular
│  ├→ provider.get_infrastructure_params()
│  └→ provider.get_ramp_up_curve()
│
├─ Layers 4–5 (PARALLEL):
│  ├─ CadenaBCalculator.calcular
│  │  ├→ provider.get_cadena_b_params()
│  │  └→ domain/services/platform_cost_logic.py
│  │
│  └─ CadenaCCalculator.calcular
│     ├→ provider.get_cadena_c_params()
│     └→ domain/services/ai_integration_cost.py
│
├─ Layer 6: CostosTotalesCalculator.calcular
│  └→ aggregates layers 2–5
│
├─ Layer 7: CostosFinancierosCalculator.calcular
│  ├→ provider.get_gmf()
│  ├→ provider.get_ica()
│  └→ provider.get_factor_financiacion()
│
├─ Layer 8: PyGCalculator.calcular
│  ├→ aggregates layers 6–7
│  └→ computes monthly P&L
│
├─ Layer 9: KPIsCalculator.calcular
│  └→ computes deal KPIs (IRR, margin, breakeven)
│
└─ Post-Pipeline Visions:
   ├─ VisionTarifasCalculator.calcular
   ├─ CostToServeCalculator.calcular
   ├─ RiesgoCalculator.calcular
   ├─ VisionPyGBuilder.build
   ├─ VisionDatasetsBuilder.build
   └─ VisionImprimibleBuilder.build
```

### Isolation Properties

**Critical Insight:** Layers 2–5 tienen **ZERO inter-dependencies**.

```
Layer 2 (Nomina)
  ├─ depends on: request, provider
  └─ INDEPENDENT from layers 3–5

Layer 3 (NoPayroll)
  ├─ depends on: request, provider
  └─ INDEPENDENT from layers 2, 4, 5

Layer 4 (CadenaB)
  ├─ depends on: request, provider
  └─ INDEPENDENT from layers 2, 3, 5

Layer 5 (CadenaC)
  ├─ depends on: request, provider
  └─ INDEPENDENT from layers 2–4
```

**Implication:** Layers 2–5 ejecutables en paralelo en 4 threads/processes.

```python
# Pseudocode
with ThreadPoolExecutor(max_workers=4) as pool:
    future_layer2 = pool.submit(nomina_calc.calcular, request, provider)
    future_layer3 = pool.submit(no_payroll_calc.calcular, request, provider)
    future_layer4 = pool.submit(cadena_b_calc.calcular, request, provider)
    future_layer5 = pool.submit(cadena_c_calc.calcular, request, provider)
    
    results = [f.result() for f in [future_layer2, future_layer3, future_layer4, future_layer5]]
```

### Module Coupling Metrics

| Layer | Input Dependencies | Output Consumers | Parallelizable |
|-------|-------------------|------------------|---------------|
| 2 (Nomina) | request, provider | layer 6 | YES |
| 3 (NoPayroll) | request, provider | layer 6 | YES |
| 4 (CadenaB) | request, provider | layer 6 | YES |
| 5 (CadenaC) | request, provider | layer 6 | YES |
| 6 (CostosTotales) | layers 2–5 | layer 7 | NO |
| 7 (CostosFinancieros) | layer 6, provider | layer 8 | NO |
| 8 (PyG) | layer 7 | layer 9 | NO |
| 9 (KPIs) | layer 8 | visions | NO |
| Visions | layer 9 | API response | YES (each independent) |

---

## SECTION 2.4: Patrones de Diseño

### 1. Factory Pattern

**Ubicación:** `input/context_builder.py`, `application/orchestrators/pricing_pipeline.py`

```python
class SimulationContextBuilder:
    """Factory que construye PricingRequest desde entrada de usuario."""
    
    def construir(self, user_input: EntryDataV1) -> PricingRequest:
        # Valida, deserializa, enriquece con defaults
        return PricingRequest(
            panel=panel_from_user_data(user_input),
            scenarios=scenarios_from_user_data(user_input),
            ...
        )

class PricingPipeline:
    """Factory/Builder que compone orquestación de 10 capas."""
    
    @staticmethod
    def create(provider: IParametrizationProvider) -> PricingPipeline:
        return PricingPipeline(provider)
```

### 2. Strategy Pattern

**Ubicación:** `domain/services/cargo_classifier.py`, `domain/services/especialista_calc.py`

```python
class CargoClassifier:
    """Pluggable role classification strategy."""
    
    def classify(self, cargo_name: str) -> CargoTipo:
        if cargo_name in SENA_ROLES:
            return CargoTipo.SENA
        elif cargo_name in ESPECIALISTA_ROLES:
            return CargoTipo.ESPECIALISTA
        else:
            return CargoTipo.BASE

# Use cases can swap strategies:
specialist_classifier = EspecialistaCargoClassifier()
base_classifier = BaseCargoClassifier()
pipeline.use_strategy(specialist_classifier)
```

### 3. Builder Pattern

**Ubicación:** `calculators/vision_*.py`, `application/lineage/lineage_builder.py`

```python
class VisionTarifasCalculator:
    """Builds VisionTarifas by assembling rates from multiple sources."""
    
    def calcular(self, result: PricingResult, provider: IParametrizationProvider) -> VisionTarifas:
        builder = VisionTarifasBuilder()
        builder.add_base_rate(result.tarifa_base)
        builder.add_markup(result.margen_comercial)
        builder.add_taxes(result.iva_rate)
        builder.apply_rounding()
        return builder.build()

class LineageBuilder:
    """Accumulates nodes and builds immutable LineageGraph."""
    
    def register_stage(self, stage: str, result: Any) -> None:
        # Accumulates nodes
        ...
    
    def build(self) -> LineageGraph:
        # Freezes and returns immutable graph
        return LineageGraph(
            simulation_id=self._simulation_id,
            nodes=tuple(self._nodes),  # Frozen
            roots=tuple(self._roots),  # Frozen
        )
```

### 4. Repository Pattern

**Ubicación:** `infrastructure/repositories/*.py`

```python
class IParametrizationProvider(Protocol):
    """Interface (Port)."""
    
    def get_nomina_laboral_params(self) -> Dict[str, Any]:
        ...

class ParametrizationProvider(IParametrizationProvider):
    """Concrete implementation (Adapter)."""
    
    def get_nomina_laboral_params(self) -> Dict[str, Any]:
        # Reads from storage/parametrization/hr/nomina.json
        ...

class FrozenParametrizationAdapter(IParametrizationProvider):
    """Another concrete implementation for certified mode."""
    
    def __init__(self, frozen: FrozenParametrizationV26, base: ParametrizationProvider):
        self._frozen = frozen
        self._base = base
    
    def get_nomina_laboral_params(self) -> Dict[str, Any]:
        # Uses frozen SMMLV, delegates rest to base
        ...
```

### 5. Adapter Pattern

**Ubicación:** `serialization/pricing_serializer.py`, `contracts/api_v1/adapter.py`

```python
class PricingResultAdapter:
    """Translates Domain → DTO."""
    
    @staticmethod
    def to_api_response(result: PricingResult) -> SimulationResultV1:
        return SimulationResultV1(
            simulation_id=result.simulation_id,
            visions=PricingResultAdapter._visions_to_dto(result.visions),
            lineage_hash=hashlib.sha256(
                json.dumps(result.lineage_graph.to_dict()).encode()
            ).hexdigest(),
        )
    
    @staticmethod
    def from_api_request(request: EntryDataV1) -> PricingRequest:
        return PricingRequest(
            panel=Panel.from_dict(request.panel_data),
            scenarios=Scenario.from_list(request.scenarios),
            ...
        )
```

### 6. Template Method Pattern

**Ubicación:** `calculators/` (all calculators implement common interface)

```python
class Calculator(ABC):
    """Template: all calculators follow same contract."""
    
    @abstractmethod
    def calcular(
        self,
        request: PricingRequest,
        provider: IParametrizationProvider,
    ) -> Any:
        """
        Subclasses override this. Contract guarantees:
        - deterministic (no side effects)
        - stateless (no internal mutation)
        - testeable (no IO dependencies passed to constructor)
        """
        ...

# Concrete implementations
class NominaCalculator(Calculator):
    def calcular(self, request: PricingRequest, provider: IParametrizationProvider) -> ResultadoNomina:
        ...

class NoPayrollCalculator(Calculator):
    def calcular(self, request: PricingRequest, provider: IParametrizationProvider) -> ResultadoNoPayroll:
        ...
```

### 7. Immutable Value Object Pattern

**Ubicación:** `domain/models/`, `application/versioning/`

```python
@dataclass(frozen=True)
class VersionMetadata:
    """Immutable snapshot. Once created, never changes."""
    excel_version: str
    parametrization_version: str
    engine_version: str
    api_version: str
    formula_set: str
    baseline_version: Optional[str]
    parametrization_hashes: Dict[str, str]
    
    def with_overrides(self, **overrides) -> "VersionMetadata":
        # Immutable: returns NEW instance, doesn't mutate self
        return replace(self, **overrides)

@dataclass(frozen=True)
class LineageNode:
    """Every node is immutable once created."""
    trace_id: str
    simulation_id: str
    stage: str
    calculator: str
    value_name: str
    value: Any
    formula: str = ""
    inputs: tuple = field(default_factory=tuple)
    outputs: tuple = field(default_factory=tuple)
```

---

## SECTION 2.5: Flujo de Datos End-to-End

### Request → Processing → Response

**Complete request lifecycle:**

```
1. POST /api/v1/simulate/calculate
   ├─ Body: EntryDataV1 (validated against JSON Schema)
   └─ Headers: Authorization, Content-Type, Client-ID

2. CalculationRequest endpoint (routers/simulation.py)
   ├─ Deserialize EntryDataV1
   ├─ Inject IParametrizationProvider dependency
   └─ Call CalculateSimulationUseCase

3. CalculateSimulationUseCase.execute(request: EntryDataV1)
   ├─ Create SimulationContextBuilder(provider)
   ├─ Build PricingRequest from user input
   ├─ Initialize NexaPricingEngine(parametrizacion=provider)
   └─ Call engine.calcular(pricing_request)

4. NexaPricingEngine.calcular(request: PricingRequest) → PricingResult
   ├─ Layer 2: NominaCalculator.calcular() → ResultadoNomina
   ├─ Layer 3: NoPayrollCalculator.calcular() → ResultadoNoPayroll
   ├─ Layers 4–5 (parallel):
   │  ├─ CadenaBCalculator.calcular() → ResultadoCadenaB
   │  └─ CadenaCCalculator.calcular() → ResultadoCadenaC
   ├─ Layer 6: CostosTotalesCalculator.calcular() → ResultadoCostosTotales
   ├─ Layer 7: CostosFinancierosCalculator.calcular() → ResultadoCostosFinancieros
   ├─ Layer 8: PyGCalculator.calcular() → PyGMensual[]
   ├─ Layer 9: KPIsCalculator.calcular() → KPIsDeal
   └─ Build aggregated PricingResult
   
5. Post-Pipeline: Vision Building
   ├─ VisionTarifasCalculator.calcular() → VisionTarifas
   ├─ CostToServeCalculator.calcular() → VisionCostToServe
   ├─ RiesgoCalculator.calcular() → VisionRiesgo
   ├─ VisionPyGBuilder.build() → VisionPyG
   ├─ VisionDatasetsBuilder.build() → VisionDatasets
   └─ VisionImprimibleBuilder.build() → VisionImprimible

6. Lineage Capture
   ├─ LineageBuilder accumulates all nodes (10 layers + visions)
   ├─ Build immutable LineageGraph
   ├─ Compute hashes (request hash, result hash, lineage hash)
   └─ Attach VersionMetadata snapshot

7. Persistence
   ├─ Save to storage/simulations/{simulation_id}/result.json
   ├─ Save to storage/lineage/{simulation_id}/graph.json (async, best-effort)
   └─ Optional: write to database/cache

8. API Response
   ├─ Adapter: PricingResult → SimulationResultV1
   ├─ Serialize visions to DTO (Vision* → VisionDTO)
   ├─ Return HTTP 201 Created
   └─ Body: {
       simulation_id: uuid,
       created_at: iso8601,
       status: "complete",
       visions_ready: true,
       version_metadata: { engine_version, parametrization_version, ... }
     }

9. Client Polls Results
   ├─ GET /api/v1/simulate/{simulation_id}/results/tarifas
   ├─ Fetch VisionTarifas from storage
   ├─ Serialize to VisionTarifasV1
   └─ Return HTTP 200 OK + payload

10. Optional: Audit Trail
    ├─ GET /api/v1/simulate/{simulation_id}/audit
    ├─ Fetch LineageGraph from storage
    ├─ Query: all nodes in stage "PAYROLL_BUILD"
    ├─ Trace: which inputs → ingreso_neto_mes_1
    └─ Return human-readable lineage JSON
```

### Data Structures at Each Stage

```
User Input (EntryDataV1)
├─ panel: { cargo_list, scenario_id, modelo_cobro, ... }
└─ parametrization_version: Optional[str] (default: active)

        ↓ SimulationContextBuilder

PricingRequest (domain object)
├─ panel: Panel (role assignments, base rate)
├─ scenarios: Scenario[] (commercial scenarios)
├─ request_hash: str (SHA-256 of serialized input)
└─ metadata: Dict (timestamp, client_id, ...)

        ↓ NexaPricingEngine

PricingResult (aggregated domain objects)
├─ simulation_id: UUID
├─ request: PricingRequest (original input, immutable)
├─ results: Dict[str, Any]
│  ├─ nomina: ResultadoNomina
│  ├─ no_payroll: ResultadoNoPayroll
│  ├─ cadena_b: ResultadoCadenaB
│  ├─ cadena_c: ResultadoCadenaC
│  ├─ costos_totales: ResultadoCostosTotales
│  ├─ costos_financieros: ResultadoCostosFinancieros
│  ├─ pyg: PyGMensual[] (monthly P&L for 12+ months)
│  └─ kpis: KPIsDeal
├─ visions: Dict[str, Vision]
│  ├─ vision_tarifas: VisionTarifas (tariff breakdown)
│  ├─ vision_cost_to_serve: VisionCostToServe (fully-loaded cost)
│  ├─ vision_riesgo: VisionRiesgo (risk metrics)
│  ├─ vision_pyg: VisionPyG (P&L by month/scenario)
│  ├─ vision_datasets: VisionDatasets (detail tables)
│  └─ vision_imprimible: VisionImprimible (printable summary)
├─ lineage_graph: LineageGraph (full trace, immutable)
│  ├─ nodes: LineageNode[] (calculation steps)
│  ├─ roots: str[] (final output trace_ids)
│  └─ version_metadata: VersionMetadata
└─ execution_time_ms: int

        ↓ Adapter (pricing_serializer.py)

SimulationResultV1 (DTO, API-safe)
├─ simulation_id: UUID
├─ created_at: ISO8601
├─ status: "complete"
├─ visions: Dict[str, VisionDTO]
│  ├─ vision_tarifas: VisionTarifasV1
│  ├─ vision_cost_to_serve: VisionCostToServeV1
│  ├─ ...
├─ lineage_hash: str (SHA-256 of graph)
├─ version_metadata: Dict
│  ├─ engine_version: "engine-v2"
│  ├─ api_version: "api-v1"
│  ├─ parametrization_version: "v2-7"
│  ├─ formula_set: "formula-set-v2-7"
│  └─ parametrization_hashes: { hr, gn, op }

        ↓ JSON Serialization

HTTP Response Body (200 OK)
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-05-31T14:23:45Z",
  "status": "complete",
  "visions": { ... },
  "version_metadata": { ... }
}
```

---

## Summary: Architectural Principles in Action

| Principle | Implementation | Benefit |
|-----------|----------------|---------|
| **Clean Architecture** | 4-layer stack (API → App → Domain → Infrastructure) | Easy to test, deploy, refactor |
| **DDD** | Domain models (Panel, Vision*), subdomains (payroll, financial) | Business logic in one place, easy to discuss with stakeholders |
| **Dependency Inversion** | IParametrizationProvider protocol | Swap implementations (frozen, mock, live) without changing engine |
| **Statelessness** | All calculators are pure functions | Thread-safe, parallelizable (Layers 2–5) |
| **Immutability** | frozen=True dataclasses, no setters | Thread-safe by default, easier to debug |
| **Separation of Concerns** | Calculator ≠ API ≠ DB | Each layer independently testeable and deployeable |
| **Composition Root** | NexaPricingEngine + PricingPipeline | Single place to wire dependencies and understand data flow |

