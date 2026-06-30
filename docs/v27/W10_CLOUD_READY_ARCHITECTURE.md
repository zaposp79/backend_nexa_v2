# Clean Architecture aplicada al motor NEXA — referencia post-WAVE 9

**Fecha**: 2026-05-28

Este documento describe cómo está organizada la capa lógica del motor
NEXA después de WAVE 9, y cómo cada capa se prepara para los pasos
cloud-native de WAVE 10–15.

---

## 1. Diagrama (post-WAVE 9)

```
┌─────────────────────────── interfaces ───────────────────────────┐
│  http (api/v1/ shim)     excel       cli       azure (W11)        │
└─────────────────────────────┬─────────────────────────────────────┘
                              │ depende de
┌─────────────────────────────▼─────────────────────────────────────┐
│                        application                                │
│                                                                   │
│  use_cases/        orchestrators/   services/   ports/            │
│  ─────────         ───────────────  ──────────  ──────────────    │
│  CalculateSim.     PricingPipeline  Canon.Svc   IParamProvider    │
│  BuildPayroll                                   ILogger           │
│  BuildStaffing                                  ITraceEmitter     │
│  BuildPricing                                                     │
│  BuildScenarios                                                   │
│  BuildVisions                                                     │
└─────────────────────────────┬─────────────────────────────────────┘
                              │ depende de
┌─────────────────────────────▼─────────────────────────────────────┐
│                           domain                                  │
│                                                                   │
│  pricing/            payroll/        staffing/      financial/    │
│  profitability/      risk (rsv)      shared/                      │
│                                                                   │
│  *.value_objects      *.entities      *.calculators               │
│      (puros: NO IO, NO logging, NO HTTP, NO openpyxl)             │
└───────────────────────────────────────────────────────────────────┘

    ▲   los componentes superiores SOLO ven los puertos (interfaces)
    │
┌───┴───────────────────── infrastructure ──────────────────────────┐
│  parametrization/   logging/           persistence/  storage/     │
│  json_provider.py   StructuredLogger   (W13)         json_store   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Reglas de dependencia

| Capa            | Puede importar de…                                                              |
|-----------------|---------------------------------------------------------------------------------|
| `domain/`       | otros módulos `domain/` + stdlib estricto (no `logging`, no IO)                |
| `application/`  | `domain/` + `application/ports/` + stdlib                                       |
| `infrastructure/` | `application/ports/` (para implementar) + stdlib + librerías externas         |
| `interfaces/`   | `application/use_cases/` + `application/ports/` + framework (FastAPI/Azure)     |

Violaciones detectadas por `tests/unit/test_wave9_domain_purity.py` (ast scan).

---

## 3. Ports — DIP en práctica

### IParametrizationProvider
Re-export del Protocol de `repositories/i_parametrization_provider.py`.
Razón: 50+ callsites legacy ya lo importaban desde ahí; mover el class
object rompería `isinstance()` checks. El re-export garantiza que ambas
rutas devuelvan el mismo class object.

### ILogger
Métodos: `info/debug/warning/error(msg, **kwargs)`. Implementación
default `NullLogger` (silencio). Producción: `StructuredLogger`
(stdlib).

### ITraceEmitter
Método: `emit(stage, inputs, outputs, source="")`. Default
`NullTraceEmitter`. WAVE 10 enchufará un `JsonLineageEmitter` que
buffrea stages para serializarlas al `PricingResult.lineage`.

---

## 4. Use cases — anatomy

```python
class BuildPricingUseCase:
    def __init__(self, logger=None, tracer=None):
        self._logger = logger or NullLogger()
        self._tracer = tracer or NullTraceEmitter()

    def calcular_factor_billing(self, margen, op_cont, com_cont, markup, descuento, cadena="A"):
        result = ProfitabilityCalculator.calcular_factor_billing(
            margen, op_cont, com_cont, markup, descuento
        )   # ← pure domain math
        self._logger.info("[PRICING_BUILD] op=factor_billing", ...)
        self._tracer.emit(stage="pricing.factor_billing.A", inputs={...}, outputs={...})
        return result
```

Tres responsabilidades por método:
1. Llamar a un calculator puro (`domain/`).
2. Loggear vía `self._logger`.
3. Emitir lineage vía `self._tracer`.

---

## 5. Por qué el strangler y no un big-bang

* La paridad V2-7 fue certificada en WAVE 5 con 39 tests parity + 16
  baselines + 49 contracts (104 tests). Cualquier reescritura completa
  riesgea quebrar al menos uno.
* Big-bang requeriría regenerar fixtures de 5 escenarios Bancamia,
  3 escenarios Excel oracle, etc.
* Strangler permite:
  * Avanzar con cada calculator de forma incremental.
  * Tener siempre un sistema en estado verde.
  * Revertir un solo archivo si paridad rompe.

---

## 6. Cómo añadir un nuevo dominio

1. Crear `domain/<dominio>/__init__.py` + `calculators.py` + `value_objects.py` + `entities.py` + `README.md`.
2. Reglas: NO importar `logging`, NO IO, métodos `@staticmethod` o functions puras.
3. Crear `application/use_cases/build_<dominio>.py` que inyecte ports y delegue a los puros.
4. Si necesita parametrización: depender de `IParametrizationProvider` (NO instanciar provider).
5. Si emite eventos: usar `self._tracer.emit(stage=..., ...)`.
6. Añadir tests en `tests/unit/test_<dominio>.py` con `NullLogger` + `NullTraceEmitter`.

---

## 7. Cloud-readiness checklist (estado post-WAVE 9)

| Item                                                    | Estado          |
|---------------------------------------------------------|-----------------|
| Use case puro inyectable                                | ✓ (W9)          |
| Logger inyectable (no `logging.getLogger()` global)     | ✓ ports + impl  |
| Provider inyectable (no singleton global)               | ✓ ports         |
| Trace emitter inyectable                                | ✓ ports         |
| Parametrización separable de filesystem                 | parcial (W11)   |
| Function entry point HTTP-triggered                     | reservado (W11) |
| Persistence repository de snapshots                     | reservado (W13) |
| Versionado SemVer del motor                             | reservado (W14) |

---

— Fin del documento.
