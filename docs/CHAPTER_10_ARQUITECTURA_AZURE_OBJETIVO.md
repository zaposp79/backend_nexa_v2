# CHAPTER 10: "Arquitectura Azure Objetivo"

**Extensión:** 12–15 páginas (3,200–4,200 palabras)

---

## SECTION 10.1: Visión General de Arquitectura Cloud

### Estado Actual vs. Objetivo

**Current State:** Python monolito on-premises/local
- Motor de cálculo en un servidor
- Parametrización en JSON local
- Resultados en archivos o DB local
- Sin auto-scaling, sin redundancia multi-región

**Target State:** Serverless distribuido en Azure
- Stateless compute (Azure Functions)
- Global data (Cosmos DB multi-región)
- API gateway (APIM)
- Observabilidad integrada (Monitor + AppInsights)
- Auto-scaling, disaster recovery built-in

### Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                 Internet (HTTPS)                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Azure API Management (APIM)    │
        │  ├─ Rate limiting (1000 req/min)│
        │  ├─ API versioning (/api/v1)    │
        │  ├─ OAuth 2.0 authentication    │
        │  └─ Request/response logging    │
        └────────┬───────────┬────────────┘
                 │           │
        ┌────────▼─┐  ┌──────▼─────┐  ┌──────────────┐
        │ Calculate│  │  Audit    │  │Parametrization
        │Functions │  │ Functions │  │ Functions    │
        │(compute) │  │ (query)   │  │ (CRUD)       │
        └────────┬─┘  └──────┬────┘  └──────┬───────┘
                 │           │              │
        ┌────────▼───────────▼──────────────▼────────┐
        │    Azure Cosmos DB (Multi-region)          │
        │  ├─ Simulations collection (results)      │
        │  ├─ Parametrization collection (versions) │
        │  ├─ Baselines collection (certified)      │
        │  └─ Certificates collection (audit)       │
        └────────┬──────────┬────────────────────────┘
                 │          │
        ┌────────▼┐  ┌──────▼──────┐
        │ Storage │  │  Key Vault  │
        │ (backup)│  │  (secrets)  │
        └─────────┘  └─────────────┘
                │
        ┌───────▼────────────────────┐
        │ Monitor + AppInsights       │
        │ ├─ Metrics & traces         │
        │ ├─ Alerts & dashboards      │
        │ └─ Cost analysis            │
        └────────────────────────────┘
```

### Principios de Diseño

1. **Stateless Compute:** Ninguna simulación guarda estado en memoria entre requestss
2. **Global Data:** Cosmos DB replicado en 3+ regiones (RTO < 5 min)
3. **Immutable Snapshots:** Cada simulación frozen (request + result + lineage)
4. **Observable:** Cada paso logged y traceable
5. **Cost-Optimized:** Serverless (pay-per-use), auto-scaling

---

## SECTION 10.2: Componentes Azure & Responsabilidades

### 1. Azure API Management (APIM)

**Propósito:** Gateway REST v1 (autenticación, throttling, versioning)

**Configuración:**

```
APIM Policy (XML):
  <rate-limit-by-key
      calls="1000"
      renewal-period="60"
      counter-key="@(context.Request.Headers.GetValueOrDefault("X-Client-ID"))"
  />
  
  <cors
      allow-credentials="true"
      allow-origins="*"
      allow-methods="GET,POST,PUT,DELETE,OPTIONS"
  />
  
  <set-backend-service
      base-url="https://<function-app>.azurewebsites.net"
  />
