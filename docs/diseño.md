# Arquitectura Cloud: Pricing Simulator — Microsoft Azure

---

## 1. Diagrama Secuencial End-to-End

```
┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐
│  Cliente │  │  Front Door  │  │    WAF    │  │ APIM │  │Functions │  │ Key Vault │  │Cosmos DB │  │  Blob  │  │ Monitor  │
└────┬─────┘  └──────┬───────┘  └─────┬─────┘  └──┬───┘  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └───┬────┘  └────┬─────┘
     │                │                │            │           │              │               │            │            │
     │ HTTPS POST /simulations         │            │           │              │               │            │            │
     │ Authorization: Bearer <JWT>     │            │           │              │               │            │            │
     │ X-Correlation-ID: <uuid>        │            │           │              │               │            │            │
     │───────────────>│                │            │           │              │               │            │            │
     │                │ Anycast DNS    │            │           │              │               │            │            │
     │                │ TLS 1.3 term.  │            │           │              │               │            │            │
     │                │ Route /api/*   │            │           │              │               │            │            │
     │                │───────────────>│            │           │              │               │            │            │
     │                │                │ OWASP CRS  │           │              │               │            │            │
     │                │                │ Rate limit │           │              │               │            │            │
     │                │                │ Bot detect │           │              │               │            │            │
     │                │                │ → PASS     │           │              │               │            │            │
     │                │                │───────────>│           │              │               │            │            │
     │                │                │            │ JWT valid │              │               │            │            │
     │                │                │            │ Scope chk │              │               │            │            │
     │                │                │            │ Rate limit│              │               │            │            │
     │                │                │            │ X-Corr-ID │              │               │            │            │
     │                │                │            │ → PASS    │              │               │            │            │
     │                │                │            │──────────>│              │               │            │            │
     │                │                │            │           │ GetSecret(   │               │            │            │
     │                │                │            │           │  cosmos-conn)│               │            │            │
     │                │                │            │           │─────────────>│               │            │            │
     │                │                │            │           │<── secret ───│               │            │            │
     │                │                │            │           │              │               │            │            │
     │                │                │            │           │ Validate body│               │            │            │
     │                │                │            │           │ Execute calc │               │            │            │
     │                │                │            │           │ Build doc    │               │            │            │
     │                │                │            │           │──────────────────────────────>│            │            │
     │                │                │            │           │<────────── 201 Created ───────│            │            │
     │                │                │            │           │              │               │            │            │
     │                │                │            │           │ Upload report (async DurFunc) │            │            │
     │                │                │            │           │────────────────────────────────────────>│            │
     │                │                │            │           │              │               │            │            │
     │                │                │            │           │ TrackEvent + Trace            │            │            │
     │                │                │            │           │────────────────────────────────────────────────────>│
     │                │                │            │           │              │               │            │            │
     │                │                │            │<── 201 ───│              │               │            │            │
     │                │                │            │ Set headers (Corr-ID,    │               │            │            │
     │                │                │            │  Security, HSTS)         │               │            │            │
     │                │<───────────────────────────<│           │              │               │            │            │
     │<───────────────│                │            │           │              │               │            │            │
```

---

## 2. Separación de Ambientes

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AZURE TENANT                                            │
│                                                                                   │
│  ┌───────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  │
│  │  Subscription: DEV    │  │  Subscription: PROD   │  │  Subscription: DR    │  │
│  │  RG: pricing-sim-dev  │  │  RG: pricing-sim-prod │  │  RG: pricing-sim-dr  │  │
│  │                       │  │                       │  │                      │  │
│  │  Functions (Python)   │  │  Functions (Python)   │  │  Functions (Python)  │  │
│  │  Cosmos DB (dev)      │  │  Cosmos DB (prod)     │  │  Cosmos DB (replica) │  │
│  │  APIM (dev)           │  │  APIM (prod)          │  │  APIM (dr)           │  │
│  │  Key Vault (dev)      │  │  Key Vault (prod)     │  │  Key Vault (dr)      │  │
│  │  Blob Storage (dev)   │  │  Blob Storage (prod)  │  │  Blob Storage (dr)   │  │
│  │  AppInsights (dev)    │  │  AppInsights (prod)   │  │  AppInsights (dr)    │  │
│  │                       │  │                       │  │                      │  │
│  │  Region: East US      │  │  Region: East US 2    │  │  Region: West US 3   │  │
│  └───────────────────────┘  └──────────────────────┘  └──────────────────────┘  │
│                                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │  Azure Front Door Premium (Global — única instancia)                       │   │
│  │  pricing-sim-dev.example.com  ──────────────────→  Origin: APIM DEV        │   │
│  │  pricing-sim.example.com      → Priority 1 ──────→  Origin: APIM PROD      │   │
│  │                               → Priority 2 ──────→  Origin: APIM DR        │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │  Azure Entra ID                                                            │   │
│  │  App Registration: pricing-simulator-dev   (client_id_dev, scopes dev)     │   │
│  │  App Registration: pricing-simulator-prod  (client_id_prod, scopes prod)   │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Principios de aislamiento:**
- Suscripciones Azure separadas por ambiente — RBAC no puede cruzar suscripciones accidentalmente
- Key Vault completamente independiente por ambiente; ningún secreto es compartido
- Managed Identity distinta por ambiente; no puede autenticarse contra recursos de otro ambiente
- Tags obligatorios en todos los recursos: `environment`, `project`, `owner`, `cost-center`
- Cosmos DB DEV y PROD nunca comparten replication link; son cuentas separadas

---

## 3. Catálogo Completo de Endpoints REST

### Base URLs
```
DEV:  https://pricing-sim-dev.example.com/api/v1
PROD: https://pricing-sim.example.com/api/v1
```

### Headers obligatorios en todas las requests
```http
Authorization: Bearer <JWT>
X-Correlation-ID: <uuid-v4>
Content-Type: application/json
Accept: application/json
```

### Headers obligatorios en todas las responses
```http
X-Correlation-ID: <uuid-v4>          (mismo que el de la request)
X-Request-ID: <uuid-v4>              (generado por APIM, único por request)
Content-Type: application/json
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Cache-Control: no-store
```

