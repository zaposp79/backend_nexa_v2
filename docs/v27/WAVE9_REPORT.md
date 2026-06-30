> **⚠️ POST-W17 NOTE**: Mutation testing in W17 revealed extracted
> `domain/` functions are NOT exercised in the real runtime — dual
> execution paths persist. Full unification deferred to SEMANTIC F3.

# WAVE 9 — Clean Architecture (FASE 4)

**Fecha**: 2026-05-28
**Branch**: `refactor/engine-v2`
**Foco**: Extraer el core financiero a Clean Architecture vía strangler pattern.

---

## 1. Resumen ejecutivo

WAVE 9 introduce la estructura `domain/{pricing,payroll,staffing,financial,profitability,risk,shared}/`,
`application/{use_cases,orchestrators,services,ports}/`, e `infrastructure/{parametrization,logging,persistence,repositories}/`
en el monorepo, sin tocar las APIs públicas del motor.

**Estrategia**: strangler pattern. Cada calculator viejo permanece en
`calculators/` como shim que delega a su contraparte pura en `domain/`.
Los 104 tests críticos (39 parity + 16 baselines + 49 contracts) siguen
verdes con 0 modificaciones.

**Resultado**:
* **Critical**: 104 / 104 (39 parity + 16 baselines + 49 contracts).
* **Default suite**: 808 passed (era 795 + 13 nuevos tests WAVE 9).
* **Deselected** (legacy): 411 sin cambios.
* **Skipped**: 23 sin cambios.
* **Failed**: 0.
* **Domain purity check** (ast scan): 0 violaciones — ningún módulo
  WAVE 9 en `domain/{pricing,payroll,staffing,financial,profitability,
  risk,shared}/` importa `logging/requests/httpx/fastapi/openpyxl/xlrd/pandas`.

---

## 2. Estructura creada

```
backend_nexa/
├── domain/
│   ├── pricing/          calculators.py + value_objects.py + entities.py
│   ├── payroll/          calculators.py + value_objects.py + entities.py
│   ├── staffing/         calculators.py + value_objects.py + entities.py
│   ├── financial/        calculators.py + value_objects.py + entities.py
│   ├── profitability/    calculators.py + value_objects.py + entities.py
│   ├── risk/             (reserved, WAVE9-DEFERRED)
│   └── shared/           constants.py + exceptions.py
├── application/
│   ├── ports/            IParametrizationProvider (re-export) + ILogger + ITraceEmitter
│   ├── use_cases/        CalculateSimulationUseCase, BuildPayrollUseCase,
│   │                     BuildStaffingUseCase, BuildPricingUseCase,
│   │                     BuildScenariosUseCase, BuildVisionsUseCase
│   ├── orchestrators/    PricingPipeline
│   └── services/         CanonicalizationService
├── infrastructure/
│   ├── logging/          StructuredLogger (ILogger backed by stdlib logging)
│   ├── parametrization/  json_provider.py (re-export of ParametrizationProvider)
│   ├── repositories/     (reserved, WAVE9-DEFERRED)
│   └── persistence/      (reserved)
└── interfaces/
    ├── http/             (api/v1/ remains in place, WAVE9-DEFERRED)
    ├── excel/            (reserved)
    ├── cli/              (reserved)
    └── azure/            (reserved for WAVE 11)
```

Cada directorio incluye `__init__.py` y `README.md` con sus reglas.

---

## 3. Calculadores migrados a `domain/` (strangler shims)

| Legacy                        | Domain destination                                                 | Shim status                              |
|-------------------------------|--------------------------------------------------------------------|------------------------------------------|
| `calculators/utils.py::calcular_factor_margenes` | `domain.profitability.calculators.ProfitabilityCalculator.calcular_factor_margenes` | Delegated, signature unchanged |
| `calculators/utils.py::calcular_factor_aumento`  | `domain.payroll.calculators.PayrollCalculator.calcular_factor_aumento`              | Delegated, signature unchanged |
| `calculators/vision_tarifas.py::_componentes_label` | `domain.pricing.calculators.PricingCalculator.derivar_componentes_label`         | Delegated                       |
| `calculators/pyg.py::PyGCalculator.calcular_mes` (formula) | `domain.profitability.calculators.ProfitabilityCalculator.calcular_factor_billing` | Pure formula re-exported (used via utils shim) |

