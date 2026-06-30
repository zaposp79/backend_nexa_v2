# NEXA Architecture Documentation Index

**Versión:** 1.0  
**Fecha:** 31 de mayo de 2026  
**Estado:** Aprobado para revisión técnica

---

## Resumen Ejecutivo

Este índice cataloga los documentos arquitectónicos principales de NEXA, un motor de simulación de costos y precios para servicios de TI que utiliza Clean Architecture + Domain-Driven Design, versionado inmutable y modos certificados.

**Scope Total:** ~13,000 palabras (30–40 páginas según formato de impresión)

---

## Documentos Incluidos

### 1. CHAPTER 2: "Arquitectura de Software"

**Ubicación:** `/docs/CHAPTER_2_ARQUITECTURA_SOFTWARE.md`  
**Extensión:** ~2,850 palabras (7–8 páginas)  
**Audiencia:** Arquitectos, desarrolladores, tech leads

**Contenido:**

- **SECTION 2.1: Estilo Arquitectónico**
  - Clean Architecture (Ports & Adapters)
  - Domain-Driven Design (DDD)
  - Principios clave (inversión de dependencias, statelessness, inmutabilidad)

- **SECTION 2.2: Desglose por Capas**
  - Domain Layer (modelos, servicios, calculadores, value objects)
  - Application Layer (use cases, orchestrators, ports, versioning, lineage)
  - Infrastructure Layer (parametrization loaders, repositories)
  - API Layer (REST endpoints, DTOs, adapters)

- **SECTION 2.3: Dependencias entre Módulos**
  - Dependency graph (10-layer pipeline)
  - Isolation properties (layers 2-5 paralelizables)
  - Coupling metrics por layer

- **SECTION 2.4: Patrones de Diseño**
  - Factory (SimulationContextBuilder, PricingPipeline)
  - Strategy (CargoClassifier, pluggable billing models)
  - Builder (Vision builders, LineageBuilder)
  - Repository (ParametrizationProvider, FrozenParametrizationAdapter)
  - Adapter (pricing_serializer)
  - Template Method (Calculator interface)
  - Immutable Value Object (VersionMetadata, LineageNode)

- **SECTION 2.5: Flujo de Datos End-to-End**
  - Request → Processing → Response
  - Complete lifecycle con timestamps y transformaciones
  - Data structures en cada stage

**Valor:** Proporciona mapa mental completo de la arquitectura interna, justifica decisiones de diseño, establece convenciones de código.

---

### 2. CHAPTER 9: "Versionado y Modos Certificados"

**Ubicación:** `/docs/CHAPTER_9_VERSIONADO_MODOS_CERTIFICADOS.md`  
**Extensión:** ~2,650 palabras (7–8 páginas)  
**Audiencia:** Arquitectos, desarrolladores, auditores, compliance

**Contenido:**

- **SECTION 9.1: Registro Central de Versiones**
  - VersionRegistry (fuente única de verdad)
  - VersionMetadata (snapshot inmutable)
  - Estructura de almacenamiento (storage/parametrization/)
  - API del registry

- **SECTION 9.2: Modo Certificado**
  - Flujo de cálculo certificado (determinístico)
  - ExecutionCertificate (proof of reproducibility)
  - Baseline Validation endpoint
  - Garantías de reproducibilidad (hash integrity)

- **SECTION 9.3: Versionado de Parametrización**
  - Módulos independientes (HR, GN, OP, Business Rules)
  - Drift Detection (SHA-256 comparison)
  - Backward Compatibility (carga de versiones antiguas)

- **SECTION 9.4: Lineage & Audit Trail**
  - LineageGraph (grafo acíclico dirigido de cálculo)
  - LineageNode (nodo individual de cálculo)
  - LineageRef (referencia a origen: request, parametrization, Excel, computed)
  - LineageSnapshotRepository (persistencia)
  - Ejemplo: Traza de ingreso neto (5 pasos)

- **SECTION 9.5: Migración & Rollback de Versiones**
  - Forward migration (v1 → v2, parity testing)
  - Rollback (v2 → v1 si hay bugs críticos)
  - No data loss (full audit trail)
  - Testing de reproducibilidad

**Valor:** Garantiza conformidad regulatoria, permite auditoría completa del cálculo, facilita debugging y retracing.

---

### 3. CHAPTER 10: "Arquitectura Azure Objetivo"

**Ubicación:** `/docs/CHAPTER_10_ARQUITECTURA_AZURE_OBJETIVO.md`  
**Extensión:** ~3,300 palabras (9–10 páginas)  
**Audiencia:** Arquitectos cloud, DevOps, product managers, CFO

**Contenido:**

- **SECTION 10.1: Visión General de Arquitectura Cloud**
  - Estado actual (on-prem monolito) vs. objetivo (serverless)
  - Arquitectura de alto nivel (5 componentes principales)
  - Principios de diseño (stateless, global data, immutable snapshots)

