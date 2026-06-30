# CHAPTER 9: "Versionado y Modos Certificados"

**Extensión:** 8–10 páginas (2,200–2,800 palabras)

---

## SECTION 9.1: Registro Central de Versiones

### VersionRegistry: Fuente Única de Verdad

El **VersionRegistry** (`application/versioning/version_registry.py`) es el repositorio central de versiones del motor, API, fórmulas y parametrización. Su responsabilidad es:

1. Leer la versión activa de parametrización desde storage
2. Computar hashes SHA-256 de cada módulo (HR, GN, OP, business_rules)
3. Emitir snapshots inmutables (VersionMetadata) para cada simulación
4. Detectar cambios de versión (drift detection)

### Estructura de Datos

**VersionMetadata** (immutable dataclass):

```python
@dataclass(frozen=True)
class VersionMetadata:
    """
    Snapshot inmutable de todas las versiones en un momento dado.
    Se embebe en cada lineage graph y respuesta API.
    """
    
    # Versiones de los componentes
    excel_version: str                      # e.g., "V2-7"
    engine_version: str                     # e.g., "engine-v2"
    api_version: str                        # e.g., "api-v1"
    formula_set: str                        # e.g., "formula-set-v2-7"
    parametrization_version: str            # e.g., "v2-7" or UUID
    baseline_version: Optional[str]         # Para certified mode
    
    # Hashes para detectar drift
    parametrization_hashes: Dict[str, str]  # { "hr": "abc123...", "gn": "def456...", ... }
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable representation."""
        return asdict(self)
    
    def with_overrides(self, **overrides) -> "VersionMetadata":
        """Retorna copia modificada (immutable pattern)."""
        return replace(self, **overrides)
```

**VersionRegistry API:**

```python
class VersionRegistry:
    """Central repository of version metadata."""
    
    # Constantes — única fuente de verdad
    ENGINE_VERSION: str = "engine-v2"
    API_VERSION: str = "api-v1"
    PARAM_MODULES = ("hr", "gn", "op", "business_rules")
    
    def __init__(self, storage_root: Optional[Path] = None):
        """Inicializa con storage root (default: ./storage)."""
        self._storage_root = Path(storage_root or Path.cwd() / "storage")
        self._cached: Optional[VersionMetadata] = None
        self._cached_hashes: Optional[Dict[str, str]] = None
    
    def get_current(self, baseline_version: Optional[str] = None) -> VersionMetadata:
        """
        Retorna VersionMetadata actual (cached después de primer call).
        
        Args:
            baseline_version: Para certified mode, versión a comparar
        
        Returns:
            VersionMetadata snapshot (frozen)
        """
        if self._cached is not None and baseline_version is None:
            return self._cached
        
        param_version = self.get_active_parametrization_version()
        excel_version = self._read_excel_version(param_version)
        hashes = self.compute_parametrization_hashes()
        formula_set = self._derive_formula_set(param_version)
        
        meta = VersionMetadata(
            excel_version=excel_version,
            parametrization_version=param_version,
            engine_version=self.ENGINE_VERSION,
            api_version=self.API_VERSION,
            formula_set=formula_set,
            baseline_version=baseline_version,
            parametrization_hashes=hashes,
        )
        
        # Only cache the default (no baseline override) snapshot
        if baseline_version is None:
            self._cached = meta
        return meta
    
    def invalidate_cache(self) -> None:
        """Drop cached metadata. Useful cuando storage changes mid-process."""
        self._cached = None
        self._cached_hashes = None
    
    def get_active_parametrization_version(self) -> str:
        """
        Lee versión activa desde storage/parametrization/<module>/versions.json.
        
        Estrategia:
        1. Busca entry con is_active=true o status="active"
        2. Si manifesto expone stable path (e.g., "../v2-7/..."), prefiere ID legible
        3. Fallback: "unknown"
        
        Returns:
            version_id como string (e.g., "v2-7", UUID, o "unknown")
        """
        for module in self.PARAM_MODULES:
            version = self._read_active_from_versions_file(module)
            if version:
                return version
        return "unknown"
    
    def compute_parametrization_hashes(self) -> Dict[str, str]:
        """
        SHA-256 de cada JSON activo de parametrización.
        
        Idempotente y cached: siguientes calls retornan el mismo dict
        a menos que invalidate_cache() sea llamado.
        
        Returns:
            { "hr": "sha256hash...", "gn": "...", "op": "...", ... }
        """
        if self._cached_hashes is not None:
            return dict(self._cached_hashes)
        
        version = self.get_active_parametrization_version()
        hashes: Dict[str, str] = {}
        baseline_dir = self._storage_root / "parametrization" / version
        
        for module in self.PARAM_MODULES:
            path = baseline_dir / f"{module}.json"
            if not path.exists():
                # Fallback: module-specific lookup (UUID path)
                path = self._resolve_active_path(module)
                if path is None or not path.exists():
                    continue
            try:
                raw = path.read_bytes()
                hashes[module] = hashlib.sha256(raw).hexdigest()
            except OSError as exc:
                _logger.warning(
                    "[versioning] failed to hash module=%s path=%s err=%s",
                    module, path, exc
                )
        
        self._cached_hashes = dict(hashes)
        return dict(hashes)
```