### Formato estándar de error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "El campo 'cadena' debe ser A, B o C",
    "details": [
      { "field": "scenario.cadena", "issue": "valor 'X' no permitido", "allowed": ["A","B","C"] }
    ],
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-05-29T10:00:00.123Z"
  }
}
```

---

### 3.1 Simulaciones

---

#### `POST /simulations`

Ejecuta una simulación de precios completa y persiste el resultado.

**Autenticación:** Bearer JWT — scope requerido: `simulation.write`

**Request Body:**
```json
{
  "client_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "scenario": {
    "canal": "directo",
    "cadena": "A",
    "modelo_cobro": "fijo",
    "volumen_operaciones": 15000,
    "periodo_meses": 12,
    "moneda": "COP",
    "municipio": "BOGOTA"
  },
  "version_parametros": "v2-7",
  "parametros_override": {
    "tasa_descuento": 0.12,
    "factor_indexacion": 0.035
  },
  "idempotency_key": "sha256-del-payload-opcional"
}
```

> `parametros_override` requiere scope adicional `simulation.admin`. Si se omite, se usan los parámetros activos de la versión indicada.
> `version_parametros` es opcional; si se omite usa la versión activa vigente.

**Response 201 — Procesamiento sincrónico (< 30s):**
```json
{
  "simulation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "client_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "completed",
  "created_at": "2026-05-29T10:00:00.123Z",
  "completed_at": "2026-05-29T10:00:01.850Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "version_parametros": "v2-7",
  "result": {
    "precio_base": 120000000.00,
    "precio_final": 138500000.00,
    "desglose": {
      "nomina": 80000000.00,
      "costos_operativos": {
        "fijo": 15000000.00,
        "variable": 5000000.00,
        "subtotal": 20000000.00
      },
      "costos_financieros": 5000000.00,
      "capex_amortizado": 10000000.00,
      "no_payroll": 5000000.00,
      "ica": 1200000.00,
      "gmf": 480000.00,
      "polizas": 0.00,
      "admin": 1490400.00,
      "margen": 15329600.00
    },
    "pyg": {
      "ingresos": 138500000.00,
      "costo_total": 123170400.00,
      "ebitda": 15329600.00,
      "ebitda_pct": 0.1107,
      "ebit": 14329600.00,
      "utilidad_antes_impuesto": 14329600.00,
      "impuesto_renta": 4727568.00,
      "utilidad_neta": 9602032.00,
      "utilidad_neta_pct": 0.0693
    },
    "metadata": {
      "engine_version": "2.0.0",
      "version_parametros": "v2-7",
      "factor_cadena": 1.00,
      "factor_canal": 1.00,
      "factor_indexacion_aplicado": 1.035,
      "periodos_indexacion": 1
    }
  }
}
```

**Response 202 — Procesamiento asincrónico (estimado > 30s):**
```json
{
  "simulation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "processing",
  "created_at": "2026-05-29T10:00:00.123Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "poll_url": "/api/v1/simulations/7c9e6679-7425-40de-944b-e07fc1f90ae7/status",
  "estimated_completion_seconds": 45
}
```

**Response 200 — Idempotencia (mismo payload en < 60s):**
```json
{
  "simulation_id": "existing-uuid",
  "status": "completed",
  "idempotent": true,
  "...": "mismo body que el 201 original"
}
```
> Header adicional: `X-Idempotent: true`

**Códigos de error:**

| Código | `error.code` | Causa |
|--------|-------------|-------|
| 400 | `VALIDATION_ERROR` | Payload malformado o campos inválidos |
| 401 | `UNAUTHORIZED` | JWT ausente, expirado o firma inválida |
| 403 | `FORBIDDEN` | JWT válido pero scope insuficiente |
| 409 | `CONFLICT` | `client_id` ya tiene 3 simulaciones en curso |
| 422 | `BUSINESS_RULE_VIOLATION` | Parámetros de negocio inconsistentes (ej: cadena B sin componente variable) |
| 429 | `RATE_LIMIT_EXCEEDED` | Límite de requests alcanzado |
| 500 | `INTERNAL_ERROR` | Error no controlado |
| 503 | `SERVICE_UNAVAILABLE` | Cosmos DB o Functions degradados |

---

#### `GET /simulations/{simulation_id}`

Recupera el resultado completo de una simulación.

**Autenticación:** Bearer JWT — scope: `simulation.read`

**Path param:** `simulation_id` (uuid-v4)

**Response 200:**
```json
{
  "simulation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "client_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "completed",
  "created_at": "2026-05-29T10:00:00.123Z",
  "completed_at": "2026-05-29T10:00:01.850Z",
  "deleted_at": null,
  "version_parametros": "v2-7",
  "scenario": {
    "canal": "directo",
    "cadena": "A",
    "modelo_cobro": "fijo",
    "volumen_operaciones": 15000,
    "periodo_meses": 12,
    "moneda": "COP",
    "municipio": "BOGOTA"
  },
  "result": { "...": "idéntico al POST /simulations 201" },
  "audit": {
    "created_by": "usr_***abc",
    "ip": "190.***.***.45",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "engine_version": "2.0.0"
  }
}
```

**Códigos de error:** `401`, `403`, `404` (`SIMULATION_NOT_FOUND`)

---

#### `GET /simulations/{simulation_id}/status`

Polling de estado para simulaciones asincrónicas.

**Autenticación:** Bearer JWT — scope: `simulation.read`

**Response 200:**
```json
{
  "simulation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "processing",
  "progress_pct": 65,
  "started_at": "2026-05-29T10:00:00.123Z",
  "estimated_completion_at": "2026-05-29T10:00:45.000Z",
  "current_step": "calculating_costos_financieros"
}
```

> Cuando `status = "completed"`, el body incluye `result_url: "/api/v1/simulations/{id}"`. Cuando `status = "failed"`, incluye `error: { code, message }`.

---

#### `GET /simulations`

Lista simulaciones del cliente autenticado con paginación por cursor.

**Autenticación:** Bearer JWT — scope: `simulation.read`

**Query params:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `client_id` | uuid | No | Filtrar por cliente (scope admin para ver otros) |
| `from` | ISO8601 | No | Fecha inicio (default: -30 días) |
| `to` | ISO8601 | No | Fecha fin (default: now) |
| `status` | string | No | `completed`, `processing`, `failed` |
| `cadena` | string | No | `A`, `B`, `C` |
| `cursor` | string | No | Cursor de paginación opaco (base64) |
| `page_size` | integer | No | Default 20, máximo 100 |

**Response 200:**
```json
{
  "items": [
    {
      "simulation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "client_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "status": "completed",
      "created_at": "2026-05-29T10:00:00.123Z",
      "version_parametros": "v2-7",
      "scenario": { "canal": "directo", "cadena": "A", "modelo_cobro": "fijo" },
      "result_summary": {
        "precio_final": 138500000.00,
        "moneda": "COP"
      }
    }
  ],
  "pagination": {
    "page_size": 20,
    "total_returned": 1,
    "has_more": false,
    "next_cursor": null,
    "prev_cursor": null
  }
}
```

> No se retorna `total` absoluto para evitar queries costosas con `COUNT(*)` en Cosmos DB. Se usa cursor-based pagination.

---

#### `DELETE /simulations/{simulation_id}`

Soft-delete lógico. El documento persiste con `deleted_at` para auditoría regulatoria.

**Autenticación:** Bearer JWT — scope: `simulation.admin`

**Response 204:** Sin body.

**Response 404:** `SIMULATION_NOT_FOUND`

**Response 409:** `ALREADY_DELETED` — ya fue eliminado previamente.

---

### 3.2 Parámetros

---

#### `GET /parameters/versions`

Lista todas las versiones de parámetros disponibles.

**Autenticación:** Bearer JWT — scope: `parameters.read`

**Response 200:**
```json
{
  "versions": [
    {
      "version": "v2-7",
      "status": "active",
      "published_at": "2026-05-11T09:52:29Z",
      "published_by": "usr_***xyz",
      "certification_id": "cert-uuid",
      "sunset_at": null
    },
    {
      "version": "v2-6",
      "status": "deprecated",
      "published_at": "2026-03-01T08:00:00Z",
      "sunset_at": "2026-08-01T00:00:00Z"
    }
  ]
}
```

---

#### `GET /parameters/{version}`

Retorna el contenido completo de una versión de parámetros.

**Autenticación:** Bearer JWT — scope: `parameters.read`

**Path param:** `version` — ej: `v2-7`

**Query param:** `include_snapshot=true` (incluye snapshot completo de HR/OP; default `false` — sólo business_rules)

**Response 200:**
```json
{
  "version": "v2-7",
  "status": "active",
  "published_at": "2026-05-11T09:52:29Z",
  "integrity": {
    "sha256": "a3f5bc...",
    "signed_by": "usr_approver_1",
    "countersigned_by": "usr_approver_2"
  },
  "business_rules": {
    "tasa_impuesto_renta": 0.33,
    "comision_adm_pct": 0.0118,
    "factor_indexacion_base": 0.035,
    "ipc_proyectado": 0.06,
    "spread_negocio": 0.025,
    "tasa_gmf": 0.004,
    "com_vendedor_pct": 0.08,
    "com_cont_pct": 0.05,
    "factor_canal_1": 1.12,
    "factor_canal_2": 1.25,
    "ica_por_municipio": {
      "BOGOTA": 0.01104,
      "MEDELLIN": 0.01,
      "CALI": 0.01
    }
  },
  "hr": { "...": "incluido sólo si include_snapshot=true" },
  "op": { "...": "incluido sólo si include_snapshot=true" }
}
```

---

#### `POST /parameters`

Publica una nueva versión de parámetros en estado `draft`. No activa automáticamente; requiere certificación exitosa.

**Autenticación:** Bearer JWT — scope: `parameters.write`

**Request Body:**
```json
{
  "version": "v2-8",
  "business_rules": { "...": "objeto completo" },
  "hr_data": {
    "sheets": {
      "Director": { "salario_base": 12000000, "factor_prestaciones": 1.521 },
      "GTR": { "salario_base": 8000000, "factor_prestaciones": 1.521 }
    }
  },
  "op_data": { "...": "objeto completo" },
  "gn_data": { "...": "objeto completo" }
}
```

**Response 201:**
```json
{
  "version": "v2-8",
  "status": "draft",
  "published_at": "2026-05-29T10:00:00Z",
  "published_by": "usr_***abc",
  "integrity": { "sha256": "b4a1cd..." },
  "next_step": "POST /certifications con version: v2-8"
}
```

**Códigos de error:** `400` (schema inválido), `401`, `403`, `409` (versión ya existe)

---

#### `PATCH /parameters/{version}`

Actualiza el estado de una versión (`draft → active`, `active → deprecated`). Requiere firma de dos actores (4-eyes).

**Autenticación:** Bearer JWT — scope: `parameters.admin`

**Request Body:**
```json
{
  "status": "active",
  "countersign_token": "token-del-segundo-aprobador",
  "sunset_at": null
}
```

**Response 200:**
```json
{
  "version": "v2-8",
  "status": "active",
  "updated_at": "2026-05-29T11:00:00Z",
  "updated_by": "usr_***abc",
  "countersigned_by": "usr_***xyz"
}
```

> Transición `active → deprecated` también depreca automáticamente la versión anterior si existe otra `active`.

**Códigos de error:** `400` (transición no permitida), `401`, `403`, `404`, `409` (certification no aprobada para activar)

---

### 3.3 Certificación

---

#### `POST /certifications`

Lanza proceso de certificación de parámetros contra el oracle Excel. Ejecución asincrónica.

**Autenticación:** Bearer JWT — scope: `parameters.write`

**Request Body:**
```json
{
  "version": "v2-7",
  "oracle_blob_path": "certifications/2026/05/29/oracle_v2-7.xlsx",
  "oracle_sas_token": "sv=2024-...&sig=..."
}
```

**Response 202:**
```json
{
  "certification_id": "cert-7c9e6679",
  "version": "v2-7",
  "status": "running",
  "started_at": "2026-05-29T10:00:00Z",
  "poll_url": "/api/v1/certifications/cert-7c9e6679"
}
```

---

#### `GET /certifications/{certification_id}`

Retorna resultado completo de certificación.

**Autenticación:** Bearer JWT — scope: `parameters.read`

**Response 200:**
```json
{
  "certification_id": "cert-7c9e6679",
  "version": "v2-7",
  "status": "passed",
  "started_at": "2026-05-29T10:00:00Z",
  "completed_at": "2026-05-29T10:02:15Z",
  "score": {
    "total_cells": 1118,
    "matched": 1118,
    "failed": 0,
    "drift_pct": 0.0000,
    "tolerance_abs": 0.01,
    "tolerance_pct": 0.0001
  },
  "checkpoints": {
    "total": 161,
    "passed": 161,
    "failed": 0
  },
  "drift_heatmap_url": "https://pricing-sim-prod.blob.core.windows.net/certifications/2026/05/29/cert-7c9e6679/heatmap.html?sv=...",
  "report_url": "https://pricing-sim-prod.blob.core.windows.net/certifications/2026/05/29/cert-7c9e6679/report.json?sv=..."
}
```

> Si `status = "failed"`, `score.failed > 0` e incluye `failures: [ { cell, expected, actual, diff } ]`.

---

#### `GET /certifications`

Lista certificaciones por versión de parámetros.

**Query params:** `?version=v2-7&status=passed|failed|running&page_size=20&cursor=...`

**Response 200:** Misma estructura paginada que `GET /simulations`.

---

### 3.4 Auditoría

---

#### `GET /audit/logs`

Consulta el log de auditoría inmutable.

**Autenticación:** Bearer JWT — scope: `audit.read` (rol auditor exclusivo)

**Query params:**

| Param | Tipo | Descripción |
|-------|------|-------------|
| `from` | ISO8601 | Obligatorio |
| `to` | ISO8601 | Obligatorio |
| `event_type` | string | `simulation.created`, `param.updated`, `auth.failed`, `secret.accessed`, ... |
| `actor_user_id` | string | Masked — búsqueda parcial |
| `resource_id` | uuid | ID del recurso afectado |
| `correlation_id` | uuid | Trazar un request específico |
| `cursor` | string | Paginación |
| `page_size` | integer | Máximo 500 |

**Response 200:**
```json
{
  "items": [
    {
      "event_id": "evt-uuid",
      "event_date": "2026-05-29",
      "timestamp": "2026-05-29T10:00:00.123Z",
      "event_type": "simulation.created",
      "actor": {
        "user_id": "usr_***abc",
        "ip": "190.***.***.45",
        "user_agent_hash": "sha256:abc123"
      },
      "resource": {
        "type": "simulation",
        "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
      },
      "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
      "payload_hash": "sha256:def456",
      "integrity_hash": "sha256:rsa-signed-ghi789"
    }
  ],
  "pagination": { "has_more": true, "next_cursor": "eyJ..." }
}
```

---

#### `GET /audit/logs/{event_id}/verify`

Verifica la integridad criptográfica de un evento de auditoría. Recalcula el hash y compara con la firma RSA-2048 almacenada.

**Autenticación:** Bearer JWT — scope: `audit.read`

**Response 200:**
```json
{
  "event_id": "evt-uuid",
  "integrity_valid": true,
  "computed_hash": "sha256:ghi789",
  "stored_hash": "sha256:ghi789",
  "verified_at": "2026-05-29T12:00:00Z"
}
```

---

### 3.5 Clientes

---

#### `POST /clients`

Registra un nuevo cliente en el sistema.

**Autenticación:** Bearer JWT — scope: `clients.write`

**Request Body:**
```json
{
  "razon_social": "Empresa ABC S.A.S",
  "nit": "900123456-7",
  "municipio_principal": "BOGOTA",
  "sector": "retail",
  "contacto": {
    "nombre": "Juan Pérez",
    "email": "juan@empresa.com",
    "telefono": "+573001234567"
  }
}
```

> `nit` y `email` se almacenan cifrados con AES-256 (CMK en Key Vault). En response siempre se retornan enmascarados.

**Response 201:**
```json
{
  "client_id": "new-uuid",
  "razon_social": "Empresa ABC S.A.S",
  "nit": "900***456-7",
  "municipio_principal": "BOGOTA",
  "sector": "retail",
  "created_at": "2026-05-29T10:00:00Z"
}
```

---

#### `GET /clients/{client_id}`

**Autenticación:** Bearer JWT — scope: `clients.read`

**Response 200:** Mismo schema que POST response, más `updated_at`, `simulation_count`.

---

### 3.6 Health & Observabilidad

---

#### `GET /health`

Liveness probe — verifica que la Function está activa. Sin autenticación (WAF activo).

**Response 200:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "prod",
  "timestamp": "2026-05-29T10:00:00Z"
}
```

