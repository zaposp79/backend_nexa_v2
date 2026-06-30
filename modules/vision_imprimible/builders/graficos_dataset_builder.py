"""Read-only access to precomputed graph datasets for printable vision."""

from __future__ import annotations

import logging
from typing import Optional

from nexa_engine.modules.calculator_motor.formulas.graphics.models import GraficosResult
from nexa_engine.modules.shared.models import PricingRequest, PricingResult

logger = logging.getLogger("nexa.vision_datasets")


class GraficosDatasetBuilder:
    """Returns already-computed graph datasets from ``PricingResult``."""

    def __init__(self, parametrizacion: Optional[object] = None) -> None:
        self._parametrizacion = parametrizacion

    def construir(
        self,
        resultado: PricingResult,
        solicitud: PricingRequest,
    ) -> Optional[GraficosResult]:
        """Return the graph payload already stored on the result, if any."""
        datasets = getattr(resultado, "datasets_vision", None)
        if datasets is None:
            logger.debug("[vision_datasets] graficos skipped: datasets_vision missing")
            return None
        return getattr(datasets, "graficos", None)