### Almacenamiento: Estructura de Directorios

**Versiones de parametrización:**

```
storage/parametrization/
├─ v2-7/                           # Versión "v2-7"
│  ├─ manifest.json                # { version: "V2-7", source_file: "...", ... }
│  ├─ hr.json                      # { roles: [...], salarios: [...], ... }
│  ├─ gn.json                      # { defaults: [...], ramp_up: [...], ... }
│  └─ op.json                      # { margins: [...], rules: [...], ... }
├─ hr/
│  └─ versions.json                # [
│                                   #   { version_id: "v2-7", is_active: true, ... },
│                                   #   { version_id: "v2-6", is_active: false, ... }
│                                   # ]
├─ gn/
│  └─ versions.json                # Similar structure
├─ op/
│  └─ versions.json                # Similar structure
└─ business_rules/
   └─ versions.json                # {
                                   #   active_version: "v2-7",
                                   #   versions: [...]
                                   # }
```

**Baseline snapshots (para certified mode):**

```
storage/parametrization/
└─ baselines/
   └─ baseline-v2-7/               # Frozen snapshot
      ├─ manifest.json
      ├─ hr.json
      ├─ gn.json
      └─ op.json
```

---

## SECTION 9.2: Modo Certificado (Certified Mode)

### Flujo de Cálculo Certificado

Cuando un usuario solicita **modo certificado**, el engine retorna un **ExecutionCertificate** que garantiza reproducibilidad.

**Request → Response:**

```
POST /api/v1/simulate/calculate?mode=certified
Content-Type: application/json

{
  "panel": { ... },
  "scenarios": [ ... ],
  "parametrization_version": "v2-7"  # Optional: explicit baseline
}

        ↓ CalculatedSimulationUseCase.execute

1. Load FrozenParametrizationAdapter.from_version("v2-7")
   └─ Locks parametrization at specific version snapshot
   
2. Run NexaPricingEngine.calcular(request, frozen_provider)
   └─ Deterministic: same input → same output always
   
3. Capture VersionMetadata snapshot
   └─ Hashes de parametrización congelada
   
4. Compute ExecutionCertificate
   └─ Signed record de la ejecución
   
5. Return HTTP 201 Created

{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-05-31T14:23:45Z",
  "certified": true,
  "certificate_id": "cert-550e8400",
  "certificate": {
    "version_metadata": {
      "engine_version": "engine-v2",
      "api_version": "api-v1",
      "parametrization_version": "v2-7",
      "baseline_version": "v2-7",
      "parametrization_hashes": {
        "hr": "3a4d5f6e7c8b9a1d2e3f4a5b6c7d8e9f",
        "gn": "1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e",
        "op": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d",
        "business_rules": "xyz..."
      }
    },
    "request_hash": "sha256:...",
    "result_hash": "sha256:...",
    "lineage_hash": "sha256:...",
    "issued_at": "2026-05-31T14:23:45Z"
  },
  "visions_ready": true
}
```