**Response 503:**
```json
{
  "status": "unhealthy",
  "version": "2.0.0",
  "timestamp": "2026-05-29T10:00:00Z"
}
```

---

#### `GET /health/ready`

Readiness probe — verifica conectividad con todos los servicios dependientes.

**Response 200:**
```json
{
  "status": "ready",
  "components": {
    "cosmos_db": { "status": "ok", "latency_ms": 4 },
    "key_vault": { "status": "ok", "latency_ms": 2 },
    "blob_storage": { "status": "ok", "latency_ms": 8 }
  },
  "timestamp": "2026-05-29T10:00:00Z"
}
```

**Response 503:**
```json
{
  "status": "not_ready",
  "components": {
    "cosmos_db": { "status": "error", "error": "connection timeout", "latency_ms": 5000 },
    "key_vault": { "status": "ok", "latency_ms": 2 },
    "blob_storage": { "status": "ok", "latency_ms": 8 }
  }
}
```

---

#### `GET /metrics/summary`

Métricas de uso para dashboards internos.

**Autenticación:** Bearer JWT — scope: `metrics.read`

**Response 200:**
```json
{
  "period": { "from": "2026-05-29T00:00:00Z", "to": "2026-05-29T23:59:59Z" },
  "simulations": {
    "total": 342,
    "completed": 338,
    "failed": 4,
    "processing": 0,
    "avg_duration_ms": 1240,
    "p95_duration_ms": 1890
  },
  "errors": {
    "4xx": 12,
    "5xx": 2
  },
  "top_clients": [
    { "client_id": "uuid-masked", "simulation_count": 45 }
  ]
}
```

---

## 4. Reglas de Negocio del Simulador

**RN-001 — Versionamiento de parámetros**
- Toda simulación referencia una versión explícita de parámetros
- El `parametros_snapshot` se congela en el momento de la ejecución; cambios futuros no afectan simulaciones históricas
- Versiones `deprecated` sólo accesibles con flag `allow_legacy=true` y scope `simulation.admin`
- Versiones `draft` no pueden usarse en simulaciones

**RN-002 — Validación de escenario comercial**
- `cadena` ∈ `{A, B, C}`
- `canal` ∈ `{directo, canal_1, canal_2}`
- `modelo_cobro: mixto` requiere `componente_fijo > 0` AND `componente_variable > 0`; cualquiera en cero → `422`
- `periodo_meses` ∈ `[1, 60]`
- `volumen_operaciones` > 0

**RN-003 — Concurrencia por cliente**
- Máximo 3 simulaciones simultáneas por `client_id` (estado `processing`)
- Al superar el límite → `409 CONFLICT` con `active_simulations_count` en el body

**RN-004 — Integridad y 4-eyes de parámetros**
- Parámetros pasan de `draft` a `active` sólo con certificación `passed` + dos firmas
- El primer aprobador firma con `PATCH /parameters/{version}` con su JWT
- El segundo aprobador aporta `countersign_token` (OTP generado por Entra ID)
- Cualquier cambio genera entrada en `audit_log` con `integrity_hash`

**RN-005 — Enmascaramiento de datos sensibles**
- Campos PII (`nit`, `rut`, `email`, `telefono`) jamás aparecen en claro en logs, telemetría ni responses de auditoría
- Formato masking: primeros 3 + últimos 2 caracteres visibles, resto `***`
- La IP del actor: octetos 3 y 4 siempre reemplazados por `***`

**RN-006 — Retención y eliminación**
- Simulaciones: retención mínima 5 años desde `created_at`; sólo soft-delete
- Hard-delete requiere proceso legal documentado y aprobación en sistema externo
- `audit_log`: append-only, retención 7 años, WORM en Blob Storage

**RN-007 — Idempotencia**
- Misma combinación `client_id` + hash del `scenario` en ventana de 60 segundos → retorna la simulación existente
- `idempotency_key` puede proveerse explícitamente; si no, se calcula como `SHA256(client_id + JSON.stringify(scenario))`
- Response incluye header `X-Idempotent: true` y HTTP 200 (no 201)

**RN-008 — Cadenas B y C**
- `factor_cadena["B"] = 0` y `factor_cadena["C"] = 0` hasta que se parametrice C1/C2
- El simulador NO bloquea la ejecución; retorna precio calculado con factor 0 y advertencia en `metadata.warnings`

**RN-009 — Comisiones Director/GTR**
- `comision_pct` de roles Director y GTR es siempre 0, hardcoded, no sobreescribible por `parametros_override`
- Validación en la capa de negocio, no en el contrato de request

---

## 5. Fórmulas de Cálculo de Precios (Completas)

### 5.1 Precio Final

```
PrecioFinal = CostoTotal × FactorIndexacion^PeriodosIndexacion

donde:
  CostoTotal = Nomina
             + CostosOperativos
             + CostosFinancieros
             + CAPEX_Amortizado
             + NoPayroll
             + ICA
             + GMF
             + Polizas
             + Admin

  FactorIndexacion    = 1 + (IPC_proyectado + spread_negocio)
  PeriodosIndexacion  = floor(periodo_meses / 12)
```

### 5.2 Nómina