Calculadores cuya extracción se **DEFERRED** y razón:

* **`calculators/nomina.py::NominaCalculator`** — depende de docenas de
  atributos de `ParametrosNomina` / `PerfilCadenaA` y produce
  `ResultadoNomina`. Extracción completa rompe paridad por matching
  exacto con Excel. Solo se extrajeron las dos sub-fórmulas puras:
  `factor_aumento` y `factor_indexacion`.

* **`calculators/cost_to_serve.py`** y **`calculators/vision_tarifas.py`** —
  ambos componen Nómina + No-Payroll + Cadena B + Cadena C con lógica
  iterativa. Solo se extrajeron los helpers puros
  (`_componentes_label`, `_factor_billing` ya delega vía
  `calcular_factor_margenes`).

* **`calculators/costos_financieros.py::CostosFinancierosCalculator`** —
  depende del orden ICA → Pólizas → GMF → Financiación con gross-up. Se
  extrajeron las 4 atómicas puras a `FinancialCalculator` para que
  futuros use cases compongan sin pasar por la clase legacy.

* **`calculators/cadena_b.py`, `cadena_c.py`, `kpis.py`, `riesgo.py`,
  `costos_totales.py`, `no_payroll.py`, `vision_*.py`** — fuera del scope
  de WAVE 9. Marcados `WAVE9-DEFERRED` en el README de cada subdir
  correspondiente.

---

## 4. Use cases creados en `application/use_cases/`

| Use case                         | Responsabilidad                                                  |
|----------------------------------|------------------------------------------------------------------|
| `CalculateSimulationUseCase`     | End-to-end: delega a `NexaPricingEngine.calcular()` con logger + tracer |
| `BuildPayrollUseCase`            | `factor_indexacion` + emisión `[PAYROLL_BUILD]`                  |
| `BuildStaffingUseCase`           | `aplicar_rampup` (lookup HR + cálculo puro)                      |
| `BuildPricingUseCase`            | `factor_billing` + `ingreso_bruto` con `[PRICING_BUILD]`         |
| `BuildScenariosUseCase`          | Passthrough con `[SCENARIO_BUILD]` (real impl deferred)          |
| `BuildVisionsUseCase`            | Emisor de `[VISION_BUILD]` events                                |

Todos aceptan `logger=None` y `tracer=None` con fallback a
`NullLogger` / `NullTraceEmitter` para uso en tests.

Orchestrator: `application/orchestrators/pricing_pipeline.py::PricingPipeline`
expone las 5 use cases en un solo contenedor para tests y futura
composición.

Service: `application/services/canonicalization_service.py::CanonicalizationService`
es una fachada estática sobre `shared/canonicalization.py`.

---

## 5. Ports definidos

| Port                       | Archivo                                                  | Implementación default       |
|----------------------------|----------------------------------------------------------|------------------------------|
| `IParametrizationProvider` | `application/ports/parametrization_provider.py`          | Re-export de legacy Protocol |
| `ILogger`                  | `application/ports/logger.py`                            | `NullLogger`                 |
| `ITraceEmitter`            | `application/ports/trace_emitter.py`                     | `NullTraceEmitter` (WAVE 10) |

`IParametrizationProvider` es un **re-export** del Protocol existente en
`repositories/i_parametrization_provider.py`. El test
`test_iparametrization_provider_reexport_is_same_object` valida que
ambos paths devuelvan exactamente el mismo objeto-clase, garantizando
que isinstance/Protocol checks se comportan idénticos.

