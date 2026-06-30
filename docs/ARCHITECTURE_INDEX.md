# NEXA Architecture Documentation Index

**Status**: Under active development (FASE 1-8)  
**Target Completion**: June 2026  
**Last Updated**: 2026-05-31

---

## 📋 Deliverables Overview

### Primary Document
- **`NEXA_Architecture_Updated.docx`** — 200-250 pages, 12 chapters
  - Complete system architecture, data models, API reference, calculation pipeline, business rules, visions, traceability, versioning, Azure target, maintenance guide, glossary

### Supporting Documentation (Markdown)
| File | Purpose | Scope |
|------|---------|-------|
| `API_REFERENCE.md` | All 25+ endpoints documented | Request/response JSON, validations, HTTP codes, dependencies |
| `BUSINESS_RULES.md` | Complete rule catalog | Staffing, channels, risk, pricing, margins, FTE volumetric, rampup |
| `FORMULAS.md` | Formula reference | All critical formulas with variables, implementation, examples |
| `TRACEABILITY_MATRIX.md` | Excel ↔ Backend ↔ API | Panel → DTO → Variable → Formula → Vision → API response |
| `DATA_MODEL.md` | All DTOs/models | Input, domain, result, vision models in structured tables |
| `AZURE_TARGET_ARCHITECTURE.md` | Cloud migration design | Azure components, flows, scalability, security |
| `MAINTENANCE_GUIDE.md` | Operations & evolution | How to add calculators, change formulas, manage versions, rollback |

---

## 🗂️ Critical Files Reference

### Architecture & Pipeline
```
backend_nexa/
├── engine.py                          # Main orchestrator (10-layer pipeline)
├── calculators/
│   ├── nomina.py                      # Layer 2: Payroll (NominaCalculator)
│   ├── no_payroll.py                  # Layer 3: Infrastructure (NoPayrollCalculator)
│   ├── cadena_b.py                    # Layer 4: Digital platform (CadenaBCalculator)
│   ├── cadena_c.py                    # Layer 5: AI/Integration (CadenaCCalculator)
│   ├── costos_totales.py              # Layer 6: Aggregation (CostosTotalesCalculator)
│   ├── costos_financieros.py          # Layer 7: Financial costs (CostosFinancierosCalculator)
│   ├── pyg.py                         # Layer 8: Monthly P&L (PyGCalculator)
│   ├── kpis.py                        # Layer 9: Deal KPIs (KPIsCalculator)
│   ├── cost_to_serve.py               # Vision: CTS per unit (CostToServeCalculator)
│   ├── vision_tarifas.py              # Vision: Per-channel tariffs (VisionTarifasCalculator)
│   ├── vision_pyg.py                  # Vision: Structured P&G (VisionPyGBuilder)
│   ├── vision_imprimible.py           # Vision: Composite view (VisionImprimibleBuilder)
│   └── riesgo.py                      # Risk assessment (RiesgoCalculator)
```

### Domain & Models
```
domain/
├── models/
│   ├── panel.py                       # Input structures (PanelDeControl, PerfilCadenaA)
│   ├── results.py                     # Calculator outputs (ResultadoNomina, ResultadoCadenaB, PyGMensual)
│   ├── visions.py                     # Vision structures (CTS, Tarifas, P&G, Imprimible)
│   └── value_objects.py               # Enums, constants
├── services/
│   └── special_roles_calculator.py    # CargoClassifier (role classification)
├── profitability/
│   └── calculators.py                 # Margin factor formula (pure domain)
├── payroll/
│   └── calculators.py                 # Salary indexation (pure domain)
└── financial/
    ├── models.py                      # Financial value objects
    └── calculators.py                 # ICA, GMF, financing logic
```

### API & Contracts
```
api/v1/                                # REST endpoints (25+)
├── simulation/
│   ├── calculate_router.py            # POST /calculate (main entry)
│   ├── results_router.py              # GET /results + /traceability
│   └── vision_router.py               # GET /results/vision-pyg
├── audit/
│   └── audit_router.py                # GET /audit/* (lineage, explain, baseline-diff)
├── certification/
│   └── certification_router.py        # GET /certificate/* (certified mode)
└── parametrization/
    ├── hr_router.py                   # POST /upload, GET /versions, etc.
    ├── gn_router.py
    └── op_router.py

contracts/api_v1/
├── request/                           # Input DTOs (EntryDataV1, Panel, Cadenas, Escenarios)
├── response/                          # Output DTOs (KPIs, Visions, Audit, Certified)
└── openapi/
    ├── api-v1.json                    # Frozen contract (stable, additive-only)
    └── api-v1.yaml
```

### Parametrization & Versioning
```
application/
├── versioning/
│   └── version_registry.py            # VersionRegistry, VersionMetadata (immutable snapshot)
├── lineage/
│   ├── models.py                      # LineageGraph, LineageNode, LineageRef
│   └── lineage_builder.py             # seed_lineage_from_request/result

infrastructure/
├── parametrization/                   # HR/GN/OP loaders, resolvers
└── certification/                     # Certified mode adapters

storage/parametrization/
├── v2-7/
│   ├── hr.json                        # HR-Salarios, HR-Ratios, clasificacion_cargos, tipos_carga
│   ├── gn.json                        # GN (General) configs
│   └── op.json                        # OP (Operations) rules, rampup curves
└── {module}/versions.json             # Version registry (active version ID + hash)
```

---

## 📊 Documentation Phases