```
Nomina = Σ_i ( empleados_i × salario_base_i × factor_prestaciones_i × periodo_meses )

factor_prestaciones_i = 1
  + prima_legal / 12                    # 1 salario / año → 1/12 mensual
  + cesantias / 12                      # 1 salario / año
  + intereses_cesantias / 12            # 12% sobre cesantías / año → 0.12/12 mensual
  + vacaciones / 24                     # 15 días / año → 0.5/12 mensual = /24
  + salud_empleador                     # 8.5%
  + pension_empleador                   # 12%
  + arl                                 # 0.522% (clase I riesgo mínimo, configurable)
  + caja_compensacion                   # 4%
  + icbf                                # 3%  (sólo si salario < 10 SMLMV)
  + sena                                # 2%  (sólo si salario < 10 SMLMV)

# Roles con comision_pct = 0: Director, GTR
Comision_i = salario_base_i × comision_pct_i    # 0 para Director/GTR
Nomina_total = Nomina + Σ_i Comision_i
```

### 5.3 Costos Operativos

```
CostosOperativos = CostoFijo + CostoVariable

# modelo_cobro = "fijo"
CostoFijo    = overhead_mensual × periodo_meses
CostoVariable = 0

# modelo_cobro = "variable"
CostoFijo    = 0
CostoVariable = costo_por_operacion × volumen_operaciones

# modelo_cobro = "mixto"
CostoFijo    = componente_fijo × periodo_meses
CostoVariable = costo_por_operacion × volumen_operaciones

# Los valores de overhead, costo_por_operacion provienen de parametros["op"][cadena][canal]
```

### 5.4 Costos Financieros

```
CostosFinancieros = Σ_item ( monto_item × tasa_mensual_financ × plazo_meses_item )

# Para ítems CAPEX financiados:
factor_financiacion_item = (1 + tasa_mensual_financ) ^ plazo_meses_item
CostoFinancieroItem = monto_item × (factor_financiacion_item - 1)

# tasa_mensual_financ proviene de business_rules["tasa_mensual_financ"]
# plazo_meses_item y monto_item provienen de la hoja CAPEX en parámetros HR/OP
```

### 5.5 CAPEX Amortizado

```
CAPEX_Amortizado = Σ_item ( capex_item / plazo_amortizacion_meses_item ) × min(periodo_meses, plazo_amortizacion_meses_item)

# Exclusión: ítems marcados como "excluir_sftp: true" no se incluyen
# (quirk documentado: SFTP excluido del CAPEX amortizado, tratado como costo operativo separado)
# plazo_amortizacion_meses_item viene del campo K167/K168 de la hoja CAPEX Excel (storage v2-7)
```

### 5.6 No Payroll

```
NoPayroll = honorarios + seguros_medicos + licencias_software + otros_sin_nomina

# Cada componente viene de parametros["hr"][rol]["no_payroll"] o ["op"]["no_payroll"]
# No aplica factor_prestaciones (no hay cargas sociales sobre honorarios)
```

### 5.7 ICA (Impuesto de Industria y Comercio)

```
Base_ICA = Nomina_total + CostosOperativos + CostosFinancieros + CAPEX_Amortizado + NoPayroll
ICA = Base_ICA × tasa_ica_municipio

# tasa_ica_municipio viene de business_rules["ica_por_municipio"][municipio]
# Ley 1819/2016: tarifa bimestral convertida a mensual por el motor
# Si municipio no está en el catálogo → excepción: 422 BUSINESS_RULE_VIOLATION
```

### 5.8 GMF (Gravamen a los Movimientos Financieros — 4×1000)

```
Base_GMF  = Nomina_total + CostosFinancieros
GMF = Base_GMF × tasa_gmf        # tasa_gmf = 0.004 (fija, regulatorio)
```

### 5.9 Pólizas

```
Polizas = valor_asegurado × tasa_poliza

# valor_asegurado = CostoTotal estimado antes de pólizas (iteración)
# tasa_poliza proviene de business_rules["tasa_poliza"] (pendiente C3 — placeholder 0.0)
# Si tasa_poliza = 0 → Polizas = 0 (no bloquea el cálculo)
```

### 5.10 Administración

```
Base_Admin = Nomina_total + CostosOperativos + CostosFinancieros + CAPEX_Amortizado + NoPayroll + ICA + GMF + Polizas
Admin = Base_Admin × comision_adm_pct       # comision_adm_pct = 0.0118 (1.18%)
```

### 5.11 Indexación

```
PrecioIndexado = CostoTotal × (1 + factor_indexacion)^periodos_indexacion

factor_indexacion   = IPC_proyectado + spread_negocio
periodos_indexacion = floor(periodo_meses / 12)

# Ejemplo: periodo_meses=18 → periodos_indexacion=1
# Ejemplo: periodo_meses=24 → periodos_indexacion=2
```

### 5.12 PYG Proyectado

```
Ingresos              = PrecioFinal × (volumen_operaciones / 1000)   # precio por millar si aplica
                      = PrecioFinal   # en modelo fijo

CostoTotal_sinMargen  = Nomina + CostosOp + CostosFinanc + CAPEX + NoPayroll + ICA + GMF + Polizas + Admin

EBITDA               = PrecioFinal - CostoTotal_sinMargen
EBITDA_pct           = EBITDA / PrecioFinal

Depreciacion         = Σ_item( capex_item / vida_util_meses_item )
Amortizacion         = Σ_item( activo_intangible_i / plazo_amort_i )

EBIT                 = EBITDA - Depreciacion - Amortizacion

GastosFinancieros    = CostosFinancieros   # intereses pagados
Utilidad_Antes_Imp   = EBIT - GastosFinancieros

Impuesto_Renta       = max(0, Utilidad_Antes_Imp) × tasa_impuesto_renta   # tasa = 0.33
Utilidad_Neta        = Utilidad_Antes_Imp - Impuesto_Renta
Utilidad_Neta_pct    = Utilidad_Neta / PrecioFinal
```

### 5.13 Factor Cadena y Canal

```python
FACTOR_CADENA = {
    "A": Decimal("1.00"),
    "B": Decimal("0"),     # placeholder C1
    "C": Decimal("0"),     # placeholder C2
}

FACTOR_CANAL = {
    "directo":  Decimal("1.00"),
    "canal_1":  Decimal(str(params["business_rules"]["factor_canal_1"])),
    "canal_2":  Decimal(str(params["business_rules"]["factor_canal_2"])),
}

# Se aplican como multiplicadores sobre CostoBase antes de calcular márgenes
# PrecioConFactores = CostoBase × FACTOR_CADENA[cadena] × FACTOR_CANAL[canal]
# Nota: si FACTOR_CADENA = 0, PrecioConFactores = 0 y se emite warning en metadata
```

---

## 6. Modelo de Datos Cosmos DB — Ejemplos Técnicos Completos

**API:** Core SQL  
**Consistency:** Session (default), Strong para `parameters` y `audit_log`

---

### 6.1 Containers

```
Database: pricing-simulator-prod

simulations    → /client_id         → autoscale 1000–10000 RU/s
parameters     → /version           → 400 RU/s fijo
audit_log      → /event_date        → autoscale 2000–20000 RU/s
certifications → /version           → 400 RU/s
clients        → /client_id         → 400 RU/s
```

---

### 6.2 Escritura en Cosmos DB — Código Python completo

```python
# azure_functions/shared/cosmos_client.py

import os
import logging
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Cliente singleton (reutilizado entre invocaciones de la Function)
_cosmos_client: CosmosClient | None = None
_container_simulations = None


def _get_client() -> CosmosClient:
    global _cosmos_client
    if _cosmos_client is None:
        endpoint = os.environ["COSMOS_ENDPOINT"]
        # Managed Identity — sin connection string, sin credenciales
        credential = DefaultAzureCredential()
        _cosmos_client = CosmosClient(url=endpoint, credential=credential)
    return _cosmos_client


async def get_simulations_container():
    global _container_simulations
    if _container_simulations is None:
        client = _get_client()
        db = client.get_database_client(os.environ["COSMOS_DATABASE"])
        _container_simulations = db.get_container_client("simulations")
    return _container_simulations


# ──────────────────────────────────────────────────
# GUARDAR una simulación
# ──────────────────────────────────────────────────

async def save_simulation(
    simulation_id: str,
    client_id: str,
    scenario: dict,
    result: dict,
    parametros_snapshot: dict,
    correlation_id: str,
    user_id_masked: str,
    ip_hash: str,
) -> dict:
    container = await get_simulations_container()

    now = datetime.now(timezone.utc).isoformat()

    # Convertir Decimal a float antes de persistir (Cosmos no soporta Decimal nativo)
    result_serializable = _serialize_decimals(result)

    document = {
        "id": simulation_id,                       # id único del documento
        "client_id": client_id,                    # partition key — Cosmos lo usa para routing
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "deleted_at": None,
        "version_parametros": parametros_snapshot["version"],
        "scenario": scenario,
        "parametros_snapshot": {
            "version": parametros_snapshot["version"],
            "snapshot": parametros_snapshot["content"],  # copia inmutable completa
        },
        "result": result_serializable,
        "audit": {
            "created_by": user_id_masked,
            "ip_hash": ip_hash,
            "correlation_id": correlation_id,
            "engine_version": os.environ.get("ENGINE_VERSION", "2.0.0"),
        },
        "idempotency_key": _compute_idempotency_key(client_id, scenario),
    }

    try:
        response = await container.create_item(
            body=document,
            # Cosmos SDK usa el partition key para dirigir el request al nodo correcto
            # Si no se especifica, lo lee del documento; explicitarlo mejora la latencia
        )
        logger.info(
            "simulation_saved",
            extra={
                "simulation_id": simulation_id,
                "client_id": client_id,
                "correlation_id": correlation_id,
                "request_charge_ru": response.get("_charge"),  # RUs consumidas
            },
        )
        return response

    except exceptions.CosmosResourceExistsError:
        # Idempotencia: ya existe, retornar el existente
        logger.warning("simulation_already_exists", extra={"simulation_id": simulation_id})
        return await container.read_item(item=simulation_id, partition_key=client_id)

    except exceptions.CosmosHttpResponseError as e:
        if e.status_code == 429:
            logger.error("cosmos_throttled", extra={"retry_after_ms": e.headers.get("x-ms-retry-after-ms")})
            raise  # El SDK reintenta automáticamente; si llega aquí es retry exhausto
        raise


def _serialize_decimals(obj: Any) -> Any:
    """Convierte recursivamente Decimal a float para serialización JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_decimals(i) for i in obj]
    return obj


def _compute_idempotency_key(client_id: str, scenario: dict) -> str:
    import hashlib, json
    payload = json.dumps({"client_id": client_id, "scenario": scenario}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
```

