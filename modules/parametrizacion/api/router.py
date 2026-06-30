"""Aggregated router for the parametrizacion capability.

Registra únicamente los routers de los dominios GN, HR y OP.
Los servicios de cadena_a/b/c son módulos independientes con sus propios
routers registrados en api/v1/router.py.
"""
from fastapi import APIRouter

from nexa_engine.modules.parametrizacion.gn.api.router import router as gn_router
from nexa_engine.modules.parametrizacion.hr.api.router import router as hr_router
from nexa_engine.modules.parametrizacion.op.api.router import router as op_router

parametrizacion_router = APIRouter()
parametrizacion_router.include_router(hr_router)
parametrizacion_router.include_router(gn_router)
parametrizacion_router.include_router(op_router)

__all__ = ["parametrizacion_router"]