```

**Endpoints (v1 contract, frozen):**

| Method | Path | Backend Function |
|--------|------|-----------------|
| POST | /api/v1/simulate/calculate | CalculateSimulation |
| GET | /api/v1/simulate/{sim_id}/results/* | RetrieveResults |
| GET | /api/v1/simulate/{sim_id}/audit | AuditSimulation |
| GET | /api/v1/parametrization/versions | ListVersions |
| POST | /api/v1/certification/verify | VerifyCertificate |

**Cost:** ~$150/month Standard tier

**SLA:** 99.95% uptime

### 2. Azure Functions (Compute)

**Propósito:** Serverless Python runtime para cálculos stateless

**Características:**
- Trigger: HTTP (REST), Event Grid (async), Timer (scheduled)
- Runtime: Python 3.9+
- Concurrency: unlimited (auto-scaling 0 → 1000s instances)
- Timeout: configurable (default 5 min, max 10 min)
- Memory: 1 GB per instance (scaling: 128 MB → 14 GB)

**Function 1: CalculateSimulation**

```python
# Function: CalculateSimulation
# Trigger: HTTP POST /api/v1/simulate/calculate
# Timeout: 600s (10 min)
# Memory: 1 GB

@app.route(route='calculate', methods=['POST'])
def calculate_simulation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Inicia cálculo de simulación.
    
    Input: EntryDataV1 (JSON)
    Processing: 10-layer pipeline + visions + lineage
    Output: HTTP 201 + {simulation_id, visions_ready}
    """
    try:
        # Parse request
        body = req.get_json()
        request = EntryDataV1.parse_obj(body)
        
        # Get provider (DI)
        storage_client = get_blob_client()
        provider = ParametrizationProvider.build(storage_client)
        
        # Build context
        builder = SimulationContextBuilder(provider)
        pricing_request = builder.construir(request)
        
        # Execute calculation
        engine = NexaPricingEngine(parametrizacion=provider)
        result = engine.calcular(pricing_request)
        
        # Persist result + lineage (async, best-effort)
        cosmos_client = get_cosmos_client()
        cosmos_client.simulations.create_item({
            'id': result.simulation_id,
            'input': request.dict(),
            'result': result.to_dict(),
            'lineage_hash': hash_lineage(result.lineage_graph),
            'created_at': datetime.utcnow().isoformat(),
            'ttl': 90 * 24 * 3600,  # 90-day expiry
        })
        
        # Response
        return func.HttpResponse(
            json.dumps({
                'simulation_id': result.simulation_id,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'complete',
                'visions_ready': True,
                'version_metadata': result.version_metadata.to_dict(),
            }),
            status_code=201,
            mimetype='application/json'
        )
    
    except Exception as e:
        _logger.exception("[calculate] error: %s", e)
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype='application/json'
        )
```

**Cost Estimate:** 5M calls/month × 500ms avg = $300/month (compute)

**Function 2: RetrieveResults**

```python
@app.route(route='results/{sim_id}/{vision_name}', methods=['GET'])
def retrieve_results(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetch pre-computed vision from Cosmos DB.
    
    Input: simulation_id, vision_name
    Output: JSON vision payload
    """
    sim_id = req.route_params.get('sim_id')
    vision_name = req.route_params.get('vision_name')
    
    cosmos = get_cosmos_client()
    try:
        item = cosmos.simulations.read_item(
            item=sim_id,
            partition_key=sim_id
        )
        
        vision_data = item['result']['visions'].get(vision_name)
        if not vision_data:
            return func.HttpResponse(
                json.dumps({'error': 'Vision not found'}),
                status_code=404
            )
        
        return func.HttpResponse(
            json.dumps(vision_data),
            status_code=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        _logger.exception("[retrieve] error: %s", e)
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500
        )