### ExecutionCertificate Structure

```python
@dataclass(frozen=True)
class ExecutionCertificate:
    """
    Registro certificado de una ejecución.
    Immutable, storable, verificable.
    """
    
    # Identity
    certificate_id: str               # UUID
    simulation_id: str                # UUID of simulation
    issued_at: datetime               # ISO8601 when issued
    
    # Version snapshot
    version_metadata: VersionMetadata  # engine, api, formula, parametrization versions
    
    # Integrity hashes (detect tampering)
    request_hash: str                 # SHA-256(serialized_input)
    result_hash: str                  # SHA-256(serialized_output)
    lineage_hash: str                 # SHA-256(lineage_graph)
    
    # Baseline validation
    baseline_matched: Optional[bool]  # True if matches expected baseline
    baseline_version: Optional[str]   # Expected version_id for validation
    
    # Per-module validation results
    validation_results: Dict[str, str]  # {
                                        #   "hr": "pass",
                                        #   "gn": "pass",
                                        #   "op": "pass"
                                        # }
    
    def to_dict(self) -> Dict[str, Any]:
        """API-safe representation."""
        return {
            "certificate_id": self.certificate_id,
            "simulation_id": self.simulation_id,
            "issued_at": self.issued_at.isoformat(),
            "version_metadata": self.version_metadata.to_dict(),
            "request_hash": self.request_hash,
            "result_hash": self.result_hash,
            "lineage_hash": self.lineage_hash,
            "baseline_matched": self.baseline_matched,
            "baseline_version": self.baseline_version,
            "validation_results": dict(self.validation_results),
        }
```

### Baseline Validation Endpoint

```python
@router.post("/certification/verify/{certificate_id}")
async def verify_certificate(
    certificate_id: str,
    baseline_id: Optional[str] = Query(None),
) -> CertificateVerificationResponse:
    """
    Verifica que un ExecutionCertificate sea válido.
    
    Operaciones:
    1. Load certificate from storage
    2. Replay input → compute output
    3. Compare hashes (request, result, lineage)
    4. Optional: check si versión de parametrización = baseline_id
    5. Return verification results
    """
    cert_repo = CertificationRepository()
    cert = cert_repo.load(certificate_id)
    
    # Validate hashes
    request_valid = (cert.request_hash == hash_of_stored_request)
    result_valid = (cert.result_hash == hash_of_stored_result)
    lineage_valid = (cert.lineage_hash == hash_of_stored_lineage)
    
    # Optional: baseline check
    baseline_matched = False
    if baseline_id:
        baseline_matched = (cert.version_metadata.parametrization_version == baseline_id)
    
    return CertificateVerificationResponse(
        certificate_id=certificate_id,
        simulation_id=cert.simulation_id,
        valid=request_valid and result_valid and lineage_valid,
        baseline_matched=baseline_matched,
        version_metadata=cert.version_metadata.to_dict(),
        validation_details={
            "request_hash_valid": request_valid,
            "result_hash_valid": result_valid,
            "lineage_hash_valid": lineage_valid,
        }
    )
```

---

## SECTION 9.3: Versionado de Parametrización

### Módulos Versionados Independientemente

Cada módulo de parametrización tiene su propio schema de versión:

**1. HR (Human Resources)**
- Roles, salarios, beneficios, aportes, clasificación de cargos
- Estable: cambios raros
- Ejemplo: `v2-7` (current), `v2-6` (archive)

**2. GN (General)**
- Configuraciones globales, ramp-up curves, defaults
- Cambios frecuentes (defaults de índices, IPC)
- Ejemplo: `v2-7-gn-20260501`

**3. OP (Operational)**
- Reglas operacionales, márgenes mínimos, riesgo thresholds
- Cambios por decisión de negocios
- Ejemplo: `v2-7-op-20260515` (margen mínimo aumentado)

**4. Business Rules**
- Ley 1819, deducibilidad, cálculos de impuestos
- Cambios por cambios legales
- Ejemplo: `v2-7-br-20260101` (entrada vigencia año fiscal)