- **SECTION 10.2: Componentes Azure & Responsabilidades**
  1. Azure API Management (APIM)
     - Gateway REST v1 (autenticación, throttling, versioning)
     - Rate limiting: 1000 req/min por cliente
     - Costo: $150/mes
  
  2. Azure Functions (Compute)
     - 5 funciones serverless (Python 3.9+)
     - CalculateSimulation (10-layer pipeline)
     - RetrieveResults, AuditSimulation, ListVersions, VerifyCertificate
     - Auto-scaling 0–1000 instancias
     - Costo: $300–600/mes
  
  3. Azure Cosmos DB (Data)
     - Multi-región (East US, West Europe, Southeast Asia)
     - 5 collections (simulations, parametrization, baselines, certificates, audit_logs)
     - TTL: 90 días simulations, 365 días certificates
     - RTO < 5 min, RPO < 1 min
     - Costo: $500/mes
  
  4. Azure Storage (Persistence)
     - Parametrization snapshots
     - Lineage graphs (best-effort)
     - Backups, logs
     - Costo: $50/mes
  
  5. Azure Key Vault (Secrets)
     - Managed Identity (no secrets en código)
     - Costo: $10/mes
  
  6. Azure Monitor + AppInsights (Observability)
     - Métricas, logs, traces, alertas
     - KPI dashboards (real-time ops, performance, costs)
     - Costo: $70–150/mes

- **SECTION 10.3: Flujo de Datos & Scaling**
  - Request flow completo (8 pasos, 3.5s latency)
  - Escalabilidad horizontal (request rate vs. instances)
  - Escalabilidad vertical (single request, memory)
  - Escalabilidad de DB (RU/s consumption)
  - Paralelización (layers 2-5 en 4 threads)

- **SECTION 10.4: Seguridad & Cumplimiento**
  - OAuth 2.0 + Azure AD
  - RBAC (Viewer, Operator, Admin)
  - Encryption at rest (AES-256)
  - Encryption in transit (TLS 1.2+)
  - Secrets management (Key Vault + Managed Identity)
  - SOC 2 Type II, GDPR, Financial Audit compliance

- **SECTION 10.5: Estimación de Costos**
  - Monthly production: ~$861/mes (optimizado: $600–700/mes)
  - Dev/staging: ~$60–70/mes
  - Cost optimization strategies (reserved instances, spot compute)

- **SECTION 10.6: Ruta de Migración**
  - Phase 1 (Month 1): Setup infrastructure, parallel run
  - Phase 2 (Month 2): Migrate remaining endpoints
  - Phase 3 (Month 3): Observability & optimization
  - Phase 4 (Month 4): Production cutover

- **SECTION 10.7: Alta Disponibilidad & Disaster Recovery**
  - Multi-región replication
  - Failover mechanics (< 5 min RTO)
  - Backup & restore procedures
  - RTO/RPO targets

**Valor:** Roadmap ejecutivo para transformación a cloud, estimación realista de costos, estrategia de despliegue por fases.

---

### 4. AZURE_TARGET_ARCHITECTURE.md (Technical Reference)

**Ubicación:** `/docs/AZURE_TARGET_ARCHITECTURE.md`  
**Extensión:** ~4,100 palabras (11–12 páginas)  
**Audiencia:** Cloud architects, DevOps, SRE, system engineers

**Contenido Adicional (más detallado que CHAPTER 10):**

- **Diagrama detallado de flujo de solicitud** (15 pasos con timestamps)
- **Configuración XML de APIM policies** (autenticación, rate limiting, routing)
- **Código Python de Functions** (CalculateSimulation, RetrieveResults, etc.)
- **Cosmos DB documento examples** (simulations, parametrization, baselines, certificates)
- **Network configuration** (VNet, NSG rules, private endpoints)
- **Logging strategy** (3 levels: request/response, calculation stages, external ops)
- **Distributed tracing** (Application Insights spans, per-layer timing)
- **Secrets management** (Key Vault access patterns, Managed Identity)
- **Phase-by-phase deployment** con comandos Azure CLI/Terraform
- **GitHub Actions CI/CD pipeline** (test → build → deploy)
- **Runbooks** (error diagnostics, disaster recovery)
- **Performance benchmark results** (2.5s para 120-month contract, 1.68x speedup paralelización)
- **Appendices:**
  - Terraform IaC (main.tf, providers, resources)
  - GitHub Actions workflow
  - Diagnostic runbook
  - Disaster recovery runbook

**Valor:** Implementación táctica lista para pasar a equipo cloud/DevOps, configuraciones copypaste, runbooks para production support.

---

## Matriz de Cobertura

