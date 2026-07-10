"""Business rules getter methods for ParametrizationProvider.

Mixin for ParametrizationProvider — extracted FASE Z.2.
BUSINESS_RULES_CANONICAL_MIGRATION: reads from canonical YAML config.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from nexa_engine.modules.shared.config.business_rules.loader import (
    load_business_rules_cached,
)
from nexa_engine.modules.shared.exceptions import ParametrizationError

logger = logging.getLogger(__name__)


class ProviderBusinessRulesMixin:
    """Mixin: Business rules getter methods for ParametrizationProvider.

    Reads from canonical YAML under modules/shared/config/business_rules/.
    No storage/parametrization dependency.
    """

    def get_politicas_comerciales(self) -> List[Dict[str, Any]]:
        """Policy min/max ranges for contingencies, markup, descuento."""
        try:
            rules = load_business_rules_cached("politicas_comerciales")
            value = rules["politicas_comerciales"]
        except KeyError as exc:
            raise ParametrizationError(
                f"politicas_comerciales.yaml missing key: {exc}", module="business_rules"
            ) from exc
        logger.debug(
            "[PARAMETRIZATION] operation=get_politicas_comerciales count=%d",
            len(value),
        )
        return value

    def get_riesgo_config(self) -> Dict[str, Any]:
        """Risk model configuration."""
        try:
            rules = load_business_rules_cached("riesgo")
        except Exception as exc:
            raise ParametrizationError(
                f"riesgo.yaml load failed: {exc}", module="business_rules"
            ) from exc
        logger.debug("[PARAMETRIZATION] operation=get_riesgo_config")
        return rules

    def get_portfolio_clientes(self) -> Optional[Dict[str, Any]]:
        """Portfolio reference data for graph band calculations.

        OP-MargenBruto removed from upload contract — always returns None.
        """
        try:
            clientes = self._financial.get_portfolio_margen_bruto_rows()  # type: ignore[attr-defined]
            if not clientes:
                return None

            sums: defaultdict = defaultdict(list)
            for row in clientes:
                sums[row["categoria"]].append(row["margen_bruto"])
            promedios = {
                cat: sum(vals) / len(vals)
                for cat, vals in sums.items()
                if vals
            }

            logger.debug(
                "[PARAMETRIZATION] operation=get_portfolio_clientes rows=%d categories=%d",
                len(clientes), len(promedios),
            )
            return {"clientes": clientes, "promedios_por_categoria": promedios}
        except Exception as exc:
            logger.warning("[PARAMETRIZATION] get_portfolio_clientes failed: %s", exc)
            return None


__all__ = ["ProviderBusinessRulesMixin"]
