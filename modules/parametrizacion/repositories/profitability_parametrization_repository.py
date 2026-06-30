"""Profitability parametrization repository.

Manages profitability and campaign parameters from HR parametrization:
- Minimum and target margins by business line
- Campaign values by line and month
- Ramp-up factors

Data sources: HR-Rentabilidad, HR-Campana sheets
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import ParametrizationError, ParametrizationNotFoundError, DomainError

logger = logging.getLogger(__name__)


class BusinessLineNotFoundError(DomainError):
    """Raised when a business line is not found."""
    pass


class InvalidMonthError(DomainError):
    """Raised when an invalid month is specified."""
    pass


class ProfitabilityParametrizationRepository:
    """Repository for profitability parameters from HR parametrization.

    Access patterns:
    - get_min_margin(linea_negocio: str) → float: Minimum margin for line
    - get_target_margin(linea_negocio: str) → float: Target margin for line
    - get_campaign_value(linea: str, mes: int) → float: Campaign value for month
    """

    def __init__(self, resolver: ParametrizationResolver):
        """Initialize with resolver.

        Args:
            resolver: ParametrizationResolver instance.
        """
        self._resolver = resolver
        self._hr_data: Optional[Dict[str, Any]] = None

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def get_min_margin(self, linea_negocio: str) -> float:
        """Get minimum margin for a business line.

        Args:
            linea_negocio: Business line name.

        Returns:
            Margin as decimal (e.g., 0.10 for 10%).

        Raises:
            BusinessLineNotFoundError: if line not found.
        """
        self._ensure_hr_loaded()

        rentabilidad = self._hr_data.get("rentabilidad", [])
        if not rentabilidad:
            raise ParametrizationError("HR-Rentabilidad sheet is empty", module="hr")

        for row in rentabilidad:
            if row.get("categoriaservicio") == linea_negocio:
                minimo = row.get("minimo")
                if minimo is not None:
                    try:
                        # New uploads store margins as decimal fractions (e.g. 0.17 = 17%).
                        # Legacy stored data may have percentage integers (e.g. 17.0 = 17%).
                        # Heuristic: value > 1.0 → legacy percentage integer → divide by 100.
                        valor = float(minimo)
                        if valor > 1.0:
                            valor = valor / 100.0
                        logger.debug(f"[PARAMETRIZATION] Min margin for {linea_negocio}: {valor}")
                        return valor
                    except (ValueError, TypeError):
                        raise ParametrizationError(
                            f"Invalid margin value for {linea_negocio}: {minimo}",
                            module="hr"
                        )

        raise BusinessLineNotFoundError(f"Business line '{linea_negocio}' not found in HR-Rentabilidad")

    def get_target_margin(self, linea_negocio: str) -> float:
        """Get target margin for a business line.

        Args:
            linea_negocio: Business line name.

        Returns:
            Margin as decimal (e.g., 0.15 for 15%).

        Raises:
            BusinessLineNotFoundError: if line not found.
        """
        self._ensure_hr_loaded()

        rentabilidad = self._hr_data.get("rentabilidad", [])
        if not rentabilidad:
            raise ParametrizationError("HR-Rentabilidad sheet is empty", module="hr")

        for row in rentabilidad:
            if row.get("categoriaservicio") == linea_negocio:
                margenobjetivo = row.get("margenobjetivo")
                if margenobjetivo is not None:
                    try:
                        # New uploads store margins as decimal fractions (e.g. 0.18 = 18%).
                        # Legacy stored data may have percentage integers (e.g. 18.0 = 18%).
                        # Heuristic: value > 1.0 → legacy percentage integer → divide by 100.
                        valor = float(margenobjetivo)
                        if valor > 1.0:
                            valor = valor / 100.0
                        logger.debug(f"[PARAMETRIZATION] Target margin for {linea_negocio}: {valor}")
                        return valor
                    except (ValueError, TypeError):
                        raise ParametrizationError(
                            f"Invalid margin value for {linea_negocio}: {margenobjetivo}",
                            module="hr"
                        )

        raise BusinessLineNotFoundError(f"Business line '{linea_negocio}' not found in HR-Rentabilidad")

    def get_campaign_value(self, linea: str, mes: int) -> float:
        """Get campaign value (ramp-up factor) for a business line and month.

        HR-Campana stores 60 rows per business line (months 1–60).
        For months beyond the data (> 60) the operation is at full capacity,
        so the caller should fall back to 1.0.

        Args:
            linea: Business line name.
            mes: Month number (1-60).

        Returns:
            Campaign value as decimal factor (e.g. 0.85 = 85% ramp-up).

        Raises:
            BusinessLineNotFoundError: if line / month not found in HR-Campana.
            InvalidMonthError: if month is < 1.
        """
        if mes < 1:
            raise InvalidMonthError(f"Invalid month: {mes}. Must be >= 1.")

        self._ensure_hr_loaded()

        campana = self._hr_data.get("campana", [])
        if not campana:
            raise ParametrizationError("HR-Campana sheet is empty", module="hr")

        for row in campana:
            if (row.get("categoriaservicio") == linea and
                int(float(row.get("mes", 0))) == mes):
                valor = row.get("valor")
                if valor is not None:
                    logger.debug(f"[PARAMETRIZATION] Campaign {linea}/{mes}: {valor}")
                    return float(valor)

        raise BusinessLineNotFoundError(
            f"Campaign value for line '{linea}' and month {mes} not found"
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _ensure_hr_loaded(self) -> None:
        """Load HR parametrization if not already loaded."""
        if self._hr_data is None:
            try:
                self._hr_data = self._resolver.get_active_hr()
            except ParametrizationNotFoundError as e:
                raise ParametrizationError(
                    "Cannot load profitability parameters: HR parametrization not found",
                    module="hr"
                ) from e
