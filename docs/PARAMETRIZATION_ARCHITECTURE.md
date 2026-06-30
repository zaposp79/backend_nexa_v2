# Parametrization-Centric Architecture: Phase 1-2 Implementation

## Overview

**Objective:** Make parametrization (HR, GN, OP) the single source of truth for all pricing calculations, replacing hardcoded master_data.json.

**Status:** Phase 1-2 Complete
- ✅ ParametrizationResolver (central resolver)
- ✅ ParametrizationLoader (low-level file I/O)
- ✅ FinancialParametrizationRepository (ICA, GMF, insurance, components)
- ✅ InfrastructureParametrizationRepository (costs, medical exams)
- ✅ PayrollParametrizationRepository (salaries, contributions, benefits)
- ✅ ProfitabilityParametrizationRepository (margins, campaigns)
- ✅ Unit tests
- ⏳ Phase 3-6: LocationPolicy, ContextBuilder refactor, Calculator migration, Validation+Logging

## Architecture

### Current (Implemented) Data Flow

```
storage/parametrization/{hr,gn,op}/
    versions.json (tracks active version)
    {version_id}.json (full parametrization data)
        ↓
ParametrizationResolver
    (loads active version by module)
        ↓
Domain Repositories
    - FinancialParametrizationRepository
    - InfrastructureParametrizationRepository
    - PayrollParametrizationRepository
    - ProfitabilityParametrizationRepository
        ↓
[READY FOR] Application Layer
    (to be used by SimulationContextBuilder, Calculators in Phase 3-6)
```

### Module Structures

#### HR Parametrization
```json
{
  "version_id": "uuid",
  "niveles": {...},          // Catalogs (tipos, roles)
  "salarios": [{...}],       // HR-SalarioBasico
  "nomina": [{              // HR-Nomina: Base salaries
    "tipo": "Empleado",
    "rol": "Director de cuentas",
    "salario": 22761150.0
  }],
  "recargos": [{...}],      // HR-Recargos: Wage surcharges
  "seg_social": [{          // HR-SegSocial: SS contributions
    "ssparafiscales": "Salud",
    "proporcion": 0.085
  }],
  "prestaciones": [{        // HR-Prestaciones: Benefits
    "prestaciones": "Prima",
    "valor": 0.0833
  }],
  "ratios": [{...}],        // HR-Ratios: Staff ratios
  "rentabilidad": [{        // HR-Rentabilidad: Margins
    "categoriaservicio": "Cobranzas",
    "minimo": 0.10,
    "margenobjetivo": 0.15
  }],
  "campana": [{             // HR-Campana: Campaign values
    "categoriaservicio": "Cobranzas",
    "mes": 1,
    "valor": 0.95
  }],
  "costo_fijo": [{          // HR-CostoFijo: Infrastructure
    "localidad": "Barranquilla",
    "servicio": "Energía",
    "valor": 153.301
  }],
  "med_seg": [{             // HR-Med-Seg: Medical exams
    "localidad": "Bogota",
    "centrocosto": "Costo externo examenes medicos nuevos",
    "valor": 60.8
  }]
}
```

#### GN Parametrization
```json
{
  "version_id": "uuid",
  "lv": {                   // Catalogs by column
    "name": "GN-LV",
    "key": "lv",
    "catalogs": {
      "ciudad": [{"name": "Bogotá"}, ...],
      "canal": [{"name": "WhatsApp"}, ...]
    }
  },
  "sheets": [...]           // Other raw data sheets
}
```

#### OP Parametrization
```json
{
  "version_id": "uuid",
  "lv": {                   // OP-LV Catalogs
    "catalogs": {"ica": [{"name": "Tasa"}, ...]}
  },
  "sheets": [
    {
      "name": "OP-ICA",
      "key": "ica",
      "rows": [
        {"ciudad": "Armenia", "ica": "Tasa", "valor": 0.006}
      ]
    },
    {
      "name": "OP-Componente",
      "key": "componente",
      "rows": [
        {"componente": "IPC", "ano": 2025, "valor": 0.0527}
      ]
    },
    // ... more sheets
  ]
}
```

## Core Classes

### ParametrizationResolver
**File:** `infrastructure/parametrization_resolver.py`

Central resolver for loading active parametrization versions.

```python
resolver = ParametrizationResolver()
hr_data = resolver.get_active_hr()      # Get active HR
op_data = resolver.get_active_op()      # Get active OP
gn_data = resolver.get_active_gn()      # Get active GN
any_data = resolver.get_module("hr")    # Generic access

# Caching
resolver.invalidate_cache("hr")         # Invalidate one module
resolver.invalidate_cache()             # Invalidate all
```

**Behavior:**
- Loads from `storage/parametrization/{module}/versions.json`
- Finds version marked `is_active: true`
- Loads full data from `{version_id}.json`
- Validates structure (must be dict with version_id)
- Caches in memory (singleton pattern available: `get_resolver()`)
- Strict errors (no fallbacks)

### ParametrizationLoader
**File:** `infrastructure/parametrization_loader.py`

Low-level file operations wrapper.

```python
ParametrizationLoader.load_active_version(module_dir)  # Get summary
ParametrizationLoader.load_version_data(module_dir, version_id)  # Get data
ParametrizationLoader.load_all_versions(module_dir)  # Get all versions
```

### Domain Repositories

#### Financial (OP + GN)
**File:** `repositories/financial_parametrization_repository.py`

```python
repo = FinancialParametrizationRepository(resolver)
ica = repo.get_ica("Armenia")           # ICA from OP-ICA
gmf = repo.get_gmf()                    # GMF rate
rate = repo.get_tasa_financiacion()     # Financing rate
policies = repo.get_insurance_policies() # All policies
value = repo.get_economic_component("IPC", 2025) # Index
```