### Drift Detection (Detección de Cambios)

**Algoritmo:**

```python
def detect_drift(active_hashes: Dict[str, str], baseline_hashes: Dict[str, str]) -> Dict[str, bool]:
    """
    Compara hashes y detecta qué módulos han cambiado.
    
    Args:
        active_hashes: SHA-256 de parametrización activa (computed now)
        baseline_hashes: SHA-256 de parametrización congelada (from certificate)
    
    Returns:
        { "hr": False, "gn": True, "op": False, "business_rules": False }
        Significa: GN ha cambiado desde baseline
    """
    drift = {}
    for module in ["hr", "gn", "op", "business_rules"]:
        active_hash = active_hashes.get(module, "")
        baseline_hash = baseline_hashes.get(module, "")
        drift[module] = (active_hash != baseline_hash)
    return drift
```

**Uso en certificación:**

```python
class CertifiedCalculationUseCase:
    """Execute calculation in certified mode with locked parametrization."""
    
    def execute(self, request: EntryDataV1, baseline_version: str) -> CertifiedResult:
        # Load frozen parametrization from baseline
        frozen_provider = FrozenParametrizationAdapter.from_version(baseline_version)
        
        # Compute current hashes (for drift check)
        current_registry = VersionRegistry()
        current_hashes = current_registry.compute_parametrization_hashes()
        
        # Load baseline hashes
        baseline_hashes = self._load_baseline_hashes(baseline_version)
        
        # Detect drift
        drift = detect_drift(current_hashes, baseline_hashes)
        
        # If drift detected, warning (but still calculate with frozen values)
        if any(drift.values()):
            _logger.warning(
                "[certified] Parametrization drift detected: %s (using frozen values)",
                drift
            )
        
        # Run calculation with frozen provider
        engine = NexaPricingEngine(parametrizacion=frozen_provider)
        result = engine.calcular(pricing_request)
        
        # Issue certificate
        cert = ExecutionCertificate(
            certificate_id=str(uuid4()),
            simulation_id=result.simulation_id,
            issued_at=datetime.utcnow(),
            version_metadata=current_registry.get_current(baseline_version=baseline_version),
            request_hash=self._hash(request),
            result_hash=self._hash(result),
            lineage_hash=self._hash(result.lineage_graph),
            baseline_matched=(drift == {k: False for k in drift.keys()}),
            baseline_version=baseline_version,
            validation_results={
                module: ("pass" if not drifted else "warning")
                for module, drifted in drift.items()
            }
        )
        
        return CertifiedResult(
            simulation_id=result.simulation_id,
            certificate=cert,
            visions=result.visions,
        )
```

### Compatibilidad Hacia Atrás

**Principio:** Las versiones antiguas de parametrización siempre pueden ser cargadas.

```python
class FrozenParametrizationRepository:
    """Carga snapshots frozen de versiones antiguas."""
    
    @staticmethod
    def load(version: str) -> Optional[FrozenParametrizationV26]:
        """
        Carga frozen parametrization para versión especificada.
        
        Soporta:
        - v2-7 (current)
        - v2-6 (archive)
        - v2-5 (old archive)
        - etc.
        
        Retorna None si no existe.
        """
        path = Path("storage") / "parametrization" / f"{version}.json"
        if not path.exists():
            return None
        
        data = json.loads(path.read_text(encoding="utf-8"))
        return FrozenParametrizationV26(
            version=data["version"],
            smmlv=data["smmlv"],
            auxilio_transporte=data["auxilio_transporte"],
            gmf=data["gmf"],
            ica_rates=data["ica_rates"],
            indexation_factors=data["indexation_factors"],
            # ... more fields
        )
```

---

## SECTION 9.4: Lineage & Audit Trail

### LineageGraph: Traza Completa de Cálculo

Cada simulación genera un **LineageGraph** (grafo acíclico dirigido) que responde: *"¿De dónde vino este número?"*