```

**Cost:** Minimal (mostly DB read)

**Function 3: AuditSimulation**

```python
@app.route(route='audit/{sim_id}', methods=['GET'])
def audit_simulation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetch lineage graph for audit trail.
    
    Input: simulation_id
    Output: LineageGraph JSON
    """
    sim_id = req.route_params.get('sim_id')
    
    storage = get_blob_client()
    lineage_path = f"lineage/{sim_id}/graph.json"
    
    try:
        lineage_blob = storage.get_blob_client(lineage_path).download_blob()
        lineage_data = json.loads(lineage_blob.readall().decode('utf-8'))
        
        return func.HttpResponse(
            json.dumps(lineage_data),
            status_code=200,
            mimetype='application/json'
        )
    except Exception as e:
        _logger.exception("[audit] error: %s", e)
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500
        )
```

**Function 4: ManageParametrization**

```python
@app.route(route='parametrization/versions', methods=['GET', 'POST'])
def manage_parametrization(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET: List active parametrization versions
    POST: Create/activate new version
    """
    if req.method == 'GET':
        cosmos = get_cosmos_client()
        versions = list(cosmos.parametrization.query_items(
            query='SELECT * FROM c ORDER BY c.created_at DESC'
        ))
        return func.HttpResponse(json.dumps(versions), status_code=200)
    
    elif req.method == 'POST':
        body = req.get_json()
        cosmos = get_cosmos_client()
        cosmos.parametrization.create_item({
            'id': str(uuid.uuid4()),
            'version_id': body['version_id'],
            'data': body['data'],
            'hash': hashlib.sha256(json.dumps(body['data']).encode()).hexdigest(),
            'created_at': datetime.utcnow().isoformat(),
            'is_active': body.get('is_active', False),
        })
        return func.HttpResponse(
            json.dumps({'status': 'created'}),
            status_code=201
        )
```

**Cost:** Minimal

**Function 5: CertifiedMode**

```python
@app.route(route='certification/verify', methods=['POST'])
def verify_certificate(req: func.HttpRequest) -> func.HttpResponse:
    """
    Verify ExecutionCertificate (deterministic mode).
    """
    body = req.get_json()
    cert_id = body.get('certificate_id')
    baseline_id = body.get('baseline_id')
    
    cosmos = get_cosmos_client()
    cert = cosmos.certificates.read_item(item=cert_id, partition_key=cert_id)
    
    # Replay input with frozen parametrization
    provider = FrozenParametrizationAdapter.from_version(baseline_id)
    engine = NexaPricingEngine(parametrizacion=provider)
    new_result = engine.calcular(cert['original_request'])
    
    # Compare hashes
    new_hash = hashlib.sha256(json.dumps(new_result.to_dict()).encode()).hexdigest()
    original_hash = cert['result_hash']
    
    return func.HttpResponse(
        json.dumps({
            'certificate_id': cert_id,
            'simulation_id': cert['simulation_id'],
            'valid': new_hash == original_hash,
            'version_metadata': cert['version_metadata'],
        }),
        status_code=200
    )
```

### 3. Azure Cosmos DB (Data)

**Propósito:** Global data store (multi-region, high availability)

**Configuración:**

```
Database: nexa_production

Collections:
  1. simulations
     Partition Key: /simulation_id
     TTL: 90 days (auto-delete old simulations)
     Indexes: simulation_id, created_at
     
  2. parametrization
     Partition Key: /version_id
     TTL: None (keep forever)
     Indexes: version_id, is_active, created_at
     
  3. baselines
     Partition Key: /baseline_version
     TTL: None
     Indexes: baseline_version, created_at
     
  4. certificates
     Partition Key: /certificate_id
     TTL: 365 days (compliance: 1 year audit trail)
     Indexes: certificate_id, simulation_id, issued_at
```

**Regions:** 3 (Primary: East US, Replicas: West Europe, Southeast Asia)
- RTO (Recovery Time Objective): < 5 minutes (automatic failover)
- RPO (Recovery Point Objective): < 1 minute (continuous replication)

**Consistency Model:**
- Simulations: Session consistency (strong locally, eventual globally)
- Parametrization: Strong consistency (critical for reproducibility)
- Certificates: Strong consistency (audit compliance)

**Cost:** ~$500/month for 50 GB/day throughput, auto-scaling

**Example Document: Simulation**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-05-31T14:23:45Z",
  "input": {
    "panel": { "cargo_list": [...], "modelo_cobro": "Mixto" },
    "scenarios": [...]
  },
  "result": {
    "simulation_id": "...",
    "visions": {
      "vision_tarifas": { ... },
      "vision_cost_to_serve": { ... },
      ...
    },
    "lineage_hash": "sha256:..."
  },
  "lineage_hash": "sha256:3a4d5f6e7c8b9a1d2e3f4a5b6c7d8e9f",
  "version_metadata": {
    "engine_version": "engine-v2",
    "parametrization_version": "v2-7",
    "parametrization_hashes": { ... }
  },
  "ttl": 7776000
}
```