| Tema | CHAPTER 2 | CHAPTER 9 | CHAPTER 10 | AZURE_REF |
|------|-----------|-----------|-----------|-----------|
| Clean Architecture | ✓ | — | — | — |
| Inversión Dependencias | ✓ | — | — | — |
| 10-Layer Pipeline | ✓ | — | ✓ | — |
| VersionRegistry | — | ✓ | — | ✓ |
| Certified Mode | — | ✓ | ✓ | ✓ |
| Lineage & Audit | — | ✓ | ✓ | ✓ |
| APIM Config | — | — | ✓ | ✓ |
| Cosmos DB Schema | — | — | ✓ | ✓ |
| Observability | — | — | ✓ | ✓ |
| Cost Estimation | — | — | ✓ | ✓ |
| Migration Phases | — | — | ✓ | — |
| Runbooks & IaC | — | — | — | ✓ |
| Disaster Recovery | — | — | ✓ | ✓ |

---

## Guía de Lectura por Audiencia

### Para Arquitectos de Software

1. CHAPTER 2 (completo) — entender estructura interna
2. CHAPTER 9 §9.1–9.4 — versioning + lineage patterns
3. CHAPTER 10 §10.1–10.2 — componentes Azure

### Para Desarrolladores

1. CHAPTER 2 (completo) — principios de diseño
2. CHAPTER 9 (completo) — cómo versioning afecta código
3. AZURE_TARGET_ARCHITECTURE §2–3 — código de Functions
4. AZURE_TARGET_ARCHITECTURE Appendix A–B — IaC + CI/CD

### Para Product Managers / Stakeholders

1. CHAPTER 10 §10.1 (resumen ejecutivo)
2. CHAPTER 10 §10.5 (estimación de costos)
3. CHAPTER 10 §10.6 (ruta de migración)
4. CHAPTER 9 §9.2 (certified mode = audit trail)

### Para Cloud/DevOps Engineers

1. CHAPTER 10 (completo)
2. AZURE_TARGET_ARCHITECTURE (completo)
3. Focus: Appendices A–D (Terraform, GitHub Actions, runbooks)

### Para QA/Testing

1. CHAPTER 2 §2.4 — patrones testeable
2. CHAPTER 9 (completo) — reproducibilidad certificada
3. AZURE_TARGET_ARCHITECTURE §Benchmark results — baseline de performance

### Para Auditores / Compliance

1. CHAPTER 9 (completo) — immutable versioning + lineage
2. CHAPTER 10 §10.4 — security + compliance certs
3. AZURE_TARGET_ARCHITECTURE §Logging strategy — audit trail mechanisms

---

## Convenciones de Documentación

### Formato de Código

```python
# Python: production code
class NexaPricingEngine:
    def calcular(self, request: PricingRequest) -> PricingResult:
        ...
```

```xml
<!-- XML: Azure APIM policies -->
<policies>
  <validate-jwt ... />
</policies>
```

```bash
# Bash: deployment commands
az deployment group create ...
```

```hcl
# HCL: Terraform IaC
resource "azurerm_cosmosdb_account" "nexa" {
  ...
}
```

### Notación de Diagramas

```
┌─────────────┐
│   Layer 1   │
└──────┬──────┘
       │
┌──────▼──────┐
│   Layer 2   │
└──────┬──────┘
```

### Tablas de Decisión

| Criterio | Opción A | Opción B | Elegido |
|----------|----------|----------|---------|
| Costo | Alto | Bajo | B |
| Complejidad | Baja | Alta | A |
| **Decisión** | — | — | **A** |

---

## Próximas Fases Documentales

**Previsto (no incluido en este entregable):**

1. **CHAPTER 1: Visión & Principios** (ejecutivo, requerimientos)
2. **CHAPTER 3–8: Detalles técnicos por dominio** (payroll, financial, P&G, risk, etc.)
3. **CHAPTER 11: Monitoreo & SLAs** (KPIs, alerting, runbooks)
4. **CHAPTER 12: API Reference** (OpenAPI/Swagger v1)
5. **CHAPTER 13: Testing & QA** (test strategy, coverage goals)
6. **CHAPTER 14: Operaciones & Runbooks** (troubleshooting, escalation)

---

## Control de Cambios

| Versión | Fecha | Autor | Cambios |
|---------|-------|-------|---------|
| 0.1 | 2026-05-25 | Drafting | Outline estructurado |
| 0.5 | 2026-05-28 | CHAPTER 2 draft | Arquitectura software completa |
| 0.7 | 2026-05-29 | CHAPTER 9 draft | Versioning + lineage |
| 0.9 | 2026-05-30 | CHAPTER 10 draft | Azure architecture overview |
| 1.0 | 2026-05-31 | All chapters + Azure ref | Release para revisión técnica |

---

## Contacto & Preguntas

**Propietario arquitectónico:** NEXA Architecture Team  
**Repositorio código:** [GitHub NEXA]  
**Wiki/Confluence:** [Link]  
**Slack channel:** #nexa-architecture  

---

**Documento final: 4 capítulos + 1 referencia técnica = ~13,000 palabras, 30–40 páginas**

