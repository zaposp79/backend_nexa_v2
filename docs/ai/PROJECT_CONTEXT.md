# Project Context

## Tipo de proyecto
Motor de pricing + API REST para parametrización y simulación de deals (contratos de outsourcing BPO).

## Stack
- **Python 3.14** (venv en `backend_nexa/venv/`)
- **FastAPI** + **uvicorn** (API REST)
- **Pydantic v2** (DTOs y modelos)
- **openpyxl** (parsing Excel HR/GN/OP)
- **azure-cosmos>=4.5,<5** (importación diferida, solo con `DB_PROVIDER=cosmos` en Azure)
- **pytest** (suite de tests)

**Cloud:** Azure (Cosmos DB, Key Vault, App Service). Default local: JSON en filesystem.

## Arquitectura

### Alias de módulo
`backend_nexa/__init__.py` registra `nexa_engine` como alias de `backend_nexa` en `sys.modules`.
Todo el código interno usa `from nexa_engine.modules.xxx import ...`.
El módulo canónico para uvicorn es siempre `backend_nexa.app:create_app`.

### Capas principales
1. **Motor de cálculo** (`modules/calculator_motor/`) — pipeline de 10 capas, entrada `PricingRequest`, salida `PricingResult`. Sin I/O.
2. **HTTP de cálculo** (`modules/calculator/api/`) — endpoints de simulación; (`modules/calculator/persistence/`) — repositorios de resultados.
3. **Módulos verticales** (`modules/`) — cada capacidad (parametrizacion, cadena_a/b/c, panel, vision_*) tiene su propio `api/`, `services/`, `repositories/`, `dto/`.
4. **Capa de persistencia** (`db/`) — `DocumentStore` con provider `json` (default) o `cosmos`. Root de inyección: `db/container.py`.
5. **API REST** (`modules/api_v1/router.py`) — composición de todos los sub-routers modulares. Prefijo `/api/v1`.
6. **Shared** (`modules/shared/`) — excepciones, `ApiResponse`, contratos; `shared/ports/` — interfaces Protocol (`IParametrizationProvider`, `ILogger`, `ITraceEmitter`).

### Composition Root
- Motor: `modules/calculator_motor/engine.py` → `_construir_calculadores()`
- Persistencia: `db/container.py` → `build_container()` (llamado desde el `lifespan` de FastAPI)

## Convenciones
- Todos los endpoints devuelven `ApiResponse` de `modules/shared/responses.py`.
- Imports usan `nexa_engine.*` (alias), nunca `backend_nexa.*`.
- Errores de dominio: `DomainError` (400), `NotFoundError` (404), `ValidationError` (422).
- Tests se ejecutan desde el directorio padre de `backend_nexa/`: `PYTHONPATH=<parent> pytest tests/`.

## Módulos principales

| Módulo | Descripción |
|---|---|
| `modules/calculator_motor/` | Engine (`NexaPricingEngine`), pipeline 10 capas, formulas, adapters, dto |
| `modules/calculator/api/` | Endpoints HTTP de cálculo (handlers, DTOs, router) |
| `modules/calculator/persistence/` | `ResultsRepository`, `TraceabilityRepository` |
| `modules/parametrizacion/hr/gn/op/` | Upload Excel, versionado, activación |
| `modules/panel/` | Input Panel de Control General |
| `modules/cadena_a/b/c/` | Inputs cadenas (A=Backoffice, B=Digital, C=IA) |
| `modules/vision_imprimible/` | Vista 9 secciones del resultado |
| `modules/vision_cost_to_serve/` | Vista Cost-to-Serve |
| `modules/vision_tarifas/` | Vista tarifas por canal |
| `modules/pyg/` | Vista Estado de Resultados (P&G) |
| `modules/shared/ports/` | Interfaces Protocol canónicas (IParametrizationProvider, etc.) |
| `db/` | DocumentStore: providers JSON y Cosmos |

## Reglas críticas
- La fuente canónica de business rules es el Excel `NexaPricing_Simulador.xlsx`.
- No cambiar fórmulas, golden values ni parámetros sin evidencia del Excel.
- No activar Cosmos por defecto ni importar `azure-cosmos` en el flujo principal.
- No exponer `/docs` en producción (`APP_ENV=production`).
- Tests `parity` y `baseline` son críticos: nunca debilitarlos.
- Contratos públicos (DTOs, `ApiResponse`) no cambian sin análisis de impacto.

## Fuentes canónicas
- Business rules: `NexaPricing_Simulador.xlsx` (Excel V2-7)
- Parametrización activa: `storage/parametrization/{hr,gn,op}/`
- Resultados de simulación: `storage/simulation_results/`

## Comandos frecuentes
```bash
# API
python -m backend_nexa.app

# Tests (desde directorio padre)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short

# Tests parity (críticos)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m parity -v

# Pipeline completo
cd backend_nexa && make all
```

## Notas para Claude
Este archivo es contexto curado. Debe mantenerse corto y útil.
No agregar logs, outputs completos ni información temporal.
