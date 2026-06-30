# Azure Target Architecture: Technical Reference

**Última actualización:** 31 de mayo de 2026  
**Versión:** 1.0  
**Estado:** Propuesta

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Conceptual](#arquitectura-conceptual)
3. [Componentes Detallados](#componentes-detallados)
4. [Flujo de Datos](#flujo-de-datos)
5. [Configuración de Redes](#configuración-de-redes)
6. [Observabilidad & Monitoreo](#observabilidad--monitoreo)
7. [Seguridad & Cumplimiento](#seguridad--cumplimiento)
8. [Estrategia de Despliegue](#estrategia-de-despliegue)
9. [Estimación de Costos](#estimación-de-costos)
10. [Apéndices](#apéndices)

---

## Resumen Ejecutivo

### Objetivo Arquitectónico

Transformar NEXA de un monolito Python on-premises a una solución **serverless, cloud-native** en Azure que:

- **Escale automáticamente** (0–1000s de instancias)
- **Garantice reproducibilidad** (versioning + certificación)
- **Proporcione trazabilidad completa** (lineage graphs)
- **Reduzca costos** operacionales (pay-per-use)
- **Mejore disponibilidad** (multi-región, auto-failover)

### Estado Actual

```
monolith.py (on-premises)
  ├─ NexaPricingEngine (10-layer pipeline)
  ├─ parametrization/ (JSON local)
  ├─ results/ (files or local DB)
  └─ No auto-scaling, sin redundancia
```

### Estado Objetivo

```
Azure Cloud (multi-región)
  ├─ APIM (gateway)
  ├─ Functions (stateless compute)
  ├─ Cosmos DB (global data)
  ├─ Storage (backups + logs)
  ├─ Key Vault (secrets)
  └─ Monitor + AppInsights (observability)
```

### Beneficios Esperados

| KPI | On-Premises | Azure |
|-----|------------|-------|
| **Escalabilidad** | Manual | Automática |
| **RTO** | 4–8 horas | < 5 minutos |
| **Costo variable** | $0 (fijo) | $600–1000/mes (variable) |
| **Time-to-Market** | Semanas | Días |
| **Compliance audit trail** | Manual | Automático |

---

## Arquitectura Conceptual

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────┐
│ Client Layer (HTTPS)                                        │
│ - Web UI (React)                                            │
│ - Mobile Apps                                               │
│ - Third-party integrations                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ API Gateway Layer (APIM)                                    │
│ - OAuth 2.0 auth (Azure AD)                                │
│ - Rate limiting (1000 req/min per client)                  │
│ - API versioning (v1 only, frozen)                         │
│ - Request/response transformation                          │
└────────────────┬────────────────────────────────────────────┘
                 │
     ┌───────────┼───────────────────────┐
     │           │                       │
┌────▼────┐ ┌───▼───┐ ┌────────────┐ ┌─▼──────────┐
│Calculate│ │Audit  │ │Parametrize│ │Certify     │
│Simulation       │              │
│Functions       │              │
└────┬────┘ └───┬───┘ └────────────┘ └─┬──────────┘
     │           │                      │
     └───────────┼──────────────────────┘
                 │
     ┌───────────▼───────────────────────┐
     │  Data Layer (Cosmos DB)            │
     │  - Simulations (results)           │
     │  - Parametrization (versions)      │
     │  - Baselines (certified snapshots) │
     │  - Certificates (audit records)    │
     └───────┬───────────────────────────┘
             │
    ┌────────┴─────────┬─────────────┐
    │                  │             │
┌───▼──────┐  ┌────────▼──────┐  ┌──▼──────┐
│ Storage  │  │  Key Vault    │  │ Monitor  │
│ (backups)│  │  (secrets)    │  │(AppInsig)│
└──────────┘  └───────────────┘  └──────────┘
```

### Flujo de Solicitud Típico

```
User Input (JSON)
    ↓
POST /api/v1/simulate/calculate
    ↓
APIM [auth, rate limit, validation]
    ↓
CalculateSimulation Function
    ├─ Deserialize EntryDataV1
    ├─ Load parametrization (Cosmos DB)
    ├─ Run 10-layer pipeline
    ├─ Build visions + lineage
    └─ Persist result to Cosmos DB
    ↓
HTTP 201 Created + {simulation_id}
    ↓
GET /api/v1/simulate/{sim_id}/results/*
    ↓
APIM [cache/route]
    ↓
RetrieveResults Function
    ├─ Query Cosmos DB (vision data)
    └─ Serialize to DTO
    ↓
HTTP 200 OK + {vision_tarifas, ...}
```

---

## Componentes Detallados

### 1. Azure API Management (APIM)

**Tier:** Standard  
**Regions:** 3 (East US, West Europe, Southeast Asia)  
**SLA:** 99.95%

#### Configuración

**Rate Limiting Policy:**

```xml
<policies>
  <inbound>
    <rate-limit-by-key
        calls="1000"
        renewal-period="60"
        counter-key="@(context.Request.Headers.GetValueOrDefault("X-Client-ID", "anonymous"))"
        increment-by="1"
        retry-after-header-name="Retry-After"
    />
  </inbound>
</policies>
```

**Authentication Policy:**

```xml
<validate-jwt
    token-value="@(context.Request.Headers.GetValueOrDefault("Authorization").Split(' ').Last())"
    failed-validation-httpcode="401"
    failed-validation-error-message="Unauthorized"
>
    <openid-config url="https://login.microsoftonline.com/{tenant-id}/.well-known/openid-configuration" />
    <audiences>
        <audience>api://nexa-simulator</audience>
    </audiences>
    <issuers>
        <issuer>https://login.microsoftonline.com/{tenant-id}/v2.0</issuer>
    </issuers>
</validate-jwt>
```

**Routing Policy:**

```xml
<set-backend-service
    base-url="https://{function-app-name}.azurewebsites.net"
    manage-header="true"
/>
```

#### API Definitions

| Endpoint | Method | Backend | Timeout |
|----------|--------|---------|---------|
| /api/v1/simulate/calculate | POST | CalculateSimulation | 600s |
| /api/v1/simulate/{id}/results/* | GET | RetrieveResults | 30s |
| /api/v1/simulate/{id}/audit | GET | AuditSimulation | 30s |
| /api/v1/parametrization/versions | GET | ListVersions | 30s |
| /api/v1/parametrization/versions | POST | CreateVersion | 120s |
| /api/v1/certification/verify | POST | VerifyCertificate | 600s |

### 2. Azure Functions

**Runtime:** Python 3.9+  
**Hosting:** Linux Consumption Plan  
**Concurrency:** Unlimited (auto-scale)

#### Function 1: CalculateSimulation

```python
@app.route(route='calculate', methods=['POST'])
@app.function_name('CalculateSimulation')
async def calculate_simulation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Calcula simulación complete (10-layer pipeline + visions).
    
    HTTP Input:  POST /api/v1/simulate/calculate
                 Content-Type: application/json
                 Body: { "panel": {...}, "scenarios": [...] }
    
    HTTP Output: 201 Created
                 { "simulation_id": "...", "status": "complete", ... }
    
    Processing:
      1. Parse & validate request
      2. Load parametrization
      3. Run engine (10 layers, layers 2-5 parallel)
      4. Build visions + lineage
      5. Persist to Cosmos DB
      6. Return response
    
    Timeout: 600 seconds
    Memory: 1 GB
    """
```

**Performance Characteristics:**

```
Input Size           Processing Time   Memory
(contract months)    (est.)            (est.)
─────────────────────────────────────────────
120                  1.2s              250 MB
240                  2.4s              400 MB
With lineage trace   +500ms            +150 MB
```

#### Function 2: RetrieveResults

```python
@app.route(route='results/{sim_id}/{vision_name}', methods=['GET'])
@app.function_name('RetrieveResults')
async def retrieve_results(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetch pre-computed vision from Cosmos DB.
    
    HTTP Input:  GET /api/v1/simulate/{sim_id}/results/{vision_name}
    HTTP Output: 200 OK + vision JSON
    
    Vision Names:
      - vision_tarifas
      - vision_cost_to_serve
      - vision_riesgo
      - vision_pyg
      - vision_datasets
      - vision_imprimible
    
    Timeout: 30 seconds
    Memory: 256 MB
    """
```

#### Function 3: AuditSimulation

```python
@app.function_name('AuditSimulation')
async def audit_simulation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetch lineage graph (calculation trace) from Storage.
    
    HTTP Input:  GET /api/v1/simulate/{sim_id}/audit
    HTTP Output: 200 OK + LineageGraph JSON
    
    Lineage contains:
      - All calculation nodes (10 layers + visions)
      - Input sources (request, parametrization, Excel)
      - Formula descriptions
      - Version metadata
    
    Timeout: 30 seconds
    Memory: 512 MB
    """
```

#### Function 4: ListVersions

```python
@app.function_name('ListParametrizationVersions')
async def list_versions(req: func.HttpRequest) -> func.HttpResponse:
    """
    List active parametrization versions.
    
    HTTP Input:  GET /api/v1/parametrization/versions
                 Query: ?module=hr (optional filter)
    
    HTTP Output: 200 OK + [
                   {
                     "version_id": "v2-7",
                     "module": "hr",
                     "is_active": true,
                     "created_at": "2026-05-31T...",
                     "hash": "sha256:..."
                   }
                 ]
    
    Timeout: 30 seconds
    Memory: 256 MB
    """
```

#### Function 5: VerifyCertificate

```python
@app.function_name('VerifyCertificate')
async def verify_certificate(req: func.HttpRequest) -> func.HttpResponse:
    """
    Verify ExecutionCertificate (deterministic mode).
    
    HTTP Input:  POST /api/v1/certification/verify
                 Body: {
                   "certificate_id": "...",
                   "baseline_id": "v2-7"  # optional
                 }
    
    HTTP Output: 200 OK + {
                   "certificate_id": "...",
                   "simulation_id": "...",
                   "valid": true,
                   "baseline_matched": true
                 }
    
    Processing:
      1. Load certificate from Cosmos DB
      2. Load baseline parametrization (frozen)
      3. Replay input with frozen params
      4. Compare output hashes
      5. Return validation result
    
    Timeout: 600 seconds
    Memory: 1 GB
    """
```

### 3. Azure Cosmos DB

**Tier:** Standard (provisioned throughput, auto-scale)  
**Regions:** 3 (East US primary, West Europe, Southeast Asia)  
**Consistency:** Multi-region (eventual, with strong for critical data)

#### Databases & Collections

**Database: nexa_production**

```
Collections:

1. simulations
   Partition Key: /simulation_id
   TTL: 90 days (auto-expire old results)
   Document Size: 100 KB — 10 MB
   
   Example Document:
   {
     "id": "550e8400-...",
     "simulation_id": "550e8400-...",
     "created_at": "2026-05-31T14:23:45Z",
     "input": { ... },  // Full request
     "result": { ... }, // All visions
     "lineage_hash": "sha256:...",
     "version_metadata": { ... },
     "ttl": 7776000
   }

2. parametrization
   Partition Key: /version_id
   TTL: None (permanent)
   Document Size: 1–10 MB
   
   Example Document:
   {
     "id": "v2-7-hr",
     "version_id": "v2-7",
     "module": "hr",
     "data": { "roles": [...], "salarios": [...] },
     "hash": "sha256:...",
     "created_at": "2026-05-31T...",
     "is_active": true
   }

3. baselines
   Partition Key: /baseline_version
   TTL: None (permanent)
   Document Size: 5–20 MB
   
   Example Document:
   {
     "id": "baseline-v2-7",
     "baseline_version": "v2-7",
     "version_metadata": { ... },
     "parametrization_hashes": { "hr": "...", "gn": "...", "op": "..." },
     "created_at": "2026-05-31T...",
     "is_active": true
   }

4. certificates
   Partition Key: /certificate_id
   TTL: 365 days (compliance: 1-year audit trail)
   Document Size: 10–100 KB
   
   Example Document:
   {
     "id": "cert-550e8400",
     "certificate_id": "cert-550e8400",
     "simulation_id": "550e8400-...",
     "issued_at": "2026-05-31T14:23:45Z",
     "version_metadata": { ... },
     "request_hash": "sha256:...",
     "result_hash": "sha256:...",
     "lineage_hash": "sha256:...",
     "validation_results": { "hr": "pass", "gn": "pass", ... },
     "ttl": 31536000
   }

5. audit_logs
   Partition Key: /simulation_id
   TTL: 365 days
   Document Size: 1–10 KB
   
   Example Document:
   {
     "id": "audit-550e8400-001",
     "simulation_id": "550e8400-...",
     "event": "SIMULATION_STARTED",
     "user_id": "user123",
     "timestamp": "2026-05-31T14:23:45Z",
     "details": { "engine_version": "engine-v2", ... },
     "ttl": 31536000
   }
```

#### Indexing Strategy

```json
{
  "indexingPolicy": {
    "indexingMode": "consistent",
    "automatic": true,
    "includedPaths": [
      {
        "path": "/simulation_id/?",
        "indexes": [
          {
            "kind": "Hash",
            "dataType": "String",
            "precision": -1
          }
        ]
      },
      {
        "path": "/created_at/?",
        "indexes": [
          {
            "kind": "Range",
            "dataType": "String",
            "precision": -1
          }
        ]
      },
      {
        "path": "/is_active/?",
        "indexes": [
          {
            "kind": "Hash",
            "dataType": "Boolean"
          }
        ]
      }
    ],
    "excludedPaths": [
      {
        "path": "/data/*"
      }
    ]
  }
}
```

### 4. Azure Storage

**Tier:** Standard (geo-redundant)  
**Containers:**

```
nexa-production/
├─ parametrization/
│  ├─ v2-7/
│  │  ├─ manifest.json (metadata)
│  │  ├─ hr.json (role, salary data)
│  │  ├─ gn.json (general configs)
│  │  └─ op.json (operational rules)
│  ├─ baselines/
│  │  └─ baseline-v2-7/ (frozen snapshot)
│  └─ versions.json (registry)
├─ lineage/
│  └─ {sim_id}/
│     └─ graph.json (10-1000 KB per simulation)
├─ backups/
│  ├─ cosmos-daily/ (daily snapshots)
│  └─ compliance/ (regulatory backups)
└─ logs/
   ├─ application/ (30-day retention)
   └─ audit/ (365-day retention, archive tier)
```

### 5. Azure Key Vault

**Tier:** Standard  
**Purpose:** Centralized secrets management

#### Secrets

```
secrets/
  ├─ cosmos-db-connection-string
  ├─ storage-account-key
  ├─ oauth-client-secret
  ├─ api-key-signing-key
  └─ database-encryption-key
```

#### Access Policies

```
Managed Identities:
  ├─ CalculateSimulation function
  ├─ RetrieveResults function
  ├─ AuditSimulation function
  └─ Utilities (backup, cleanup)

Access Level:
  ├─ Get (read secret)
  └─ List (enumerate secret versions)
```

### 6. Azure Monitor + Application Insights

**Purpose:** Observability (metrics, logs, traces, alerts)

#### Logs Collected

```
Application Logs:
  ├─ Request start/end (APIM)
  ├─ Calculation stages (Engine)
  ├─ Database operations (Cosmos)
  ├─ Error messages (stack traces)
  └─ Performance metrics (latency, throughput)

System Logs:
  ├─ Function runtime (cold start, memory, CPU)
  ├─ Database throttling (RU consumption)
  ├─ Storage access (blob operations)
  └─ Network events (ingress/egress)

Audit Logs:
  ├─ API calls (who, what, when)
  ├─ Authentication events
  ├─ Authorization decisions
  └─ Data access (compliance)
```

#### KPI Dashboards

```
Dashboard 1: Real-time Operations
  ├─ Request count (rolling 1 hour)
  ├─ Error rate (% of 5xx, 4xx)
  ├─ P50, P95, P99 latency (milliseconds)
  ├─ Active connections (Functions)
  └─ Cosmos DB RU consumption (RU/sec)

Dashboard 2: Calculation Performance
  ├─ Layer-by-layer execution time
  ├─ Parallelization efficiency (layers 2-5)
  ├─ Vision build time
  ├─ Lineage capture overhead
  └─ Memory usage per request

Dashboard 3: Data & Storage
  ├─ Cosmos DB storage size (GB)
  ├─ Document count (simulations, parametrization)
  ├─ Backup status (successful/failed)
  └─ Archive tier usage (compliance)

Dashboard 4: Costs
  ├─ Compute cost (Functions)
  ├─ Data cost (Cosmos DB RU, Storage)
  ├─ Egress cost (data transfer)
  └─ Total monthly cost
```

#### Alerting Rules

**Critical (Page on-call):**

```
1. Error Rate > 5% (5-min window)
2. P99 Latency > 5 seconds (10-min window)
3. Cosmos DB Throttling Active (any duration)
4. Function Timeout > 0/hour (each occurrence)
5. Storage Account Unavailable (any duration)
```

**Warning (Slack notification):**

```
1. Error Rate > 1% (5-min window)
2. P99 Latency > 2 seconds (10-min window)
3. Cost Anomaly (2x historical 24h average)
4. Cosmos DB RU > 80% capacity (5-min window)
5. Function Cold Start > 5 seconds (rolling 1 hour)
```

---

## Flujo de Datos

### Simulación Completa (Sunny Path)

```
t=0s     : Cliente envía POST /api/v1/simulate/calculate
t=0.1s   : APIM: validar token OAuth, rate limit check
t=0.2s   : APIM: routear a CalculateSimulation function
t=0.3s   : Function: inicializar (cold start si no warm)
t=0.5s   : Function: cargar parametrización de Cosmos DB
t=0.7s   : Function: deserializar EntryDataV1, construir PricingRequest
t=1s     : Engine: ejecutar Layer 2 (NominaCalculator)
t=1.2s   : Engine: ejecutar Layers 3-5 en paralelo (4 threads)
t=2s     : Engine: ejecutar Layers 6-9 secuencialmente
t=2.5s   : Engine: construir visions (6 vision builders, independientes)
t=3s     : Engine: construir LineageGraph (trace acumulado)
t=3.2s   : Function: persistir resultado a Cosmos DB (async)
t=3.3s   : Function: persistir lineage a Storage (async, best-effort)
t=3.5s   : Function: retornar HTTP 201 Created

Cliente recibe {simulation_id, status: "complete"}

t=5s     : Cliente envía GET /api/v1/simulate/{sim_id}/results/vision_tarifas
t=5.1s   : APIM: routear a RetrieveResults function
t=5.2s   : Function: query Cosmos DB (cached < 50ms)
t=5.3s   : Function: retornar HTTP 200 OK + vision JSON

Total latency: 3.5s (calculate) + 0.3s (retrieve) = 3.8s
```

### Escenario de Error (Rainy Path)

```
t=0s     : Cliente envía POST /api/v1/simulate/calculate
t=0.1s   : APIM: validar token OAuth → ERROR (invalid token)
t=0.1s   : APIM: retornar HTTP 401 Unauthorized

O

t=0s     : Cliente envía POST /api/v1/simulate/calculate
t=0.5s   : Function: cargar parametrización de Cosmos DB → TIMEOUT
t=0.5s   : Function: retornar HTTP 504 Gateway Timeout
          (AppInsights: error logged, alert triggered)

O

t=0s     : Cliente envía POST /api/v1/simulate/calculate
t=2s     : Engine: ejecutar cálculo
t=5m     : Engine: supera timeout de 600s → TIMEOUT
t=5m     : Function: retornar HTTP 504 Gateway Timeout
t=5m     : Monitor: alerta crítica (function timeout)
t=5m+   : On-call investigates (probablemente issue de parametrización)
```

---

## Configuración de Redes

### Virtual Network (Optional)

```
VNet: nexa-vnet
  ├─ Subnet: functions-subnet (Functions)
  ├─ Subnet: cosmos-subnet (Private endpoint)
  ├─ Subnet: storage-subnet (Private endpoint)
  └─ Subnet: keyvault-subnet (Private endpoint)

Network Security Groups:
  ├─ Allow APIM → Functions (internal)
  ├─ Allow Functions → Cosmos (internal)
  ├─ Allow Functions → Storage (internal)
  ├─ Allow Functions → Key Vault (internal)
  └─ Deny all else
```

### Public Endpoints (APIM Only)

```
Internet Clients
    ↓ HTTPS
API Management (public)
    ↓ Private network
Functions (private endpoint, optional)
    ↓ Internal routing
Cosmos DB (private endpoint, optional)
    ↓
Storage (private endpoint, optional)
```

---

## Observabilidad & Monitoreo

### Logging Strategy

**Level 1: Request/Response**

```python
@app.function_name('CalculateSimulation')
async def calculate_simulation(req: func.HttpRequest) -> func.HttpResponse:
    logger.info(f"[request] POST /calculate from={req.remote_addr} "
                f"client_id={req.headers.get('X-Client-ID')}")
    
    try:
        # ... processing ...
        logger.info(f"[response] 201 Created simulation_id={result.simulation_id} "
                    f"processing_time_ms={elapsed_ms}")
        return response
    
    except Exception as e:
        logger.exception(f"[error] Calculation failed: {e}")
        return error_response
```

**Level 2: Calculation Stages**

```python
logger.info(f"[calculation] Starting 10-layer pipeline")
logger.debug(f"[layer2] NominaCalculator.calcular() → {result.summary}")
logger.debug(f"[layers4-5] Parallel execution (threads=4) → completed")
logger.info(f"[calculation] Pipeline complete, building visions")
logger.debug(f"[vision_tarifas] VisionTarifasCalculator.calcular() → {count} rows")
logger.info(f"[calculation] Complete")
```

**Level 3: External Operations**

```python
logger.debug(f"[cosmos] query simulations collection")
logger.debug(f"[cosmos] create_item(simulation_id=...) → 45ms, 10 RU")
logger.debug(f"[storage] download blob lineage/{sim_id}/graph.json → 120ms")
logger.debug(f"[keyvault] get_secret(cosmos-db-connection-string) → 8ms")
```

### Tracing Strategy

**Distributed Tracing** (via Application Insights):

```
Request arrives at APIM
    ↓ [trace_id=abc123]
Function starts
    ├─ [span: deserialize_request] 50ms
    ├─ [span: load_parametrization] 200ms
    ├─ [span: execute_calculation] 2000ms
    │  ├─ [span: layer2_nomina] 400ms
    │  ├─ [span: layers4-5_parallel] 800ms (wall-clock, 1600ms threads)
    │  ├─ [span: layers6-9_sequential] 600ms
    │  └─ [span: vision_builders] 200ms
    ├─ [span: persist_cosmos] 100ms
    └─ [span: construct_response] 20ms
Function returns
    ↓
Total: 2.5s (app logic)

Traces visible in:
  - Application Insights Portal
  - Grafana dashboards (optional)
  - Splunk/ELK (optional, if integrated)
```

---

## Seguridad & Cumplimiento

### Authentication & Authorization

**Authentication:**

```
1. Client calls APIM with Authorization: Bearer {access_token}
2. APIM extracts token, validates signature
3. Verify token issued by Azure AD for tenant
4. Verify token not expired
5. Extract claims (user_id, groups, scopes)
6. Allow or deny (HTTP 401 if invalid)
```

**Authorization (RBAC):**

```
Roles:
  - Viewer:   GET /results/*
  - Operator: POST /calculate, GET /results/*, GET /audit/*
  - Admin:    All endpoints + /parametrization/*, /certification/*

APIM Policy:
  <choose>
    <when condition="@(context.User.Groups.Contains('Viewer'))">
      <!-- Allow GET only -->
    </when>
    <when condition="@(context.User.Groups.Contains('Operator'))">
      <!-- Allow GET, POST /calculate, /audit -->
    </when>
    <when condition="@(context.User.Groups.Contains('Admin'))">
      <!-- Allow all -->
    </when>
    <otherwise>
      <return-response>
        <set-status code="403" reason="Forbidden" />
      </return-response>
    </otherwise>
  </choose>
```

### Data Protection

**Encryption at Rest:**

```
Cosmos DB:
  - Service-managed encryption (AES-256)
  - Encryption key stored separately
  - Transparent to application

Storage:
  - Service-managed encryption (AES-256)
  - Optional: customer-managed keys (CMK) in Key Vault

Key Vault:
  - Hardware Security Module (HSM) backed
  - FIPS 140-2 Level 2 compliance
```

**Encryption in Transit:**

```
All connections use TLS 1.2+:
  - Client ↔ APIM: HTTPS (certificate pinning optional)
  - APIM ↔ Functions: Internal network (optional TLS)
  - Functions ↔ Cosmos DB: TLS 1.2
  - Functions ↔ Storage: TLS 1.2
  - Functions ↔ Key Vault: TLS 1.2
```

### Secrets Management

**No Secrets in Code:**

```python
# ❌ WRONG: Secrets in code
connection_string = "DefaultEndpointsProtocol=https;AccountName=..."
client = CosmosClient(connection_string)

# ✅ CORRECT: Secrets in Key Vault
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

credential = ManagedIdentityCredential()
secret_client = SecretClient(vault_url="https://{keyvault}.vault.azure.net", credential=credential)
connection_string = secret_client.get_secret("cosmos-db-connection-string").value
client = CosmosClient(connection_string)
```

### Compliance Certifications

**SOC 2 Type II:**
- Microsoft data centers certified
- Encryption + access controls + audit logs
- Third-party audits (annual)

**GDPR:**
- Data residency (EU region for EU customers)
- Right to deletion (TTL on simulations)
- Data portability (export via API)

**Financial Audit:**
- ExecutionCertificate (reproducibility proof)
- LineageGraph (calculation traceability)
- Audit logs (who called what, when)

---

## Estrategia de Despliegue

### Phase 1: Setup (Month 1)

**Weeks 1-2: Infrastructure**

```bash
# Create resource group
az group create --name nexa-rg --location eastus

# Deploy ARM template (IaC)
az deployment group create \
  --resource-group nexa-rg \
  --template-file infra/main.bicep \
  --parameters env=prod

# Provisions:
#   - APIM instance
#   - Cosmos DB account (3 regions)
#   - Storage account
#   - Key Vault
#   - Application Insights
#   - Function App
```

**Weeks 2-3: Functions**

```python
# Deploy Python functions
func azure functionapp publish nexa-function-app

# Configure bindings (in function.json)
{
  "scriptFile": "calculate.py",
  "bindings": [
    {
      "authLevel": "Function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["post"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}

# Test locally
func start
curl -X POST http://localhost:7071/api/calculate
```

**Weeks 3-4: Parallel Run**

```
Production Load
    ↓
[Load Balancer]
    ├─ 50% → Old Monolith (baseline)
    ├─ 50% → Azure (canary)
    └─ Compare results (tolerance: 0.01%)

Monitor:
  - Error rates
  - Latencies
  - Output parity
  - Cost

Rollout criteria:
  ✓ Parity achieved
  ✓ Error rate < 0.5%
  ✓ P99 latency < 2s
  ✓ No cost surprises
```

### Phase 2: Migration (Month 2)

**Deploy remaining functions**

```
CalculateSimulation   ✓ (from Phase 1)
RetrieveResults      ← Deploy
AuditSimulation      ← Deploy
ListVersions         ← Deploy
VerifyCertificate    ← Deploy
```

**Migrate parametrization storage**

```
Old: storage/parametrization/{hr,gn,op}/
     └─ Loaded via Python file I/O

New: Cosmos DB collection "parametrization"
     └─ Loaded via REST API
     └─ With versioning + drift detection
```

### Phase 3: Optimization (Month 3)

```
1. Performance profiling
   - Identify hot spots (per-layer timing)
   - Optimize Cosmos DB indexes
   - Tune Function memory allocation

2. Cost optimization
   - Use reserved instances (30% discount)
   - Archive old lineage graphs (cheaper storage tier)
   - Evaluate caching strategy (Redis?)

3. Observability maturity
   - Setup production dashboards
   - Configure alerting rules
   - Document runbooks
```

### Phase 4: Cutover (Month 4)

```
1. Pre-cutover validation
   - Final parity test (old vs. new)
   - Load test (1000 req/s sustained)
   - Security scan (OWASP Top 10)
   - Disaster recovery drill

2. Scheduled maintenance (24-hour window)
   - Customer notification
   - DNS CNAME update (old monolith → APIM)
   - Monitor error rates & latency
   - Rollback plan armed

3. Post-cutover validation (48 hours)
   - Live traffic monitoring
   - Customer smoke tests
   - Archive old system backups
   - Decommission on-prem infrastructure
```

---

## Estimación de Costos

### Modelo de Costos Mensual (Producción)

| Component | Volume | Unit Cost | Monthly | Notes |
|-----------|--------|-----------|---------|-------|
| APIM (Standard tier) | — | $150 flat | $150 | Gateway + rate limiting |
| Functions (compute) | 5M × 500ms | $0.000000167/GB-s | $417 | Parallel layers 2-5 efficient |
| Functions (requests) | 5M | $0.20/1M | $1 | Minimal |
| Cosmos DB (RU) | 50 GB/day | Variable | $500 | Auto-scale included |
| Storage (blobs) | 100 GB | $0.018/GB | $50 | Parametrization + lineage |
| Key Vault | 10 secrets | $1 each | $10 | Per-secret fee |
| Monitor + AppInsights | 1 GB/day logs | $2.46/GB | $74 | Ingestion cost |
| Data Transfer (egress) | 10 GB | $0.09/GB | $9 | Cloud egress |
| — | — | **SUBTOTAL** | **$1,211** | |
| Discount: Reserved Instances | -30% | — | -$150 | 1-year Cosmos commitment |
| Discount: Spot Functions | -60% | — | -$250 | Low-priority compute |
| — | — | **TOTAL** | **$811** | Optimized |

### Desglose de Costos por Componente

**APIM:** $150/month (fixed)
- Standard tier = $150/month
- No cost per request (first 1M included)
- Rate limiting + versioning included

**Functions:** ~$350–600/month depending on load
- CalculateSimulation: 5M calls × 500ms × 1GB = $250/month
- Other functions: minimal (mostly GET, < 50ms)

**Cosmos DB:** $400–700/month depending on throughput
- Auto-scale: 400–1000 RU/s
- ~$0.50 per 100 RU/hour
- With reserved capacity: -30% discount

**Storage:** $50–100/month
- Parametrization snapshots: ~10 MB (negligible)
- Lineage graphs: ~100 KB per simulation × 5K/month = 500 GB/month
- Archive tier: $0.004/GB (cost optimization)

**Observability:** $70–150/month
- Application Insights: $2.46/GB ingestion
- 1 GB/day = ~30 GB/month
- Longer retention → higher cost

### Cost Optimization Strategies

1. **Reserved Instances** (Cosmos DB)
   - 1-year commitment: -30% discount
   - Savings: $150/month

2. **Spot Instances** (Functions)
   - Low-priority compute: -60% discount
   - Savings: $200+/month
   - Risk: interruptible (acceptable for non-critical)

3. **Archive Storage Tier**
   - Lineage > 90 days: move to archive ($0.004/GB)
   - Savings: $40–80/month

4. **Caching Layer** (Redis, optional)
   - Hot simulations (< 1 day): cache results
   - Reduces Cosmos DB reads
   - Cost: $50–150/month (may exceed savings)

5. **Parametrization Compression**
   - JSON → MessagePack (binary format)
   - Reduces storage + network
   - Minimal savings, more complexity

---

## Apéndices

### A. Terraform IaC (Infrastructure as Code)

```hcl
# main.tf
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "nexa" {
  name     = "nexa-rg"
  location = "East US"
}

resource "azurerm_cosmosdb_account" "nexa" {
  name                = "nexa-cosmos"
  location            = azurerm_resource_group.nexa.location
  resource_group_name = azurerm_resource_group.nexa.name
  offer_type          = "Standard"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = "East US"
    failover_priority = 0
  }

  geo_location {
    location          = "West Europe"
    failover_priority = 1
  }

  geo_location {
    location          = "Southeast Asia"
    failover_priority = 2
  }
}

# ... more resources (Storage, Key Vault, Functions, APIM, etc.)
```

### B. GitHub Actions CI/CD Pipeline

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=calculators --cov-report=term

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v2
      - uses: azure/setup-kubectl@v1
      - run: |
          func azure functionapp publish \
            --resource-group nexa-rg \
            --name nexa-function-app

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - run: |
          az deployment group create \
            --resource-group nexa-rg \
            --template-file infra/main.bicep
```

### C. Runbook: Diagnostic de Errores

```
SYMPTOM: High error rate (> 5%)

DIAGNOSTIC STEPS:
1. Check Application Insights
   - Review recent error logs
   - Identify error type (4xx vs 5xx)
   - Trace affected requests

2. If 5xx (server error):
   - Check Function logs (Azure Portal)
   - Look for timeouts, memory issues, dependency failures
   - Typical causes:
     a) Cosmos DB throttling (RU limit exceeded)
     b) Parametrization missing (wrong version)
     c) Network connectivity issue

3. If 4xx (client error):
   - Check request validation (EntryDataV1 schema)
   - Verify client credentials (OAuth token)
   - Check rate limiting

4. Mitigation:
   - If Cosmos throttling: increase RU/s (auto-scale)
   - If parametrization: verify versions.json
   - If network: check VNet NSG rules
   - If credentials: rotate tokens

5. Long-term:
   - Monitor RU consumption trends
   - Tune Function memory/timeout
   - Review request patterns (unusual spike?)
```

### D. Runbook: Disaster Recovery

```
SCENARIO: Cosmos DB primary region (East US) down

EXPECTED BEHAVIOR:
1. Cosmos DB auto-failover (< 5 min)
   - West Europe becomes write region
   - Southeast Asia becomes read replica
   - RTO < 5 minutes, RPO < 1 minute

2. APIM health check detects failure
   - Probes Functions every 30s
   - If East US Functions unavailable:
     - Route to West Europe + Southeast Asia Functions
     - Traffic shifted automatically

3. Functions can read from any region
   - Replica regions lag by < 1 second
   - Session consistency + local quorum

RECOVERY ACTIONS:
1. Monitor Cosmos DB failover completion
   - Check "Monitoring" tab in Azure Portal
   - Verify new write region

2. Once East US recovered:
   - Cosmos DB auto-failback (if configured)
   - Or manual failback (Admin choice)

3. Verify application state
   - Query Cosmos DB (latest simulation)
   - Compare with backup/lineage
   - No data loss expected

TOTAL DOWNTIME: < 5 minutes
COMMUNICATION: Alert sent to on-call
```

### E. Performance Benchmark Results

**(Hypothetical baseline for project planning)**

```
Test Setup:
  - Contract: 120 months
  - Roles: 10 (mixed types)
  - Scenario: standard (no extreme parameters)
  - Parametrization: v2-7 active

Results (single invocation):
  ├─ Deserialization: 50ms
  ├─ Load parametrization: 200ms (cached < 50ms on warm)
  ├─ Execute Layer 2 (Nomina): 400ms
  ├─ Layers 3-5 (parallel, 4 threads): 800ms (wall-clock) / 1600ms (total threads)
  ├─ Layers 6-9 (sequential): 600ms
  ├─ Vision builders: 200ms
  ├─ Lineage capture: 150ms
  ├─ Persist to Cosmos DB: 100ms
  └─ **Total: 2.5 seconds**

Scaling:
  - 120 months → 2.5s
  - 240 months → 4.2s (non-linear due to more rows)
  - 360 months → 6.5s

Memory usage:
  - Baseline: 150 MB (runtime)
  - 120-month contract: 300 MB
  - 240-month contract: 500 MB
  - 360-month contract: 700 MB

Parallelization benefit:
  - Serial (all 10 layers): 4.2s
  - Parallel layers 2-5: 2.5s
  - **Speedup: 1.68x** (not linear due to sequential layers)
```

---

## Contacto & Soporte

**Architecture Owner:** [Name], [Email]  
**Cloud Platform Team:** [Email]  
**On-Call Rotation:** [PagerDuty Link]  
**Documentation:** [Wiki/Confluence Link]  
**Code Repository:** [GitHub URL]

---

**Documento Control:**

| Versión | Fecha | Autor | Cambios |
|---------|-------|-------|---------|
| 1.0 | 2026-05-31 | NEXA Architecture Team | Release inicial |