**Documento resultante en Cosmos DB (JSON real almacenado):**

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "client_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "completed",
  "created_at": "2026-05-29T10:00:00.123456+00:00",
  "completed_at": "2026-05-29T10:00:01.850000+00:00",
  "deleted_at": null,
  "version_parametros": "v2-7",
  "scenario": {
    "canal": "directo",
    "cadena": "A",
    "modelo_cobro": "fijo",
    "volumen_operaciones": 15000,
    "periodo_meses": 12,
    "moneda": "COP",
    "municipio": "BOGOTA"
  },
  "parametros_snapshot": {
    "version": "v2-7",
    "snapshot": {
      "business_rules": {
        "tasa_impuesto_renta": 0.33,
        "comision_adm_pct": 0.0118,
        "factor_indexacion_base": 0.035,
        "ipc_proyectado": 0.06,
        "spread_negocio": 0.025,
        "tasa_gmf": 0.004,
        "ica_por_municipio": { "BOGOTA": 0.01104 }
      }
    }
  },
  "result": {
    "precio_base": 120000000.0,
    "precio_final": 138500000.0,
    "desglose": {
      "nomina": 80000000.0,
      "costos_operativos": { "fijo": 15000000.0, "variable": 5000000.0, "subtotal": 20000000.0 },
      "costos_financieros": 5000000.0,
      "capex_amortizado": 10000000.0,
      "no_payroll": 5000000.0,
      "ica": 1200000.0,
      "gmf": 480000.0,
      "polizas": 0.0,
      "admin": 1490400.0,
      "margen": 15329600.0
    },
    "pyg": {
      "ingresos": 138500000.0,
      "costo_total": 123170400.0,
      "ebitda": 15329600.0,
      "ebitda_pct": 0.1107,
      "ebit": 14329600.0,
      "utilidad_antes_impuesto": 14329600.0,
      "impuesto_renta": 4727568.0,
      "utilidad_neta": 9602032.0,
      "utilidad_neta_pct": 0.0693
    },
    "metadata": {
      "engine_version": "2.0.0",
      "version_parametros": "v2-7",
      "factor_cadena": 1.0,
      "factor_canal": 1.0,
      "factor_indexacion_aplicado": 1.035,
      "periodos_indexacion": 1,
      "warnings": []
    }
  },
  "audit": {
    "created_by": "usr_***abc",
    "ip_hash": "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "engine_version": "2.0.0"
  },
  "idempotency_key": "a3f5bc7d2e1c9f8a4b6d0e2f7c5a1b3d",
  "_rid": "AbCdEfGhIjKl==",
  "_self": "dbs/pricing-simulator-prod/colls/simulations/docs/...",
  "_etag": "\"00005400-0000-0d00-0000-6838e1a00000\"",
  "_attachments": "attachments/",
  "_ts": 1748520000
}
```

---

### 6.3 Lectura de Cosmos DB — Código Python completo

```python
# ──────────────────────────────────────────────────
# OBTENER simulación por ID (point read — O(1), mínimo RU)
# ──────────────────────────────────────────────────

async def get_simulation(simulation_id: str, client_id: str) -> dict | None:
    """
    Point read: requiere id + partition_key.
    Consume exactamente 1 RU independiente del tamaño del documento.
    """
    container = await get_simulations_container()
    try:
        item = await container.read_item(
            item=simulation_id,
            partition_key=client_id,   # CRÍTICO: sin esto Cosmos hace fan-out a todas las particiones
        )
        if item.get("deleted_at") is not None:
            return None  # soft-deleted → tratar como no encontrado
        return item

    except exceptions.CosmosResourceNotFoundError:
        return None


# ──────────────────────────────────────────────────
# LISTAR simulaciones con cursor-based pagination
# ──────────────────────────────────────────────────

async def list_simulations(
    client_id: str,
    status: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page_size: int = 20,
    continuation_token: str | None = None,  # cursor opaco de Cosmos
) -> tuple[list[dict], str | None]:
    """
    Retorna (items, next_continuation_token).
    next_continuation_token es None si no hay más páginas.
    """
    container = await get_simulations_container()

    # Siempre filtrar por partition key para evitar cross-partition queries
    query = """
        SELECT
            c.id,
            c.client_id,
            c.status,
            c.created_at,
            c.completed_at,
            c.version_parametros,
            c.scenario,
            c.result.precio_final,
            c.result.metadata
        FROM c
        WHERE c.client_id = @client_id
          AND c.deleted_at = null
    """
    params = [{"name": "@client_id", "value": client_id}]

    if status:
        query += " AND c.status = @status"
        params.append({"name": "@status", "value": status})

    if from_date:
        query += " AND c.created_at >= @from_date"
        params.append({"name": "@from_date", "value": from_date})

    if to_date:
        query += " AND c.created_at <= @to_date"
        params.append({"name": "@to_date", "value": to_date})

    query += " ORDER BY c.created_at DESC"

    # El índice compuesto [status ASC, created_at DESC] cubre esta query eficientemente
    query_options = {
        "max_item_count": page_size,          # tamaño de página
        "enable_cross_partition_query": False, # forzar single-partition (tenemos WHERE client_id)
        "populate_query_metrics": True,        # para logging de RU consumidas
    }

    items = []
    next_token = None

    # SDK async iterator con soporte nativo de continuation token
    async for page in container.query_items(
        query=query,
        parameters=params,
        partition_key=client_id,          # single-partition query — mucho más barato en RU
        max_item_count=page_size,
        continuation_token=continuation_token,
    ).by_page(continuation_token=continuation_token):
        async for item in page:
            items.append(item)
        next_token = page.continuation_token   # None si es la última página
        break  # sólo la primera página en cada llamada

    return items, next_token


# ──────────────────────────────────────────────────
# SOFT-DELETE
# ──────────────────────────────────────────────────

async def soft_delete_simulation(simulation_id: str, client_id: str) -> bool:
    container = await get_simulations_container()
    now = datetime.now(timezone.utc).isoformat()

    try:
        # read_item para obtener _etag actual (optimistic concurrency)
        item = await container.read_item(item=simulation_id, partition_key=client_id)

        if item.get("deleted_at") is not None:
            return False  # ya borrado → 409

        item["deleted_at"] = now

        # replace_item con If-Match header → falla si alguien modificó concurrentemente
        await container.replace_item(
            item=simulation_id,
            body=item,
            match_condition={"if_match_etag": item["_etag"]},
        )
        return True

    except exceptions.CosmosResourceNotFoundError:
        return False
    except exceptions.CosmosAccessConditionFailedError:
        # Conflicto de concurrencia — reintentar o retornar 409
        raise


# ──────────────────────────────────────────────────
# IDEMPOTENCIA — buscar simulación existente en 60s
# ──────────────────────────────────────────────────

async def find_by_idempotency_key(
    client_id: str,
    idempotency_key: str,
    within_seconds: int = 60,
) -> dict | None:
    from datetime import timedelta

    container = await get_simulations_container()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()

    query = """
        SELECT TOP 1 *
        FROM c
        WHERE c.client_id = @client_id
          AND c.idempotency_key = @key
          AND c.created_at >= @cutoff
          AND c.deleted_at = null
        ORDER BY c.created_at DESC
    """
    params = [
        {"name": "@client_id", "value": client_id},
        {"name": "@key",       "value": idempotency_key},
        {"name": "@cutoff",    "value": cutoff},
    ]

    async for item in container.query_items(
        query=query, parameters=params, partition_key=client_id
    ):
        return item  # retorna el primero encontrado

    return None
```

---

### 6.4 Indexing Policy completa (container: simulations)

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    { "path": "/client_id/?" },
    { "path": "/status/?" },
    { "path": "/created_at/?" },
    { "path": "/deleted_at/?" },
    { "path": "/idempotency_key/?" },
    { "path": "/version_parametros/?" }
  ],
  "excludedPaths": [
    { "path": "/parametros_snapshot/*" },
    { "path": "/result/desglose/*" },
    { "path": "/result/pyg/*" },
    { "path": "/audit/ip_hash/?" },
    { "path": "/_etag/?" }
  ],
  "compositeIndexes": [
    [
      { "path": "/client_id",   "order": "ascending" },
      { "path": "/status",      "order": "ascending" },
      { "path": "/created_at",  "order": "descending" }
    ],
    [
      { "path": "/client_id",       "order": "ascending" },
      { "path": "/idempotency_key", "order": "ascending" },
      { "path": "/created_at",      "order": "descending" }
    ]
  ]
}
```

---

## 7. Código Técnico por Componente

### 7.1 Azure Function — Entry Point completo