```python
@dataclass(frozen=True)
class LineageGraph:
    """
    Grafo de cálculo completo. Responde preguntas de auditoría.
    """
    
    simulation_id: str               # Deal/cliente ID
    nodes: tuple[LineageNode, ...]   # Calculation steps (immutable)
    roots: tuple[str, ...]           # Final output trace_ids
    parametrization_hashes: Dict[str, str]  # Snapshot de hashes
    version_metadata: VersionMetadata        # Engine/formula versions
    generated_at: datetime           # When graph was built
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "roots": list(self.roots),
            "parametrization_hashes": dict(self.parametrization_hashes),
            "version_metadata": self.version_metadata.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }
    
    def find_ancestors(self, trace_id: str) -> List[LineageNode]:
        """Query: todos los inputs que contribuyen a este trace_id."""
        ...
    
    def find_descendants(self, trace_id: str) -> List[LineageNode]:
        """Query: todos los outputs que dependen de este trace_id."""
        ...
```

### LineageNode: Nodo Individual

```python
@dataclass(frozen=True)
class LineageNode:
    """
    Un paso de cálculo. Enlaza inputs → outputs.
    """
    
    # Identity
    trace_id: str                    # UUID único en la simulación
    simulation_id: str
    
    # Semantic location
    stage: str                       # e.g., "PAYROLL_BUILD", "FINANCIALS", "P&G"
    calculator: str                  # Qualified name: "NominaCalculator"
    value_name: str                  # e.g., "ingreso_neto_mes_1"
    
    # Data
    value: Any                       # Calculated result (number, dict, list)
    formula: str                     # Human-readable formula description
    
    # Lineage
    inputs: tuple[LineageRef, ...]   # Parents: where data came from
    outputs: tuple[str, ...]         # Children: trace_ids downstream
    
    # Versioning
    engine_version: str = "engine-v2"
    formula_set: str = "formula-set-v2-7"
    
    # Performance (optional)
    timestamp_ms: float = 0.0        # Benchmark timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "simulation_id": self.simulation_id,
            "stage": self.stage,
            "calculator": self.calculator,
            "value_name": self.value_name,
            "value": _coerce_to_json(self.value),
            "formula": self.formula,
            "inputs": [ref.to_dict() for ref in self.inputs],
            "outputs": list(self.outputs),
            "engine_version": self.engine_version,
            "formula_set": self.formula_set,
            "timestamp_ms": self.timestamp_ms,
        }
```

### LineageRef: Referencia a Origen

```python
@dataclass(frozen=True)
class LineageRef:
    """
    Referencia a un origen de datos. Soporta múltiples fuentes.
    """
    
    # Tipo de origen
    source_type: str                 # "request", "parametrization", "excel", "computed", "constant"
    
    # Identificador estable
    source_id: str                   # e.g.,
                                     #   "request.panel.margen_a"
                                     #   "hr.nomina[Director].salario"
                                     #   "excel:Vision Tarifas!H42"
                                     #   "computed:trace:550e8400-..."
    
    # Valor
    value: Any                       # The actual value
    
    # Excel details (only for source_type == "excel")
    sheet: Optional[str]             # e.g., "Vision Tarifas"
    cell: Optional[str]              # e.g., "H42"
    formula: Optional[str]           # e.g., "=SUM(H39:H41)"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "value": _coerce_to_json(self.value),
            "sheet": self.sheet,
            "cell": self.cell,
            "formula": self.formula,
        }
```

### Ejemplo: Traza de Ingreso Neto

Request:
```json
{
  "cargo": "Director de Operaciones",
  "salario_base": 5000000,
  "modelo_cobro": "Mixto"
}
```

Lineage trace (parcial):