---

## 6. Logger en infrastructure

`infrastructure/logging/structured_logger.py::StructuredLogger`:
* Implementa `ILogger`
* Usa stdlib `logging`
* Formato compatible con WAVE 5: `[TAG] op=... key=value ...`
* Inyectable en use cases vía constructor

Los logs `[PAYROLL_BUILD] [STAFFING_BUILD] [SCENARIO_BUILD] [PRICING_BUILD]
[VISION_BUILD] [SIMULATION_BUILD]` ahora viven en `application/use_cases/`
cuando se llama desde el nuevo path. Los logs equivalentes en
`calculators/*` se mantuvieron (legacy path sigue produciéndolos).
Esto cumple "domain SIN IO" — los nuevos calculators puros no producen
ningún log; solo los use cases lo hacen.

---

## 7. Tests críticos — counts

```
tests/parity     39 passed  (intacto vs baseline V2-7)
tests/baselines  16 passed  (intacto)
tests/contracts  49 passed  (intacto)
                ───
TOTAL critical  104 passed
```

## 8. Suite default — counts

```
Before WAVE 9: 795 passed / 0 failed / 0 errors / 23 skipped / 411 deselected
After WAVE 9:  808 passed / 0 failed / 0 errors / 23 skipped / 411 deselected
                ↑ +13 nuevos tests en tests/unit/test_wave9_domain_purity.py
```

Sin regresiones. Suite default crece sólo por los tests añadidos para
validar la propia WAVE 9 (numeric parity, purity scan, ports/null impl).

---

## 9. Domain purity check (ast scan)

Script: `tests/unit/test_wave9_domain_purity.py::test_domain_modules_do_not_import_io`.

Lista de imports prohibidos en `domain/{pricing,payroll,staffing,
financial,profitability,risk,shared}/`:

* `logging`
* `requests`
* `httpx`
* `fastapi`
* `openpyxl`
* `xlrd`
* `pandas`

**Resultado**: 0 violaciones.

> Nota: `domain/models/`, `domain/services/`, `domain/snapshot.py`,
> `domain/user_inputs.py`, `domain/visions.py`, `domain/constants.py`,
> `domain/normalized_input.py`, `domain/frozen_parametrization.py`
> pre-existen a WAVE 9 y NO se enforcean por este test (son Pydantic +
> helpers). Su saneo a "puro" se programará en wave futura — están
> marcados WAVE9-DEFERRED en los README correspondientes.

---

## 10. Bloqueos para WAVE 10 (lineage)

Ninguno. Las piezas necesarias ya están listas:

1. **`ITraceEmitter` port** — solo emite no-op por ahora; WAVE 10
   reemplaza con un buffer que serializa stages.
2. **Use cases ya emiten `tracer.emit(...)`** en cada operación clave —
   no requiere cambiar callsites, solo inyectar un emisor real.
3. **`PricingPipeline`** centraliza la inyección de logger+tracer, así
   WAVE 10 puede crear un único emisor con cliente_id y reutilizarlo
   transversalmente.

---

## 11. Lógica DEFERRED — checklist

| ID              | Lugar                                                          | Razón                                                                  | Plan                                  |
|-----------------|----------------------------------------------------------------|------------------------------------------------------------------------|---------------------------------------|
| W9-DEF-1        | `calculators/nomina.py`                                        | Tightly coupled to `ParametrosNomina`/`PerfilCadenaA`                  | Migrar en WAVE 12 (perf cleanup)      |
| W9-DEF-2        | `calculators/costos_financieros.py`                            | ICA gross-up + polizas dependency + user-polizas branching             | Reescribir como use case en WAVE 13   |
| W9-DEF-3        | `calculators/vision_tarifas.py` (cuerpo)                       | 488 líneas con loops + escenarios + canales                            | Mover canal-by-canal a use case        |
| W9-DEF-4        | `calculators/cost_to_serve.py`                                 | Compone Nómina + No-Payroll + Cadena B + Cadena C                      | Como W9-DEF-3                         |
| W9-DEF-5        | `repositories/{payroll,infrastructure,profitability,financial}_parametrization_repository.py` | Coupling a provider composition                                        | Mover a `infrastructure/repositories/` en WAVE 14 |
| W9-DEF-6        | `api/v1/` HTTP routers                                         | FastAPI app wiring assume current paths                                | Mover a `interfaces/http/` en WAVE 11 |
| W9-DEF-7        | `domain/models/`, `domain/services/`                           | Pre-WAVE 9, mezclan Pydantic + helpers                                 | Refactor en WAVE 14 (versionado)      |