```python
# azure_functions/simulations/create/__init__.py

import logging
import os
from uuid import uuid4
from datetime import datetime, timezone

import azure.functions as func
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor

from shared.auth import validate_jwt, extract_user_masked
from shared.cosmos_client import save_simulation, find_by_idempotency_key
from shared.key_vault import get_secret_cached
from shared.validator import validate_simulation_request
from shared.calculator import SimulationEngine
from shared.masking import mask_ip, compute_ip_hash
from shared.audit import write_audit_event

configure_azure_monitor(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
)
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    correlation_id = req.headers.get("X-Correlation-ID") or str(uuid4())

    with tracer.start_as_current_span("simulation.create") as span:
        span.set_attribute("correlation.id", correlation_id)

        # ── 1. Validar JWT ──────────────────────────────────────────────
        try:
            claims = await validate_jwt(
                token=req.headers.get("Authorization", "").removeprefix("Bearer "),
                required_scope="simulation.write",
                tenant_id=os.environ["ENTRA_TENANT_ID"],
                audience=os.environ["ENTRA_CLIENT_ID"],
            )
        except ValueError as e:
            return _error_response(401, "UNAUTHORIZED", str(e), correlation_id)

        user_id_masked = extract_user_masked(claims)
        client_ip      = req.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        ip_hash        = compute_ip_hash(client_ip)

        span.set_attribute("user.id_masked", user_id_masked)

        # ── 2. Parsear y validar body ───────────────────────────────────
        try:
            body = req.get_json()
        except ValueError:
            return _error_response(400, "VALIDATION_ERROR", "Body no es JSON válido", correlation_id)

        validation_errors = validate_simulation_request(body)
        if validation_errors:
            return _error_response(400, "VALIDATION_ERROR", "Payload inválido", correlation_id, details=validation_errors)

        client_id = body["client_id"]
        scenario  = body["scenario"]
        span.set_attribute("client.id", client_id)
        span.set_attribute("scenario.cadena", scenario["cadena"])

        # ── 3. Idempotencia ─────────────────────────────────────────────
        existing = await find_by_idempotency_key(client_id, _idempotency_key(client_id, scenario))
        if existing:
            logger.info("idempotent_hit", extra={"simulation_id": existing["id"], "correlation_id": correlation_id})
            return func.HttpResponse(
                body=_to_json(existing),
                status_code=200,
                headers={
                    "Content-Type": "application/json",
                    "X-Correlation-ID": correlation_id,
                    "X-Idempotent": "true",
                },
            )

        # ── 4. Cargar parámetros ────────────────────────────────────────
        version = body.get("version_parametros") or os.environ["PARAM_VERSION_DEFAULT"]
        params  = await _load_parameters(version)
        if params is None:
            return _error_response(422, "PARAM_VERSION_NOT_FOUND", f"Versión {version} no disponible", correlation_id)

        # ── 5. Ejecutar cálculo ─────────────────────────────────────────
        try:
            engine = SimulationEngine(params)
            result = engine.calculate(scenario)
        except ValueError as e:
            return _error_response(422, "BUSINESS_RULE_VIOLATION", str(e), correlation_id)

        span.set_attribute("result.precio_final", float(result["precio_final"]))

        # ── 6. Persistir en Cosmos DB ───────────────────────────────────
        simulation_id = str(uuid4())
        doc = await save_simulation(
            simulation_id=simulation_id,
            client_id=client_id,
            scenario=scenario,
            result=result,
            parametros_snapshot={"version": version, "content": params},
            correlation_id=correlation_id,
            user_id_masked=user_id_masked,
            ip_hash=ip_hash,
        )

        # ── 7. Audit log ────────────────────────────────────────────────
        await write_audit_event(
            event_type="simulation.created",
            resource_type="simulation",
            resource_id=simulation_id,
            actor_user_id_masked=user_id_masked,
            actor_ip_masked=mask_ip(client_ip),
            correlation_id=correlation_id,
        )

        # ── 8. Response ─────────────────────────────────────────────────
        response_body = {
            "simulation_id": simulation_id,
            "client_id": client_id,
            "status": "completed",
            "created_at": doc["created_at"],
            "completed_at": doc["completed_at"],
            "correlation_id": correlation_id,
            "version_parametros": version,
            "result": result,
        }

        return func.HttpResponse(
            body=_to_json(response_body),
            status_code=201,
            headers={
                "Content-Type": "application/json",
                "X-Correlation-ID": correlation_id,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Cache-Control": "no-store",
            },
        )


def _error_response(status: int, code: str, message: str, correlation_id: str, details=None) -> func.HttpResponse:
    import json
    body = {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if details:
        body["error"]["details"] = details
    return func.HttpResponse(
        body=json.dumps(body),
        status_code=status,
        headers={"Content-Type": "application/json", "X-Correlation-ID": correlation_id},
    )
```

---

### 7.2 Motor de cálculo — SimulationEngine

```python
# azure_functions/shared/calculator.py

from decimal import Decimal, ROUND_HALF_UP
import math


class SimulationEngine:
    def __init__(self, params: dict):
        self.br  = params["business_rules"]
        self.hr  = params.get("hr", {})
        self.op  = params.get("op", {})
        self.version = params["version"]

    def calculate(self, scenario: dict) -> dict:
        cadena   = scenario["cadena"]
        canal    = scenario["canal"]
        modelo   = scenario["modelo_cobro"]
        vol_ops  = Decimal(str(scenario["volumen_operaciones"]))
        periodos = int(scenario["periodo_meses"])
        municipio = scenario.get("municipio", "BOGOTA")

        factor_cadena = self._factor_cadena(cadena)
        factor_canal  = self._factor_canal(canal)

        warnings = []
        if factor_cadena == Decimal("0"):
            warnings.append(f"factor_cadena para cadena={cadena} es 0; precio resultante = 0")

        nomina             = self._calcular_nomina(cadena, canal, periodos)
        costos_op          = self._calcular_costos_operativos(cadena, canal, modelo, vol_ops, periodos)
        costos_financ      = self._calcular_costos_financieros(cadena, periodos)
        capex_amort        = self._calcular_capex_amortizado(cadena, periodos)
        no_payroll         = self._calcular_no_payroll(cadena, periodos)
        ica                = self._calcular_ica(nomina, costos_op, costos_financ, capex_amort, no_payroll, municipio)
        gmf                = self._calcular_gmf(nomina, costos_financ)
        polizas            = self._calcular_polizas(nomina, costos_op, costos_financ, capex_amort, no_payroll)
        base_admin         = nomina + costos_op["subtotal"] + costos_financ + capex_amort + no_payroll + ica + gmf + polizas
        admin              = (base_admin * Decimal(str(self.br["comision_adm_pct"]))).quantize(Decimal("0.01"), ROUND_HALF_UP)

        costo_total_sin_margen = base_admin + admin

        # Aplicar factores de cadena y canal
        costo_base = costo_total_sin_margen * factor_cadena * factor_canal

        # Indexación
        periodos_index = math.floor(periodos / 12)
        factor_index   = Decimal("1") + Decimal(str(self.br["ipc_proyectado"])) + Decimal(str(self.br["spread_negocio"]))
        precio_final   = (costo_base * (factor_index ** periodos_index)).quantize(Decimal("0.01"), ROUND_HALF_UP)

        # PYG
        pyg = self._calcular_pyg(precio_final, costo_total_sin_margen, cadena, periodos)

        return {
            "precio_base":  float(costo_base),
            "precio_final": float(precio_final),
            "desglose": {
                "nomina":              float(nomina),
                "costos_operativos":   {k: float(v) for k, v in costos_op.items()},
                "costos_financieros":  float(costos_financ),
                "capex_amortizado":    float(capex_amort),
                "no_payroll":          float(no_payroll),
                "ica":                 float(ica),
                "gmf":                 float(gmf),
                "polizas":             float(polizas),
                "admin":               float(admin),
                "margen":              float(precio_final - costo_total_sin_margen - admin),
            },
            "pyg": {k: float(v) if isinstance(v, Decimal) else v for k, v in pyg.items()},
            "metadata": {
                "engine_version":           "2.0.0",
                "version_parametros":       self.version,
                "factor_cadena":            float(factor_cadena),
                "factor_canal":             float(factor_canal),
                "factor_indexacion_aplicado": float(factor_index),
                "periodos_indexacion":      periodos_index,
                "warnings":                 warnings,
            },
        }

    def _factor_cadena(self, cadena: str) -> Decimal:
        return {"A": Decimal("1"), "B": Decimal("0"), "C": Decimal("0")}[cadena]

    def _factor_canal(self, canal: str) -> Decimal:
        mapping = {
            "directo":  Decimal("1"),
            "canal_1":  Decimal(str(self.br["factor_canal_1"])),
            "canal_2":  Decimal(str(self.br["factor_canal_2"])),
        }
        if canal not in mapping:
            raise ValueError(f"Canal '{canal}' no reconocido")
        return mapping[canal]

    def _calcular_nomina(self, cadena: str, canal: str, periodos: int) -> Decimal:
        total = Decimal("0")
        hr_sheets = self.hr.get("sheets", {})
        for rol, data in hr_sheets.items():
            n_empleados = Decimal(str(data.get("cantidad", 0)))
            salario     = Decimal(str(data.get("salario_base", 0)))
            fp          = Decimal(str(data.get("factor_prestaciones", 1.521)))
            # RN-009: Director y GTR comision_pct = 0
            com_pct = Decimal("0") if rol in ("Director", "GTR") else Decimal(str(self.br.get("com_vendedor_pct", 0)))
            comision    = salario * com_pct
            total      += n_empleados * (salario * fp + comision) * periodos
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_costos_operativos(self, cadena, canal, modelo, vol_ops, periodos) -> dict:
        op_data = self.op.get("sheets", {}).get(cadena, {}).get(canal, {})
        overhead   = Decimal(str(op_data.get("overhead_mensual", 0)))
        costo_op_u = Decimal(str(op_data.get("costo_por_operacion", 0)))

        if modelo == "fijo":
            fijo = overhead * periodos; variable = Decimal("0")
        elif modelo == "variable":
            fijo = Decimal("0"); variable = costo_op_u * vol_ops
        else:  # mixto
            fijo = Decimal(str(op_data.get("componente_fijo", 0))) * periodos
            variable = costo_op_u * vol_ops

        return {
            "fijo":     fijo.quantize(Decimal("0.01"), ROUND_HALF_UP),
            "variable": variable.quantize(Decimal("0.01"), ROUND_HALF_UP),
            "subtotal": (fijo + variable).quantize(Decimal("0.01"), ROUND_HALF_UP),
        }

    def _calcular_costos_financieros(self, cadena: str, periodos: int) -> Decimal:
        total = Decimal("0")
        tasa_m = Decimal(str(self.br.get("tasa_mensual_financ", 0.01)))
        capex_items = self.hr.get("capex_items", []) + self.op.get("capex_items", [])
        for item in capex_items:
            if item.get("cadena") and item["cadena"] != cadena:
                continue
            monto = Decimal(str(item["monto"]))
            plazo = int(item.get("plazo_meses", periodos))
            factor = (Decimal("1") + tasa_m) ** plazo
            total += monto * (factor - Decimal("1"))
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_capex_amortizado(self, cadena: str, periodos: int) -> Decimal:
        total = Decimal("0")
        capex_items = self.hr.get("capex_items", []) + self.op.get("capex_items", [])
        for item in capex_items:
            if item.get("excluir_sftp"):  # RN quirk SFTP
                continue
            if item.get("cadena") and item["cadena"] != cadena:
                continue
            monto  = Decimal(str(item["monto"]))
            plazo  = int(item.get("plazo_amortizacion_meses", 36))
            meses  = min(periodos, plazo)
            total += (monto / plazo) * meses
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_no_payroll(self, cadena: str, periodos: int) -> Decimal:
        total = Decimal("0")
        for rol, data in self.hr.get("sheets", {}).items():
            np_mensual = Decimal(str(data.get("no_payroll_mensual", 0)))
            n_empleados = Decimal(str(data.get("cantidad", 0)))
            total += np_mensual * n_empleados * periodos
        total += Decimal(str(self.op.get("no_payroll_fijo_mensual", 0))) * periodos
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_ica(self, nomina, costos_op, costos_financ, capex_amort, no_payroll, municipio) -> Decimal:
        tasa = Decimal(str(self.br["ica_por_municipio"].get(municipio, 0)))
        if tasa == 0:
            raise ValueError(f"Municipio '{municipio}' no tiene tasa ICA configurada")
        base = nomina + costos_op["subtotal"] + costos_financ + capex_amort + no_payroll
        return (base * tasa).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_gmf(self, nomina: Decimal, costos_financ: Decimal) -> Decimal:
        tasa = Decimal(str(self.br["tasa_gmf"]))
        return ((nomina + costos_financ) * tasa).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_polizas(self, *args) -> Decimal:
        tasa = Decimal(str(self.br.get("tasa_poliza", 0)))
        base = sum(a if isinstance(a, Decimal) else a["subtotal"] for a in args)
        return (base * tasa).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _calcular_pyg(self, precio_final, costo_total, cadena, periodos) -> dict:
        tasa_ir = Decimal(str(self.br["tasa_impuesto_renta"]))
        ebitda  = precio_final - costo_total
        dep     = self._calcular_capex_amortizado(cadena, periodos)
        ebit    = ebitda - dep
        cf      = self._calcular_costos_financieros(cadena, periodos)
        uai     = ebit - cf
        imp     = max(Decimal("0"), uai) * tasa_ir
        un      = uai - imp
        return {
            "ingresos":                 precio_final,
            "costo_total":              costo_total,
            "ebitda":                   ebitda,
            "ebitda_pct":               float((ebitda / precio_final).quantize(Decimal("0.0001"))) if precio_final else 0,
            "ebit":                     ebit,
            "utilidad_antes_impuesto":  uai,
            "impuesto_renta":           imp,
            "utilidad_neta":            un,
            "utilidad_neta_pct":        float((un / precio_final).quantize(Decimal("0.0001"))) if precio_final else 0,
        }
```