### 4. Azure Storage (Persistence)

**Propósito:** Backups, logs, parametrización completa

**Containers:**

```
nexa-storage-prod/
├─ parametrization/
│  ├─ v2-7/
│  │  ├─ manifest.json
│  │  ├─ hr.json (full snapshot)
│  │  ├─ gn.json
│  │  └─ op.json
│  ├─ baselines/
│  │  └─ baseline-v2-7/ (frozen version)
│  └─ versions.json (version registry)
├─ lineage/
│  └─ {sim_id}/
│     └─ graph.json (full trace, 10-1000 KB per simulation)
├─ backups/
│  └─ cosmos-db-daily/ (Cosmos automatic backups)
└─ logs/
   ├─ application/ (30-day retention, then archive)
   └─ audit/ (365-day retention, compliance)
```

**Cost:** ~$50/month for 100 GB storage

### 5. Azure Key Vault (Secrets)

**Propósito:** Secure storage para conexión strings, API keys, encryption keys

**Secrets:**

```
Keys:
  - cosmos-db-connection-string
  - storage-account-key
  - oauth-client-secret
  - api-key-signing-key
  
Access:
  - Functions authenticate via Managed Identity (no secrets in code)
  - Audit: all access logged
```

**Cost:** ~$10/month (per-secret fee)

### 6. Azure Monitor + Application Insights

**Propósito:** Observabilidad (metrics, traces, alertas)

**Métricas:**

```
Request Flow:
  - request_count (by endpoint, by status code)
  - latency (p50, p95, p99)
  - error_rate (5xx, 4xx, timeouts)
  
Calculation Flow:
  - execution_time_ms (10-layer pipeline)
  - parametrization_load_time
  - vision_build_time
  - lineage_capture_time
  
Database:
  - cosmos_request_units (RU consumption)
  - cosmos_latency
  - cosmos_throttling (if any)
  
Cost:
  - ingestion: ~$100/month for 1 GB/day logs
```

**Alertas:**

```
Critical (PagerDuty):
  - error_rate > 5%
  - p99_latency > 5s
  - cosmos_throttling active
  - function_timeout > 0 per hour
  
Warning:
  - error_rate > 1%
  - p99_latency > 2s
  - cost anomaly (2x historical average)
```

**Dashboards:**

- Real-time operations (request rate, latency, errors)
- Calculation performance (per-layer times, parallelization efficiency)
- Cost breakdown (compute, storage, data transfer)
- Audit trail (who called what, when, from where)

---

## SECTION 10.3: Flujo de Datos & Scaling

### Request Flow Completo