### ✅ PHASE 1: Preparation & Validation
- Status: **IN PROGRESS**
- Files: `ARCHITECTURE_INDEX.md` (this file), `markdown_structure.md`
- Deliverables: Index, structure, file references

### 🔄 PHASE 2: Data Models Documentation
- Status: **PENDING**
- Input: API contracts, domain models, result models
- Output: `CAP 3 Modelo de Datos.md`, `API_REFERENCE.md`, `DATA_MODEL.md`

### 🔄 PHASE 3: Calculation & Business Rules
- Status: **PENDING**
- Input: Calculator implementations, formulas, parametrization
- Output: `CAP 5 Motor de Cálculo.md`, `CAP 6 Reglas de Negocio.md`, `FORMULAS.md`, `BUSINESS_RULES.md`

### 🔄 PHASE 4: Vision Structures
- Status: **PENDING**
- Input: Vision models, builders, activation rules
- Output: `CAP 7 Visions.md`

### 🔄 PHASE 5: Traceability Matrix
- Status: **PENDING**
- Input: Excel V2-7, backend calculations, API responses
- Output: `CAP 8 Matriz de Trazabilidad.md`, `TRACEABILITY_MATRIX.md`

### 🔄 PHASE 6: Architecture & Versioning
- Status: **PENDING**
- Input: Clean Architecture patterns, version registry, certified mode, lineage
- Output: `CAP 2 Arquitectura.md`, `CAP 9 Versionado.md`, `CAP 10 Azure.md`

### 🔄 PHASE 7: Diagrams & Validation
- Status: **PENDING**
- Output: 12+ Mermaid diagrams, PNG/SVG exports, cross-check documentation ↔ code

### 🔄 PHASE 8: Integration & Finalization
- Status: **PENDING**
- Output: `NEXA_Architecture_Updated.docx`, PDF, all markdown docs linked

---

## 🎯 Key Statistics (from code validation)

| Metric | Value |
|--------|-------|
| **Total Endpoints** | 25+ |
| **API Version** | api-v1 (frozen, stable) |
| **Pipeline Layers** | 10 (deterministic) |
| **Vision Structures** | 4 official (CTS, Tarifas, P&G, Imprimible) |
| **Domain Models** | 20+ (input, domain, result, vision) |
| **Calculators** | 13 (stateless) |
| **Parametrization Modules** | 3 (HR, GN, OP) |
| **Excel Source** | V2-7 (source of truth) |
| **Precision Rule** | Decimal + ROUND_HALF_UP (Excel-compatible) |
| **Architecture Pattern** | Clean Architecture (DDD) |
| **Versioning** | VersionRegistry with hash-based change detection |

---

## ✨ Quality Assurance Criteria

### Completeness
- [ ] 25+ endpoints documented (0 omitted)
- [ ] 10 pipeline layers explained (all formulas complete)
- [ ] 4 visions detailed (hierarchies, activation rules, JSON examples)
- [ ] Traceability matrix complete (Excel → Backend → Formula → Vision → API)

### Consistency
- [ ] Endpoint documented = exists in code ✅
- [ ] Formula documented = implemented in code ✅
- [ ] Example JSON = from real response ✅
- [ ] Variable name = matches current code (post-refactor) ✅

### Auditability
- [ ] Each calculation traceable to Excel V2-7 cell
- [ ] Each parameter documented: source (HR, OP, user, hardcoded)
- [ ] Versioning explicit: engine, API, formula-set, parametrization

### Usability
- [ ] Readable by: architect (overview), developer (details), auditor (traceability)
- [ ] 1 diagram per complex concept
- [ ] 1 table per data structure
- [ ] 1 JSON example per endpoint

---

## 📝 Document Naming Convention

All chapters follow format: `CAP {number} {Title}.md`

- CAP 1: Visión General del Sistema
- CAP 2: Arquitectura de Software
- CAP 3: Modelo de Datos
- CAP 4: API Reference
- CAP 5: Motor de Cálculo (10-Layer Pipeline)
- CAP 6: Reglas de Negocio Completas
- CAP 7: Visions (CTS, Tarifas, P&G, Imprimible)
- CAP 8: Matriz de Trazabilidad
- CAP 9: Versionado y Modos Certificados
- CAP 10: Arquitectura Azure Objetivo
- CAP 11: Guía de Mantenimiento y Evolución
- CAP 12: Glosario Técnico-Funcional

---

## 🔗 Related Documentation

### Already Completed
- `docs/refactor/NAMING_AUDIT.md` — 6-field refactor audit
- `docs/refactor/BUSINESS_GLOSSARY.md` — Business terminology glossary

### Azure Target (Pending)
- Architecture diagram (components, flows, scalability)
- Migration strategy (stateless design, versioning)
- Cost estimation (scale-out vs. legacy)

### Certified Mode (Pending)
- Baseline validation workflow
- Parametrization hash snapshot
- Drift detection & rollback

---

## 📞 Ownership & Review

| Document | Owner | Review Status |
|----------|-------|---------------|
| Architecture Overview | CloudArchitect | Pending design review |
| API Reference | APITeam | Pending contract validation |
| Formulas & Calculations | FinanceAudit | Pending Excel V2-7 sign-off |
| Vision Structures | ProductTeam | Pending business acceptance |
| Traceability Matrix | Auditor | Pending certification |
| Azure Architecture | CloudOps | Pending infrastructure design |
| Maintenance Guide | DevTeam | Pending operational acceptance |