---

### 7.3 Key Vault — Caché de secretos

```python
# azure_functions/shared/key_vault.py

import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from azure.keyvault.secrets.aio import SecretClient
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[str, datetime]] = {}  # { nombre: (valor, expira_en) }
_lock = asyncio.Lock()
_CACHE_TTL_HOURS = 24  # secretos se cachean 24h en memoria de la Function


async def get_secret_cached(secret_name: str) -> str:
    async with _lock:
        if secret_name in _cache:
            value, expires_at = _cache[secret_name]
            if datetime.now(timezone.utc) < expires_at:
                return value
            del _cache[secret_name]

    # Cache miss → consultar Key Vault
    vault_url = os.environ["KEY_VAULT_URL"]  # ej: https://pricing-sim-prod-kv.vault.azure.net
    credential = DefaultAzureCredential()

    async with SecretClient(vault_url=vault_url, credential=credential) as client:
        secret = await client.get_secret(secret_name)
        value  = secret.value

    async with _lock:
        _cache[secret_name] = (value, datetime.now(timezone.utc) + timedelta(hours=_CACHE_TTL_HOURS))

    logger.info("secret_fetched_from_keyvault", extra={"secret_name": secret_name})
    return value
```

---

### 7.4 Auditoría — Escritura con firma RSA

```python
# azure_functions/shared/audit.py

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.keys.aio import KeyClient
from azure.keyvault.keys.crypto.aio import CryptographyClient
from azure.keyvault.keys.crypto import SignatureAlgorithm

logger = logging.getLogger(__name__)


async def write_audit_event(
    event_type: str,
    resource_type: str,
    resource_id: str,
    actor_user_id_masked: str,
    actor_ip_masked: str,
    correlation_id: str,
    extra_data: dict | None = None,
) -> None:
    now  = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")

    event = {
        "id":           str(uuid4()),
        "event_date":   date,              # partition key
        "timestamp":    now.isoformat(),
        "event_type":   event_type,
        "actor": {
            "user_id":        actor_user_id_masked,
            "ip":             actor_ip_masked,
        },
        "resource": {
            "type": resource_type,
            "id":   resource_id,
        },
        "correlation_id": correlation_id,
        "extra":          extra_data or {},
    }

    # Calcular hash del contenido
    event_json    = json.dumps(event, sort_keys=True)
    payload_hash  = hashlib.sha256(event_json.encode()).hexdigest()
    event["payload_hash"] = f"sha256:{payload_hash}"

    # Firmar con clave RSA-2048 en Key Vault (garantiza no repudio)
    integrity_hash = await _sign_with_key_vault(payload_hash)
    event["integrity_hash"] = integrity_hash

    # Escribir en Cosmos DB (Strong consistency)
    credential = DefaultAzureCredential()
    client     = CosmosClient(url=os.environ["COSMOS_ENDPOINT"], credential=credential)
    container  = client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("audit_log")

    await container.create_item(body=event)
    logger.info("audit_event_written", extra={"event_type": event_type, "event_id": event["id"]})


async def _sign_with_key_vault(payload_hash: str) -> str:
    """Firma SHA-256 del payload con RSA-2048 en Key Vault HSM."""
    vault_url  = os.environ["KEY_VAULT_URL"]
    key_name   = os.environ["AUDIT_SIGNING_KEY_NAME"]  # pricing-sim-signing-key-prod
    credential = DefaultAzureCredential()

    async with KeyClient(vault_url=vault_url, credential=credential) as kc:
        key = await kc.get_key(key_name)

    async with CryptographyClient(key, credential=credential) as cc:
        digest  = bytes.fromhex(payload_hash)
        result  = await cc.sign(SignatureAlgorithm.rs256, digest)
        return f"rsa256:{result.signature.hex()}"
```

---

## 8. Observabilidad — Instrumentación

### 8.1 Propagación de Correlation ID

```python
# azure_functions/shared/telemetry.py

from opentelemetry import trace, baggage
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
import azure.functions as func

def extract_correlation_id(req: func.HttpRequest) -> str:
    """
    Extrae o genera el Correlation ID.
    Prioridad: X-Correlation-ID header → W3C traceparent → genera nuevo UUID.
    """
    if cid := req.headers.get("X-Correlation-ID"):
        return cid
    ctx = TraceContextTextMapPropagator().extract(dict(req.headers))
    span = trace.get_current_span(ctx)
    if span.is_recording():
        return format(span.get_span_context().trace_id, '032x')
    from uuid import uuid4
    return str(uuid4())


def attach_correlation_to_span(span, correlation_id: str, client_id: str = None):
    span.set_attribute("correlation.id",  correlation_id)
    span.set_attribute("http.correlation_id", correlation_id)
    if client_id:
        span.set_attribute("client.id", client_id)
    # NO añadir datos PII al span
```

### 8.2 Alertas críticas