#### Infrastructure (HR)
**File:** `repositories/infrastructure_parametrization_repository.py`

```python
repo = InfrastructureParametrizationRepository(resolver)
costs = repo.get_infrastructure_costs("Barranquilla")  # Dict: arriendo, energia, etc.
exam = repo.get_medical_exam_cost("Bogota")  # Medical exam cost
```

#### Payroll (HR)
**File:** `repositories/payroll_parametrization_repository.py`

```python
repo = PayrollParametrizationRepository(resolver)
salary = repo.get_salary_for_role("Director de cuentas")
ss = repo.get_contributions("Salud")        # SS contribution
benefit = repo.get_benefits("Prima")        # Benefit rate
```

#### Profitability (HR)
**File:** `repositories/profitability_parametrization_repository.py`

```python
repo = ProfitabilityParametrizationRepository(resolver)
min_m = repo.get_min_margin("Cobranzas")
target_m = repo.get_target_margin("Cobranzas")
campaign = repo.get_campaign_value("Cobranzas", 1)  # Month 1
```

## Error Handling

**Exception Hierarchy:**
```
DomainError (base)
├── ParametrizationError (data structure, corruption)
├── ParametrizationNotFoundError (version missing)
├── LocalityNotFoundError (locality not in parametrization)
├── RoleNotFoundError (role not found)
├── ContributionNotFoundError (contribution type not found)
├── BenefitNotFoundError (benefit not found)
├── BusinessLineNotFoundError (business line not found)
└── InvalidMonthError (month out of range 1-13)
```

**Usage:**
```python
from shared.exceptions import (
    ParametrizationError,
    ParametrizationNotFoundError,
    LocalityNotFoundError
)
```

## Data Consistency Notes

### Known Issues / Data Status

| Module | Status | Issue |
|--------|--------|-------|
| HR | ✅ Active & Complete | 360 CostoFijo entries, 55 Nomina entries |
| OP | ✅ Active & Complete | ICA rates, Components (IPC, etc.), Polizas |
| GN | ⚠️ Active but Empty | Loaded but data is NULL - needs migration from master_data |

**Impact:**
- Financial repository has working ICA access via OP
- GN fallbacks work (uses defaults)
- All other repositories fully functional

### Migration Needed

GN data should be migrated from master_data by:
1. Extracting all ICA rates by city from `master_data/tasas.json`
2. Creating Excel file GN-*.xlsx with ICA sheet
3. Uploading via `/api/v1/parametrization/gn/upload`
4. Validating ICA values match

## Next Steps (Phase 3-6)

### Phase 3: LocationPolicy
- Centralize "only Bogotá uses locality" rule
- Implement `LocationPolicy.requires_locality(ciudad)`
- Implement `LocationPolicy.validate_locality(ciudad, localidad)`
- Implement `LocationPolicy.resolve_sede(ciudad, localidad)`

### Phase 4: SimulationContextBuilder Refactor
- Replace `self._md.get_costo_no_payroll()` with infrastructure repo
- Replace `self._md.get_ica()` with financial repo
- Replace `self._md.get_salario_rol()` with payroll repo
- Replace `self._md.get_margen_minimo()` with profitability repo
- Inject 4 new repositories

### Phase 5: Calculator Refactoring
Migrate 10+ calculators from master_data → parametrization:
- NominaCalculator
- NoPayrollCalculator
- CostosFinancierosCalculator
- KPIsCalculator
- CadenaBCalculator / CadenaCCalculator
- VisionTarifasCalculator
- Supporting calculators

### Phase 6: Validation & Logging
- Implement `ParametrizationValidator`: validate on load
- Implement `ParametrizationLogger`: structured audit logs
- Generate comparison report: master_data vs parametrization

## Testing

**Test file:** `tests/test_parametrization_phase_1_2.py`

Run tests:
```bash
pytest tests/test_parametrization_phase_1_2.py -v
```

Tests cover:
- Resolver loads all modules correctly
- Domain repositories extract correct values
- Error handling for missing data
- Cache invalidation
- Type validation

## Decisions Made

✅ **Fallback Strategy:** Eliminate master_data completely (no transitional fallback)
✅ **Data Migration:** Parallel - migrate Excel data + refactor calculators simultaneously
✅ **Locality Handling:** Strict - reject if city!=Bogotá but localidad provided
✅ **Execution:** Phase 1-2 complete, Phase 3-6 deferred

## Files Created

- `infrastructure/parametrization_resolver.py` (290 lines)
- `infrastructure/parametrization_loader.py` (140 lines)
- `repositories/financial_parametrization_repository.py` (230 lines)
- `repositories/infrastructure_parametrization_repository.py` (165 lines)
- `repositories/payroll_parametrization_repository.py` (210 lines)
- `repositories/profitability_parametrization_repository.py` (240 lines)
- `tests/test_parametrization_phase_1_2.py` (240 lines)
- `shared/exceptions.py` (added 3 new exceptions)

**Total:** 1,515+ lines of new code

## Backward Compatibility

✅ **Existing APIs unchanged:** All parametrization endpoints continue to work
✅ **Existing storage unchanged:** versions.json and data JSON files untouched
✅ **No breaking changes:** Calculators still use master_data in Phase 2
✅ **Gradual migration path:** Repositories ready for Phase 3 adoption

## Future-Proofing

- ParametrizationResolver abstracts storage (easy to migrate JSON → PostgreSQL/DynamoDB)
- Domain repositories hide data structure (can change sheet names without affecting calculators)
- Consistent error handling enables client-side error recovery
- Logging foundation ready for Phase 6 audit trail