```
trace:001 [stage:PAYROLL_BUILD, calculator:NominaCalculator]
  value_name: "salario_base_Director"
  value: 5000000
  formula: "from request"
  inputs:
    - source_type: "request"
      source_id: "request.panel.salario_base"
      value: 5000000

trace:002 [stage:PAYROLL_BUILD, calculator:NominaCalculator]
  value_name: "factor_indexacion_smlv"
  value: 1.0253
  formula: "factor from parametrization[2026-05]"
  inputs:
    - source_type: "parametrization"
      source_id: "op.factor_indexacion.SMLV[2026]"
      value: 1.0253

trace:003 [stage:PAYROLL_BUILD, calculator:NominaCalculator]
  value_name: "salario_indexado_mes_1"
  value: 5126500
  formula: "salario_base * factor_indexacion"
  inputs:
    - source_type: "computed"
      source_id: "computed:trace:001"
      value: 5000000
    - source_type: "computed"
      source_id: "computed:trace:002"
      value: 1.0253

trace:004 [stage:PAYROLL_BUILD, calculator:NominaCalculator]
  value_name: "aporte_afiliacion"
  value: 307590
  formula: "salario * 6%"
  inputs:
    - source_type: "computed"
      source_id: "computed:trace:003"
      value: 5126500
    - source_type: "parametrization"
      source_id: "hr.aportes.afiliacion_rate"
      value: 0.06

trace:005 [stage:PAYROLL_BUILD, calculator:NominaCalculator]
  value_name: "ingreso_neto_mes_1"
  value: 4818910
  formula: "salario_indexado - aporte_afiliacion"
  inputs:
    - source_type: "computed"
      source_id: "computed:trace:003"
      value: 5126500
    - source_type: "computed"
      source_id: "computed:trace:004"
      value: 307590
```

### LineageSnapshotRepository: Persistencia

```python
class LineageSnapshotRepository:
    """Persiste LineageGraph a almacenamiento."""
    
    def save(self, graph: LineageGraph) -> str:
        """
        Guarda graph a storage/lineage/{simulation_id}/graph.json.
        
        Returns:
            Ruta guardada
        """
        sim_id = graph.simulation_id
        path = Path("storage") / "lineage" / sim_id / "graph.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with path.open("w", encoding="utf-8") as f:
            json.dump(graph.to_dict(), f, indent=2)
        
        _logger.info("[lineage] saved graph for simulation=%s path=%s", sim_id, path)
        return str(path)
    
    def load(self, simulation_id: str) -> Optional[LineageGraph]:
        """Carga graph desde storage."""
        path = Path("storage") / "lineage" / simulation_id / "graph.json"
        if not path.exists():
            return None
        
        data = json.loads(path.read_text(encoding="utf-8"))
        return LineageGraph.from_dict(data)
```

---

## SECTION 9.5: Migración & Rollback de Versiones

### Forward Migration (engine v1 → v2)

**Scenario:** Actualizar a nueva versión de engine manteniendo parametrización antigua.

**Pasos:**

```
1. Setup nueva versión (engine-v2)
   ├─ Deploy nuevas capas de cálculo
   ├─ Registrar VersionRegistry con versión nueva
   └─ Crear test cases de parity

2. Cargar parametrización vieja
   ├─ FrozenParametrizationAdapter.from_version("v1-5")
   └─ Inyectar en engine-v2

3. Replay simulaciones antiguas
   ├─ Para cada simulation_id en archive:
   │  ├─ Load PricingRequest original
   │  ├─ Run engine-v2 con frozen-v1-5
   │  └─ Compare outputs
   └─ Verify parity (tolerancia: 0.01% por cálculo)

4. Si parity lograda
   ├─ Deprecate engine-v1
   ├─ Activate engine-v2 como default
   └─ Archive engine-v1 code

5. Si parity fallida
   ├─ Investigar diferencias
   ├─ Ajustar fórmulas en engine-v2
   └─ Repetir step 3
```

### Rollback (engine v2 → v1, si es necesario)

**Scenario:** Discover bug crítico en v2, rollback a v1 temporalmente.

**Pasos:**

```
1. Detect issue
   ├─ Monitoreo detecta spike de errors o diferencias de parity
   └─ Trigger rollback decision

2. Prepare rollback
   ├─ Activate engine-v1 code (mantenido en git)
   ├─ Update VersionRegistry.ENGINE_VERSION = "engine-v1"
   └─ Redeploy API

3. Impacted simulations
   ├─ Simulations recientes (< 24h) re-calced con v1
   ├─ Viejas simulaciones quedan como están (certified)
   └─ LineageGraph documenta versión usada

4. Investigate root cause
   ├─ Análisis post-mortem en v2 code
   ├─ Fix implementado
   └─ Testing intenso

5. Forward upgrade (step 3 arriba)
```

