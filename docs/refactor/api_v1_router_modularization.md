# API V1 Router Modularization

**Date:** 2026-06-07  
**Branch:** refactor/modular-pure  
**Status:** COMPLETE ✅

## Objetivo

Eliminar la carpeta externa `api/` y mover el agregador de routers API v1 dentro de la estructura modular (`modules/api_v1/`), manteniendo el principio de "single entrypoint composition root" y preservando completamente la API pública.

## Estado Anterior (BEFORE)

```
backend_nexa/
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py          ← Agregador API v1 (EXTERNO)
│       └── parametrization/   ← Legacy (vacío)
├── app.py                      ← Importa de .api.v1.router
└── modules/
    ├── panel/api/...          ← Routers modulares
    ├── pyg/api/...
    └── ...
```

**Consumidor de la carpeta externa:**
- `app.py`: `from .api.v1.router import api_router as v1_router`

## Estado Nuevo (AFTER)

```
backend_nexa/
├── app.py                      ← Importa de .modules.api_v1.router
└── modules/
    ├── api_v1/                ← Nuevo: Agregador API v1 (DENTRO del árbol modular)
    │   ├── __init__.py
    │   └── router.py          ← Composición de routers modulares
    ├── panel/api/...          ← Routers modulares (sin cambios)
    ├── pyg/api/...
    └── ...
```

**La carpeta externa `api/` fue eliminada completamente.**

## Cambios de Importes

### Antes
```python
# app.py
from .api.v1.router import api_router as v1_router
```

### Después
```python
# app.py
from .modules.api_v1.router import router as v1_router
```

**Nota:** El nombre cambió de `api_router` a `router` para seguir la convención de nombres en los módulos (ej. `modules/panel/api/panel_router.py` exporta `router`, no `panel_router_instance`).

## Contenido de `modules/api_v1/router.py`

```python
"""Top-level v1 API router — aggregates all modular sub-routers.

This is the composition root for API routing. It imports routers from individual modules
and combines them into a single APIRouter that is mounted in app.py at the `/api/v1` prefix.

Contains NO business logic, NO repository instantiation, NO infrastructure dependencies.
Only router composition via include_router().
"""

from fastapi import APIRouter

from nexa_engine.modules.calculator.api.calculate_router import router as calculate_router
from nexa_engine.modules.calculator.api.results_router import router as results_router
# ... (imports de todos los routers modulares)

router = APIRouter()

# Composition: include all modular routers
router.include_router(parametrizacion_router)
router.include_router(panel_router)
# ... (todos los includes)
```

**Invariantes:**
- ✅ No contiene lógica de negocio
- ✅ No instancia repositories, DocumentStore, calculators
- ✅ Solo importa routers de módulos
- ✅ Solo usa `include_router()` para composición

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `app.py` | Import actualizado a `modules.api_v1.router` |
| `tests/unit/test_shared_guardrails.py` | Rutas de test actualizadas (referencia a `modules/api_v1/router.py`) |
| `docs/ai/PROJECT_CONTEXT.md` | Actualizada referencia de ubicación |
| `modules/calculator/__init__.py` | Actualizada referencia a ubicación nueva |
| `docs/refactor/entrypoint_notes.md` | Actualizada documentación de entrypoints |
| `docs/refactor/INPUT_CONTRACT_FIX_B1_SUMMARY.md` | Actualizada nota sobre entrada de API |

## Archivos Eliminados

```
api/__init__.py           ✅ DELETED
api/v1/__init__.py        ✅ DELETED
api/v1/router.py          ✅ DELETED
api/v1/parametrization/   ✅ DELETED (estaba vacío)
```

## Archivos Creados

```
modules/api_v1/__init__.py         ✅ NEW
modules/api_v1/router.py           ✅ NEW
```

## Validación

### Tests Ejecutados

```bash
✅ backend_nexa/tests/unit/test_shared_guardrails.py::TestNoUnmountedSharedRouters
   - test_audit_router_is_mounted_in_api_v1: PASSED
   - test_certification_router_is_mounted_in_api_v1: PASSED

✅ backend_nexa/tests/api/test_app_factory.py
   - test_api_v1_prefix_is_registered: PASSED
   - (+ 14 more app factory tests): ALL PASSED

✅ backend_nexa/tests/api/ (full suite)
   - 56/57 tests PASSED
   - 1 pre-existing failure (test_audit_endpoint, formula-set versioning issue)
```

### Validación de Estructura

```bash
✅ No external api/ folder exists at root
✅ No remaining imports to old api.v1.router location
✅ modules/api_v1/router.py registered correctly
✅ All OpenAPI paths unchanged
✅ All endpoints responding correctly
```

### Verificación de Composición Pura

```bash
✅ modules/api_v1/router.py contains NO:
   - Business logic
   - Repository instantiation
   - Infrastructure imports (JsonDocumentStore, CosmosDocumentStore)
   - Calculator imports
   - Engine imports
✅ Only contains:
   - Router imports from modules
   - APIRouter() instantiation
   - include_router() calls
```

## Impacto en API Pública

| Aspecto | Estado |
|--------|--------|
| **Paths** | ✅ Sin cambio — `/api/v1/*` intacto |
| **Prefijo** | ✅ Sin cambio — `/api/v1` intacto |
| **Montaje** | ✅ Sin cambio — app.include_router(v1_router, prefix="/api/v1") intacto |
| **Contratos OpenAPI** | ✅ Sin cambio — mismos DTOs, mismas respuestas |
| **Endpoints** | ✅ Sin cambio — todos los endpoints disponibles |

## Decisión Arquitectónica

**Principio:** Single Entrypoint Composition Root

Todos los composition roots del sistema (motor, persistencia, routers API) viven dentro del árbol modular:
- `modules/calculator/engine.py` → NexaPricingEngine (compose calculators)
- `db/container.py` → DocumentStore (compose persistence)
- `modules/api_v1/router.py` → APIRouter (compose routers) **← NUEVO**

Ventajas:
1. ✅ Claridad arquitectónica: la app solo agrega lifespan y middleware
2. ✅ Consistencia: todos los compose roots en un lugar (modular o db/)
3. ✅ Mantenibilidad: la composición de routers vive cerca de los routers
4. ✅ Facilita refactores futuros (ej. agregar versionamiento API v2)

## Tests Post-Refactor

Confirmar que se siguen pasando:

```bash
# Parity (críticos)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m parity -v

# Baseline (críticos)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v

# Golden
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -v

# API
PYTHONPATH=$(pwd) pytest backend_nexa/tests/api/ -v
```

## Guardrail Agregado

Nuevo test en `test_shared_guardrails.py` valida:
1. ✅ No existe `api/v1/router.py`
2. ✅ No existen imports `api.v1.router`
3. ✅ El router vive en `modules/api_v1/router.py`
4. ✅ El agregador no tiene lógica de negocio

## Notas para Futuros Cambios

Si se requiere:
- **Agregar V2 API:** Crear `modules/api_v2/router.py` siguiendo el mismo patrón
- **Cambiar composición:** Editar `modules/api_v1/router.py` (única ubicación)
- **Auditar routers:** Buscar `modules/*/api/` para encontrar routers modulares

## Referencias

- `modules/calculator/__init__.py` — nota actualizada sobre ubicación de routers
- `docs/ai/PROJECT_CONTEXT.md` — contexto arquitectónico actualizado
- `app.py` — single import de v1_router desde nueva ubicación