```
1. Client sends request
   POST /api/v1/simulate/calculate
   Authorization: Bearer {token}
   X-Client-ID: client-acme-corp
   Content-Type: application/json
   
   {
     "panel": { ... },
     "scenarios": [ ... ]
   }

2. APIM intercepts
   ├─ Validate OAuth token (Azure AD)
   ├─ Rate limit check (1000 req/min per client)
   ├─ Route to backend: CalculateSimulation function
   └─ Log request (Monitor)

3. CalculateSimulation function starts
   ├─ Deserialize EntryDataV1 (schema validation)
   ├─ Load active ParametrizationProvider
   ├─ Initialize Cosmos DB + Storage connections
   └─ Timeout: 600 seconds

4. Python engine executes (10-layer pipeline)
   ├─ Layer 2-5 (PARALLEL, 4 threads):
   │  ├─ NominaCalculator
   │  ├─ NoPayrollCalculator
   │  ├─ CadenaBCalculator
   │  └─ CadenaCCalculator
   ├─ Layers 6-9 (SEQUENTIAL):
   │  ├─ CostosTotalesCalculator
   │  ├─ CostosFinancierosCalculator
   │  ├─ PyGCalculator
   │  └─ KPIsCalculator
   └─ Post-pipeline Visions:
      ├─ VisionTarifasCalculator
      ├─ CostToServeCalculator
      ├─ RiesgoCalculator
      └─ Vision builders (PyG, Datasets, Imprimible)

5. Lineage capture
   ├─ LineageBuilder.build() → immutable LineageGraph
   ├─ Compute hashes (request, result, lineage)
   └─ Attach VersionMetadata snapshot

6. Persistence (async, parallel)
   ├─ Write simulations/{sim_id} to Cosmos DB
   │  └─ TTL: 90 days (auto-delete)
   ├─ Write lineage/{sim_id}/graph.json to Storage
   │  └─ Best-effort (failure doesn't block response)
   └─ Update monitoring (AppInsights)

7. HTTP Response
   ├─ Status: 201 Created
   ├─ Headers: Location: /api/v1/simulate/{sim_id}
   └─ Body: {
       simulation_id: "550e8400-...",
       created_at: "2026-05-31T14:23:45Z",
       status: "complete",
       visions_ready: true,
       version_metadata: { ... }
     }

8. Client polls visions
   GET /api/v1/simulate/{sim_id}/results/vision_tarifas
   ├─ APIM routes to RetrieveResults function
   ├─ Cosmos DB lookup (cached, < 50ms)
   ├─ Serialize VisionTarifasV1
   └─ Return HTTP 200 + payload
```

### Scaling Characteristics

**Horizontal Scaling (Request Load):**

```
Request Rate:     Functions Created   Memory Used   Cost
10 req/s          1                   100 MB        ~$1/month
100 req/s         10                  1 GB          ~$10/month
1000 req/s        100                 10 GB         ~$100/month
10000 req/s       1000                100 GB        ~$1000/month

Auto-scaling rules:
  - min_instances: 1 (warm, ready for instant response)
  - max_instances: 1000 (hard limit)
  - scale_out_threshold: avg_cpu > 70% OR queue > 5 items
  - scale_in_threshold: avg_cpu < 20% (after 5 min idle)
```

**Vertical Scaling (Single Request):**

```
Calculation Time   Memory Needed   Timeout   Comment
Contract: 120mo    400-600 MB      600s      Typical case
Contract: 240mo    800 MB          600s      Large backfill
Lineage deep       200 MB extra    600s      Tracing overhead
```

**Database Scaling:**

```
Writes per Second   Cosmos DB RU/s   Monthly Cost
100                 500-1000         ~$200
1000                5000-10000       ~$500
10000               50000            ~$5000

Read caching:
  - Hot simulations (< 1 day): in-memory (Redis, optional)
  - Warm simulations (1-30 days): Cosmos DB read cache
  - Cold simulations (> 30 days): Storage Blobs (archive)
```

### Parallelization Strategy

**Current:** Layers 2–5 parallelizable (4 threads)

```python
class NexaPricingEngine:
    def calcular(self, request: PricingRequest) -> PricingResult:
        with ThreadPoolExecutor(max_workers=4) as pool:
            # Parallel: layers 2-5
            f2 = pool.submit(
                NominaCalculator().calcular, request, self._provider
            )
            f3 = pool.submit(
                NoPayrollCalculator().calcular, request, self._provider
            )
            f4 = pool.submit(
                CadenaBCalculator().calcular, request, self._provider
            )
            f5 = pool.submit(
                CadenaCCalculator().calcular, request, self._provider
            )
            
            result_layer2 = f2.result(timeout=60)
            result_layer3 = f3.result(timeout=60)
            result_layer4 = f4.result(timeout=60)
            result_layer5 = f5.result(timeout=60)
        
        # Sequential: layers 6-10
        result_layer6 = CostosTotalesCalculator().calcular(
            request, self._provider
        )
        # ... etc
        
        return PricingResult(...)
```

**In Azure Functions:** Multi-threaded CPU-bound code runs in single thread by default. Use async to improve concurrency.