### Sin Data Loss

Todas las aproximaciones mantienen full audit trail:

```
storage/simulations/{sim_id}/
├─ request.json         # Original user input
├─ result-engine-v1.json    # Result con engine-v1
├─ result-engine-v2.json    # Result con engine-v2
└─ lineage-v2.json      # Traza completa

# Permite:
# - Comparar outputs entre versiones
# - Replayear con versión vieja si es necesario
# - Debugging (qué línea de cálculo causó diferencia)
```

---

## SECTION 9.6: Garantías de Reproducibilidad

### Invariantes Certificadas

Una simulación en **modo certificado** garantiza:

**1. Input Integrity**
```
hash(serialized_request) == certificate.request_hash
```
Si alguien modifica input, hash cambia → certificate inválido.

**2. Output Integrity**
```
hash(serialized_result) == certificate.result_hash
```
Si output fue alterado, certificate inválido.

**3. Parametrización Locked**
```
certificate.version_metadata.parametrization_hashes == {
  "hr": "...",
  "gn": "...",
  "op": "..."
}
```
Mismo parametrización que cuando se corrió la simulación.

**4. Reproducibility**
```
IF (request_hash == original AND
    parametrization_hashes == original)
THEN
  new_result == original_result (byte-for-byte)
```

### Testing Reproducibilidad

```python
class TestReproducibility:
    def test_certified_mode_deterministic(self):
        """Verify: running same simulation twice gives identical outputs."""
        provider = FrozenParametrizationAdapter.from_version("v2-7")
        request = PricingRequest(...)
        
        # Run 1
        engine1 = NexaPricingEngine(parametrizacion=provider)
        result1 = engine1.calcular(request)
        hash1 = hashlib.sha256(json.dumps(result1.to_dict()).encode()).hexdigest()
        
        # Run 2
        engine2 = NexaPricingEngine(parametrizacion=provider)
        result2 = engine2.calcular(request)
        hash2 = hashlib.sha256(json.dumps(result2.to_dict()).encode()).hexdigest()
        
        # Assertion
        assert hash1 == hash2, "Results differ!"
    
    def test_parametrization_drift_detection(self):
        """Verify: detect when parametrization changes."""
        baseline_hashes = {
            "hr": "abc123...",
            "gn": "def456...",
        }
        
        # Modify GN
        gn_path = Path("storage/parametrization/v2-7/gn.json")
        gn_data = json.loads(gn_path.read_text())
        gn_data["defaults"]["ica_rate"] = 0.015  # Change
        gn_path.write_text(json.dumps(gn_data))
        
        # Compute current hashes
        registry = VersionRegistry()
        current_hashes = registry.compute_parametrization_hashes()
        
        # Verify drift detected
        assert current_hashes["gn"] != baseline_hashes["gn"]
```

---

## Summary: Versioning Architecture

| Component | Responsibility | Location |
|-----------|----------------|----------|
| **VersionRegistry** | Central version metadata source | `application/versioning/version_registry.py` |
| **VersionMetadata** | Immutable snapshot of versions | `application/versioning/version_registry.py` |
| **FrozenParametrizationAdapter** | Locks parametrization at specific version | `repositories/frozen_parametrization_adapter.py` |
| **LineageGraph** | Complete calculation trace (audit) | `application/lineage/models.py` |
| **LineageNode** | Single calculation step | `application/lineage/models.py` |
| **ExecutionCertificate** | Reproducibility guarantee | `infrastructure/certification/models.py` |
| **CertificationRepository** | Persists & loads certificates | `infrastructure/certification/repository.py` |
| **LineageSnapshotRepository** | Persists & loads lineage graphs | `infrastructure/lineage/snapshot_repository.py` |