---

## 12. Archivos creados (resumen)

### Domain
* `domain/pricing/{__init__,value_objects,entities,calculators,README}.py`
* `domain/payroll/{__init__,value_objects,entities,calculators,README}.py`
* `domain/staffing/{__init__,value_objects,entities,calculators,README}.py`
* `domain/financial/{__init__,value_objects,entities,calculators,README}.py`
* `domain/profitability/{__init__,value_objects,entities,calculators,README}.py`
* `domain/risk/{__init__,README}.py`
* `domain/shared/{__init__,constants,exceptions,README}.py`

### Application
* `application/{__init__,README}.py`
* `application/ports/{__init__,parametrization_provider,logger,trace_emitter,README}.py`
* `application/use_cases/{__init__,calculate_simulation,build_payroll,build_staffing,build_pricing,build_scenarios,build_visions}.py`
* `application/orchestrators/{__init__,pricing_pipeline}.py`
* `application/services/{__init__,canonicalization_service}.py`

### Infrastructure
* `infrastructure/logging/{__init__,structured_logger,README}.py`
* `infrastructure/parametrization/{__init__,json_provider,README}.py`
* `infrastructure/repositories/{__init__,README}.py`
* `infrastructure/persistence/{__init__,README}.py`

### Interfaces
* `interfaces/{__init__,README}.py`
* `interfaces/http/{__init__,README}.py`
* `interfaces/excel/__init__.py`
* `interfaces/cli/__init__.py`
* `interfaces/azure/{__init__,README}.py`

### Modificados (shims, signature-preserving)
* `calculators/utils.py` — `calcular_factor_margenes`, `calcular_factor_aumento` delegan a domain
* `calculators/vision_tarifas.py` — `_componentes_label` delega a domain.pricing

### Tests añadidos
* `tests/unit/test_wave9_domain_purity.py` — 13 tests

### Documentación
* `docs/v27/WAVE9_REPORT.md` (este archivo)
* `docs/v27/W10_INDUSTRIALIZATION_PLAN.md`
* `docs/v27/W10_CLOUD_READY_ARCHITECTURE.md`

---

## 13. Criterio de éxito — Cumplimiento

| Criterio                                                       | Resultado                |
|----------------------------------------------------------------|--------------------------|
| Paridad inmutable: 104 tests críticos verdes con 0 cambios funcionales | ✓ 104 / 104       |
| Suite default sin regresión                                     | ✓ 808 (era 795 + 13 nuevos) |
| `domain/` puro (no IO/logging en módulos WAVE 9)                | ✓ 0 violaciones (ast scan) |
| `application/use_cases/` con orquestación                       | ✓ 6 use cases             |
| `infrastructure/logging/StructuredLogger` inyectable            | ✓                         |
| No import circular                                              | ✓ (suite full pasa)       |
| APIs públicas inalteradas                                       | ✓ engine.py y api/v1/ intactos |
| Strangler reversible                                            | ✓ archivos viejos vivos como shims |

**Veredicto**: **READY**. WAVE 9 entrega Clean Architecture aplicada sin
romper paridad ni APIs. WAVE 10 (lineage) puede comenzar sin bloqueos.

— Fin de WAVE 9.