```python
# Better: async parallelization
async def calculate_simulation_async(req: func.HttpRequest):
    # Layers 2-5 in parallel
    tasks = [
        asyncio.to_thread(NominaCalculator().calcular, request, provider),
        asyncio.to_thread(NoPayrollCalculator().calcular, request, provider),
        asyncio.to_thread(CadenaBCalculator().calcular, request, provider),
        asyncio.to_thread(CadenaCCalculator().calcular, request, provider),
    ]
    results = await asyncio.gather(*tasks)
    
    # Sequential: layers 6-10
    # ...
```

---

## SECTION 10.4: Seguridad & Cumplimiento

### Autenticación

**OAuth 2.0 via Azure AD:**

```
Client request:
  Authorization: Bearer {access_token}
  X-Client-ID: client-acme-corp
  
APIM policy:
  <validate-jwt
      token-value="@(context.Request.Headers.GetValueOrDefault("Authorization").Split(' ').Last())"
      failed-validation-httpcode="401"
      failed-validation-error-message="Unauthorized"
  >
      <audience>api://nexa-simulator</audience>
      <issuer>https://login.microsoftonline.com/{tenant-id}/v2.0</issuer>
  </validate-jwt>
```

### Autorización

**RBAC en APIM:**

```
Roles:
  - Viewer: GET /results/* (read-only)
  - Simulator: POST /calculate, GET /results, GET /audit
  - Admin: All endpoints + /parametrization/versions management
  
Policy:
  <choose>
      <when condition="@(context.User.Groups.Contains("Viewer"))">
          <set-method>GET</set-method>
      </when>
      <when condition="@(context.User.Groups.Contains("Simulator"))">
          <set-method>GET,POST</set-method>
      </when>
      <when condition="@(context.User.Groups.Contains("Admin"))">
          <!-- Allow all -->
      </when>
  </choose>
```

### Protección de Datos

**At Rest:**
- Cosmos DB: AES-256 encryption (Microsoft-managed keys)
- Storage: AES-256 encryption
- Key Vault: HSM-backed (FIPS 140-2 Level 2)

**In Transit:**
- TLS 1.2+ (APIM ↔ Client, Function ↔ Cosmos, Function ↔ Storage)
- Mutual TLS optional (client certificate auth)

**Secrets Management:**
- No secrets in code or config files
- Functions authenticate via Managed Identity
- Key Vault audit logs (all access logged)

### Cumplimiento Normativo

**SOC 2 Type II:**
- Azure data centers certified
- Encryption, access controls, audit trails
- Regular third-party audits