| Alerta | Condición | Severidad | Acción |
|--------|-----------|-----------|--------|
| Latencia P95 > 2s | 5 minutos consecutivos | P2 | Teams + PagerDuty |
| Error rate 5xx > 1% | 10 minutos | P1 | PagerDuty inmediato |
| Cosmos throttling | > 10 errores 429/min | P2 | Autoscale RU + alerta |
| Key Vault failure | Cualquier error de acceso | P1 | PagerDuty inmediato |
| WAF blocks spike | > 50 blocks/min | P2 | SOC notification |
| Certificación fallida | score < 100% | P1 | Bloquear deploy pipeline |
| Audit log write failure | Cualquier error | P1 | PagerDuty + rollback |

---

## 9. Política de Gestión de Cambios

### 9.1 Clasificación de cambios

| Tipo | Definición | Aprobación |
|------|-----------|------------|
| **Standard** | Cambio documentado, bajo riesgo, probado en dev | Tech Lead |
| **Normal** | Nuevo feature, cambio de infraestructura | Tech Lead + Arquitecto |
| **Emergency** | Hotfix P1/P0 en producción | On-call + CTO, post-registro obligatorio |
| **Prohibido** | Cambio directo en prod sin pipeline | Bloqueado por Branch Protection en git |

### 9.2 Pipeline CI/CD

```
Branch Strategy: GitFlow
  main        → producción  (protegida: require 2 PR reviews + status checks)
  develop     → integración continua
  release/*   → pre-producción
  hotfix/*    → correcciones urgentes (merge a main Y develop)

Pipeline completo (PR → main):

  Stage 1 — Calidad de código:
    ├── pytest (unit + integration)
    ├── ruff (linting)
    ├── mypy (type checking)
    ├── bandit (SAST Python)
    └── safety check (vulnerabilidades en dependencias)

  Stage 2 — Deploy DEV:
    ├── az functionapp deployment → pricing-sim-dev
    ├── Integration tests vs Cosmos DB DEV
    └── Parity certification suite (score debe = 100%)

  Stage 3 — SAST/DAST:
    ├── SonarCloud scan (quality gate: 0 critical, 0 blocker)
    └── OWASP ZAP scan vs endpoint DEV

  Stage 4 — Aprobación manual:
    └── GitHub Environments protection rule: Arquitecto + Tech Lead

  Stage 5 — Deploy PROD (Blue/Green):
    ├── Deploy a slot "staging" de Functions
    ├── Smoke tests automatizados contra slot staging (30 requests)
    ├── Slot swap (staging → production) — < 1s downtime
    └── Rollback automático si smoke tests fallan post-swap

  Stage 6 — Verificación post-deploy:
    ├── Smoke tests en producción (5 minutos)
    ├── Monitor latency P95 (10 minutos)
    └── Notificación Teams/Slack con summary
```

### 9.3 Gestión de parámetros del simulador

```
Flujo de cambio de parámetros (business_rules, HR, OP):

  1. Preparar nuevo archivo JSON con versión v2-N+1
  2. POST /parameters → status: draft
  3. POST /certifications → certificar vs. oracle Excel
  4. Esperar status: passed (score = 100% obligatorio)
  5. Primer aprobador: PATCH /parameters/v2-N+1 { "status": "pending_countersign" }
  6. Segundo aprobador: PATCH /parameters/v2-N+1 { "countersign_token": "..." }
  7. Sistema activa automáticamente y depreca versión anterior
  8. audit_log recibe evento param.version.activated con ambas firmas
```

---

## 10. Plan de Pruebas de Intrusión (Pentesting)

### 10.1 Alcance

```
Ambiente:  Pre-producción (espejo exacto de prod, datos 100% sintéticos)
Tipos:     Black Box → Grey Box → White Box (secuencial)
Ejecutor:  Firma certificada externa (CREST / OSCP)
```

### 10.2 Vectores de prueba

**A — Perimetral**
```
[ ] Enumeración de subdominios y endpoints expuestos
[ ] Downgrade TLS (1.0/1.1), BEAST, POODLE, CRIME
[ ] Certificate pinning validation
[ ] HTTP Request Smuggling
[ ] Host Header Injection → SSRF interno
[ ] DNS rebinding
```

**B — Autenticación y Autorización**
```
[ ] JWT: algoritmo "none", weak HMAC brute force, expired token replay
[ ] OAuth 2.1: authorization code injection, open redirect en redirect_uri
[ ] IDOR: acceder a simulation de otro client_id cambiando UUID en path
[ ] Privilege escalation: usar scope simulation.read para llamar parámetros.write
[ ] SSRF a través de campos URL en body (ej: oracle_blob_path)
[ ] Mass assignment: campos extra en body que sobrescriban campos internos
[ ] Replay de countersign_token para activar parámetros sin segundo aprobador
```

**C — Inyección y WAF Bypass**
```
[ ] NoSQL Injection en queries Cosmos DB: { "$where": "..." }, operadores Mongo si aplica
[ ] Path Traversal en oracle_blob_path → acceso a blobs de otro tenant
[ ] SSTI en generación de reportes PDF/HTML
[ ] Command Injection en campos procesados por subprocesos
[ ] WAF evasion: encoding UTF-8, chunked encoding, Unicode normalization, case folding
[ ] ReDoS en validaciones regex del simulador (payloads de hasta 50k chars)
[ ] Large payload: bodies > 10MB para agotar memoria de Functions
```

**D — Lógica de Negocio**
```
[ ] Overflow numérico: volumen_operaciones = 2^63, periodo_meses = 9999
[ ] Valores negativos en campos numéricos
[ ] Forzar cadena B/C y verificar que precio = 0 (no excepción expuesta)
[ ] Idempotency key collision: fabricar mismo hash con payload diferente
[ ] Timing attack en validación JWT (comparación de strings)
[ ] Bypass de rate limiting mediante múltiples IPs, rotation de JWT sub
[ ] Cancelar simulación async en mitad → verificar estado consistente en Cosmos
[ ] Explotar ventana de 60s de idempotencia para robar resultado ajeno
```

**E — Infraestructura Azure**
```
[ ] SSRF al metadata service: 169.254.169.254 para robar Managed Identity token
[ ] Acceso directo a Functions endpoint sin pasar por APIM (bypass de policies)
[ ] Acceso directo a Cosmos DB desde internet (debe estar detrás de Private Endpoint)
[ ] Blob Storage: acceso anónimo a containers, URL directa sin SAS
[ ] Key Vault: enumeration sin permisos (listar secret names)
[ ] Reutilizar SAS token expirado de Blob
[ ] Cross-tenant JWT (token de otro tenant/audience)
```

**F — Datos y Privacidad**
```
[ ] Stack traces en response de error (deben ser genéricos)
[ ] Connection strings o secrets en logs de Application Insights
[ ] PII (nit, email) en claro en audit_log queries
[ ] Datos sensibles en HTTP response headers
[ ] Verificar masking en TODOS los endpoints de auditoría
[ ] Cifrado at-rest: verificar que Cosmos DB usa CMK (Key Vault) y no Microsoft-managed keys
```

### 10.3 Criterios de aceptación para go-live

| Severidad | Criterio |
|-----------|---------|
| Crítica — RCE, bypass auth total, exposición de secretos | 0 hallazgos abiertos |
| Alta — IDOR, privilege escalation, NoSQLi exitoso | 0 hallazgos abiertos |
| Media — SSRF limitado, PII en logs, XSS persistente | 0 hallazgos abiertos |
| Baja — headers faltantes, verbose error messages | Plan de remediación < 30 días (no bloquea go-live) |

### 10.4 Entregables del pentesting

- Reporte ejecutivo sin tecnicismos (para dirección)
- Reporte técnico con PoC por hallazgo, CVSS v3.1 score, evidencia
- Plan de remediación priorizado con owner y fecha
- Certificado de seguridad firmado post-retesting (condición para go-live)

---

## 11. Decisiones Arquitectónicas (ADR)

| ID | Decisión | Alternativa descartada | Razón |
|----|---------|----------------------|-------|
| ADR-001 | Cosmos DB Core SQL API | MongoDB API | Queries tipadas SQL, SDK Python estable, indexing policy granular, RBAC nativo |
| ADR-002 | Flex Consumption plan | Premium plan | Escala a 0 en dev/noche, sin límite de burst, pre-warm = 1 elimina cold start en prod |
| ADR-003 | System-assigned Managed Identity | User-assigned MI | Ciclo de vida ligado a la Function; menor superficie de gestión de identidades |
| ADR-004 | Session consistency en simulations | Strong consistency | Costo RU 2x en Strong; Session garantiza que el caller ve sus propios writes |
| ADR-005 | Strong consistency en parameters y audit_log | Session | Datos críticos: no aceptable que un reader vea versión stale de parámetros activos |
| ADR-006 | Cursor-based pagination | Offset-based (SKIP/TOP) | SKIP en Cosmos cobra RU por documentos saltados; cursor es O(1) en costo |
| ADR-007 | Soft-delete en simulations | Hard-delete | Obligación regulatoria retención 5 años; integridad de auditoría no interrumpible |
| ADR-008 | Partition key /client_id en simulations | /id | Queries de lista por cliente en single-partition; /id forzaría cross-partition o lookup previo |
| ADR-009 | Firma RSA-2048 de audit events en Key Vault HSM | Hash SHA-256 sin firma | Garantiza no repudio y detección de alteración; requerimiento regulatorio de logs íntegros |
| ADR-010 | Decimal para todos los cálculos financieros | float | float IEEE 754 acumula error de redondeo en operaciones encadenadas; Decimal es exacto |