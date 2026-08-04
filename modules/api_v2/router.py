"""Router principal de la API v2."""
from fastapi import APIRouter

from .calculate.calculate_router import router as calculate_router
from .results.results_router import router as results_router

router = APIRouter()
router.include_router(calculate_router)
router.include_router(results_router)