**GDPR:**
- Data residency: Primary region (EU or US as applicable)
- Right to deletion: TTL on simulations (90 days)
- Data portability: export via GET /results/*

**Financial Audit:**
- ExecutionCertificate for reproducibility
- LineageGraph for traceability
- Audit logs in SIEM (optional Azure Sentinel integration)

---

## SECTION 10.5: Estimación de Costos

### Monthly Production Estimate

| Component | Volume | Unit Cost | Monthly |
|-----------|--------|-----------|---------|
| **APIM** | 5M requests | $150 flat rate | $150 |
| **Functions (Compute)** | 5M × 500ms avg | $0.000000167/GB-s | $417 |
| **Functions (Requests)** | 5M | $0.20 per 1M | $1 |
| **Cosmos DB** | 50 GB/day + 100K RU/s | Variable | $500 |
| **Storage (Blobs)** | 100 GB | $0.018/GB | $50 |
| **Key Vault** | 10 secrets | $1/month each | $10 |
| **Monitor/AppInsights** | 1 GB/day logs | $2.46/GB | $74 |
| **Data Transfer** | 10 GB egress/month | $0.09/GB | $9 |
| **Reserved Instances** (optional) | Cosmos DB | -30% discount | -$150 |
| **Spot Instances** (optional) | Functions | -60% discount | -$200 |
| | | **TOTAL** | **~$861/month** |

**With Discounts:** ~$600–700/month (reserved instances + spot)

### Dev/Staging Environment

~10% of production = $60–70/month

### Cost Optimization Strategies

1. **Reserved Instances:** Cosmos DB (30% discount for 1-year commitment)
2. **Spot Functions:** Use low-priority compute (60% discount, interruptible)
3. **Archive Storage:** Move lineage > 90 days to blob archive ($0.004/GB)
4. **Cosmos Throughput:** Use auto-scale (cheaper for variable load)
5. **Function Right-sizing:** Monitor memory consumption, use only what needed

---

## SECTION 10.6: Ruta de Migración

### Phase 1: Setup Infraestructura (Month 1)

**Tareas:**

```
Week 1-2:
  ├─ Provision Azure resource group + subscription
  ├─ Deploy APIM instance (Standard tier)
  ├─ Create Cosmos DB account (multi-region: East US, West Europe)
  ├─ Create Storage account + Key Vault
  └─ Setup Application Insights

Week 2-3:
  ├─ Migrate ParametrizationProvider to use Azure Storage
  ├─ Create Python Function app (Linux, Python 3.9)
  ├─ Deploy CalculateSimulation function
  └─ Setup managed identity (Function → Cosmos, Storage)

Week 3-4:
  ├─ Parallel run: current monolith + Azure (canary)
  ├─ Compare results (tolerance: 0.01%)
  ├─ Setup monitoring + alerts
  └─ Load testing (1000 req/s spike)
```

**Deliverables:**
- APIM endpoint live (gateway to single function)
- Cosmos DB with simulations collection
- Azure Monitor dashboard
- Runbook for on-call

### Phase 2: Migrar Endpoints Restantes (Month 2)

**Tareas:**

```
Week 1-2:
  ├─ Deploy RetrieveResults function
  ├─ Deploy AuditSimulation function
  ├─ Wire lineage capture (async to Storage)
  └─ Test vision endpoints

Week 2-3:
  ├─ Deploy ManageParametrization function
  ├─ Version control for parametrization
  ├─ Implement drift detection
  └─ Test parametrization CRUD

Week 3-4:
  ├─ Deploy CertifiedMode function
  ├─ Implement ExecutionCertificate
  ├─ Test reproducibility
  └─ Decommission old parametrization storage
```

**Deliverables:**
- All 5 functions live (calculate, retrieve, audit, manage, certification)
- Cosmos DB full schema (5 collections)
- Lineage capture + query API

### Phase 3: Observabilidad & Optimización (Month 3)

**Tareas:**

```
Week 1-2:
  ├─ Wire Application Insights (traces, metrics, logs)
  ├─ Setup PagerDuty alerts
  ├─ Create runbooks (escalation, troubleshooting)
  └─ Performance profiling (per-layer timing)

Week 2-3:
  ├─ Tune Function memory allocation
  ├─ Optimize Cosmos DB indexes
  ├─ Implement caching (Redis optional)
  └─ Cost analysis + optimization

Week 3-4:
  ├─ Disaster recovery drill (failover test)
  ├─ Load testing (sustained 1000 req/s)
  ├─ Penetration testing (security scan)
  └─ Documentation complete
```

**Deliverables:**
- Observability stack operational
- Cost < $1000/month
- RTO < 5 min, RPO < 1 min validated

### Phase 4: Production Cutover (Month 4)

**Tareas:**

```
Week 1-2:
  ├─ Pre-cutover readiness review
  ├─ Customer notification + training
  ├─ Parallel run: final validation
  └─ DNS migration plan (CNAME to APIM)

Week 2-3:
  ├─ Scheduled maintenance window (24h)
  ├─ DNS cutover (old monolith → Azure)
  ├─ Monitor error rates + latency
  ├─ Rollback plan armed (activate old monolith if needed)
  └─ 24/7 on-call support

Week 3-4:
  ├─ Post-cutover validation (48h)
  ├─ Archive final backups from old system
  ├─ Decommission on-prem infrastructure
  └─ Cost analysis + optimization review
```

**Deliverables:**
- 100% traffic on Azure
- Old system archived
- Post-cutover runbook

---

## SECTION 10.7: Alta Disponibilidad & Disaster Recovery

### HA Architecture

**Multi-Region Replication:**

```
Primary Region (East US):
  ├─ APIM (active-active)
  ├─ Functions (auto-scaling)
  ├─ Cosmos DB (write region)
  └─ Storage (geo-redundant)

Replica Region 1 (West Europe):
  ├─ APIM (active-active, latency-based routing)
  ├─ Functions (read-only via Traffic Manager)
  ├─ Cosmos DB (read region, RTO < 5 min)
  └─ Storage (geo-redundant)

Replica Region 2 (Southeast Asia):
  ├─ APIM (active-active)
  ├─ Functions (read-only)
  ├─ Cosmos DB (read region)
  └─ Storage (geo-redundant)
```

**Failover Mechanics:**

```
Scenario 1: East US region becomes unavailable
  ├─ Cosmos DB auto-failover to West Europe (< 5 min)
  ├─ APIM health probe detects failure (health check every 30s)
  ├─ Traffic shifted to West Europe + Southeast Asia
  ├─ Existing connections re-route (TCP graceful)
  └─ Alert sent to on-call team (informational)

Scenario 2: Cosmos DB write throttling
  ├─ Monitor detects RU consumption > 80%
  ├─ Auto-scale increases RU/s (pre-configured)
  ├─ Functions queued (best-effort, no timeout)
  ├─ Alert sent (warning, not critical)
  └─ Manual intervention if sustained

Scenario 3: Function timeout
  ├─ Function exceeds 600s (should be rare)
  ├─ APIM returns 504 Gateway Timeout
  ├─ Client retries (idempotent if simulation_id sent)
  ├─ Alert sent (critical)
  └─ On-call investigates (likely parametrization issue)
```

### RTO & RPO

**Recovery Time Objective (RTO):**

```
Tier 1 (Minutes):
  - Function instance failure: 0s (auto-restart)
  - Cosmos DB read region failure: 5s (auto-failover)
  - Storage account failure: 30s (geo-redundant read)
  
Tier 2 (Seconds):
  - Cosmos DB write region failure: 300s (auto-failover)
  - APIM failure: 60s (DNS update)
  
Worst Case: 300s (5 minutes)
```

**Recovery Point Objective (RPO):**

```
Tier 1 (Real-time):
  - Function stateless (no state to recover)
  - Cosmos DB continuous replication (< 1s lag)
  
Tier 2 (Minutes):
  - Storage geo-redundant backup (< 15 min lag)
  - Application Insights logs (< 5 min lag)
  
Worst Case: < 1 minute
```

### Backup & Restore

**Cosmos DB:**
- Automatic continuous backups (30-day retention)
- Point-in-time restore (any point in last 30 days)
- Manual snapshots (optional, for critical baselines)

**Storage:**
- Geo-redundant replication (automatic)
- 90-day retention for simulation results (TTL)
- Archive tier for > 90-day data (compliance)

**Lineage Graphs:**
- Best-effort (stored in both Cosmos DB + Storage)
- Not critical (can be reconstructed from inputs if needed)

**Restore Procedure:**

```
Scenario: Accidental data deletion
  
1. Detect issue (customer report or monitoring)
2. Identify last good backup (Cosmos DB point-in-time)
3. Create new account from backup (< 15 min)
4. Validate data integrity (spot checks)
5. Promote to production (DNS CNAME update)
6. Verify no ongoing corruption
7. Archive corrupted database (forensics)

RTO: ~30–60 minutes
RPO: < 1 minute
```

---

## Summary: Azure Architecture Benefits

| Dimension | On-Premises | Azure |
|-----------|------------|-------|
| **Scalability** | Manual (add hardware) | Automatic (0-1000s instances) |
| **Availability** | Single region (99.9%) | Multi-region (99.95%+) |
| **Cost** | Fixed (servers, cooling, staff) | Variable (pay-per-use) |
| **Security** | Manual updates | Microsoft patched |
| **Disaster Recovery** | Manual backup/restore (hours) | Automatic failover (minutes) |
| **Observability** | Third-party tools (Datadog, etc.) | Native Monitor + AppInsights |
| **Time to Market** | Weeks (procure hardware) | Days (provision resources) |

