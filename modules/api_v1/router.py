"""Enrutador API de nivel superior v1 — solo rutas públicas de producción.

Agrupa subenrutadores modulares en un único APIRouter montado en app.py con
prefijo `/api/v1`. NO expone rutas de certificación, debug, duplicados legacy.

Auditoría se incluye con include_in_schema=False: funcional en runtime pero
oculta del schema OpenAPI público.
"""
from fastapi import APIRouter

from nexa_engine.modules.calculator.api.calculate_router import (
    router as calculate_router,
)
from nexa_engine.modules.cadena_a.api.chain_a_router import router as chain_a_router
from nexa_engine.modules.cadena_b.api.chain_b_router import router as chain_b_router
from nexa_engine.modules.cadena_c.api.chain_c_router import router as chain_c_router
from nexa_engine.modules.panel.api.panel_router import router as panel_router
from nexa_engine.modules.parametrizacion.api.router import parametrizacion_router
from nexa_engine.modules.vision_pyg.api.vision_router import router as pyg_router
from nexa_engine.modules.vision_cost_to_serve.api.router import (
    router as cost_to_serve_router,
)
from nexa_engine.modules.vision_imprimible.api.router import (
    router as vision_imprimible_router,
)
from nexa_engine.modules.vision_tarifas.api.router import (
    router as vision_tarifas_router,
)
from nexa_engine.modules.audit.api.audit_router import router as audit_router

router = APIRouter()

# Public v1 routes
router.include_router(parametrizacion_router)
router.include_router(panel_router)
router.include_router(chain_a_router)
router.include_router(chain_b_router)
router.include_router(chain_c_router)
router.include_router(calculate_router)
router.include_router(vision_imprimible_router)
router.include_router(pyg_router)
router.include_router(vision_tarifas_router)
router.include_router(cost_to_serve_router)

# Hidden from schema but functional at runtime (used by internal tools / debugging)
router.include_router(audit_router, include_in_schema=False)

# Certification router intentionally excluded — no functional routes needed in v1
