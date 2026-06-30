"""Infrastructure parametrization repository.

Manages infrastructure costs from HR parametrization:
- Cost per workstation by locality (rent, energy, water, gas, cleaning, security, maintenance)
- Medical exam costs by city

Data source: HR-CostoFijo and HR-Med-Seg sheets
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, Optional

from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import ParametrizationError, ParametrizationNotFoundError, LocalityNotFoundError

logger = logging.getLogger(__name__)

# HR legacy: some versions stored costo_fijo in miles de COP (e.g. 415.975 = 415,975 COP).
# This threshold distinguishes "miles" values from full-COP values.
# Assumption: no real infrastructure cost in COP is legitimately below 10,000 COP per month.
# Idempotent: values already in full COP (>= threshold) pass through unchanged.
_HR_INFRA_COST_SCALE_THRESHOLD = 10_000.0

# Servicios that historically may come in miles de COP and should be auto-scaled.
# agua, gas, mantenimiento legitimately have small COP values and are preserved as-is.
_SERVICIOS_ESCALA_GRANDE = {
    "arriendo",
    "energia",
    "vigilancia",
    "aseo",
}


def _normalizar_costo_cop(valor: float) -> float:
    """Normalize HR infrastructure costs from legacy miles-COP to full COP.

    HR-CostoFijo in older parametrization uploads stored values in miles de COP
    (e.g. 415.975 meant 415,975 COP). This function detects and corrects that scale.

    Rule: if valor < 10,000 AND valor > 0, multiply by 1,000.
    Idempotent: values already in full COP are returned unchanged.
    Does NOT apply to percentages, quantities, or month counts — only monetary costs.

    Args:
        valor: Raw float from HR-CostoFijo storage.

    Returns:
        Cost in full COP.
    """
    if valor is None or valor == 0:
        return valor if valor is not None else 0.0
    if valor < _HR_INFRA_COST_SCALE_THRESHOLD:
        logger.debug(
            "[HR_INFRA_SCALE] Detected legacy miles value %.3f → %.0f COP (×1000)",
            valor, valor * 1_000.0,
        )
        return valor * 1_000.0
    return valor


class InfrastructureParametrizationRepository:
    """Repository for infrastructure costs from HR parametrization.

    Handles locality-based cost resolution with strict validation.

    Access patterns:
    - get_infrastructure_costs(localidad: str) → Dict: All costs for a locality
    - get_medical_exam_cost(ciudad: str) → float: Medical exam cost for a city
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

    # Mapping HR-CostoFijo servicio names → canonical keys (in full COP after ×1000)
    _SERVICIO_MAP: Dict[str, str] = {
        "energía":         "energia",
        "energia":         "energia",
        "agua":            "agua",
        "gas":             "gas",
        "aseo y cafeteria":"aseo",
        "aseo":            "aseo",
        "arriendo":        "arriendo",
        "vigilancia":      "vigilancia",
        "mantenimiento":   "mantenimiento",
    }

    def get_infrastructure_costs(self, localidad: str) -> Dict[str, float]:
        """Get all infrastructure costs for a locality, in full COP.

        HR-CostoFijo stores values in COP directo (not in thousands).
        No conversion needed — values are already in the correct currency scale.

        Returns costs for: arriendo, energia, agua, gas, aseo, vigilancia, mantenimiento.

        Args:
            localidad: Locality/city name (case/accent insensitive, supports compound names).

        Returns:
            Dict with cost keys in full COP (no transformation). Missing keys default to 0.0.

        Raises:
            LocalityNotFoundError: if localidad has no data in HR-CostoFijo.
            ParametrizationError: if data invalid.
        """
        self._ensure_hr_loaded()

        costo_fijo = self._hr_data.get("costo_fijo", [])
        if not costo_fijo:
            raise ParametrizationError("HR-CostoFijo sheet is empty", module="hr")

        costs: Dict[str, float] = {}
        found_any = False
        localidad_norm_full = self._normalize_locality(localidad, keep_compound=True)
        localidad_norm_base = self._normalize_locality(localidad, keep_compound=False)
        # A compound query (e.g. "Bogota - Toberin") names a specific sub-locality;
        # the base-city / suffix fallbacks below would conflate it with sibling
        # sub-localities ("Bogota - Americas", etc.) and the last row would win.
        query_is_compound = " - " in localidad_norm_full

        def _loc_matches(row_localidad: str) -> bool:
            """Match by:
            1. Exact normalized (full name including compound)
            2. Base city name match (only when the query is a bare city, e.g. "Bogota")
            3. Suffix match (only when the query is a bare locality part, e.g. "Toberin")
            """
            row_norm_full = self._normalize_locality(row_localidad, keep_compound=True)
            row_norm_base = self._normalize_locality(row_localidad, keep_compound=False)

            # Case 1: Exact full name match (e.g., "Bogota - Toberin" == "Bogota - Toberin")
            if row_norm_full == localidad_norm_full:
                return True

            # Fallbacks 2 & 3 only apply when the query is NOT compound; otherwise an
            # exact match is required so sibling sub-localities don't collide.
            if query_is_compound:
                return False

            # Case 2: Base city match (e.g., user passes "Bogota", matches "Bogota - Toberin")
            if row_norm_base == localidad_norm_base:
                return True

            # Case 3: Suffix match (user passes "Toberin", matches "Bogota - Toberin")
            # Extract the locality part after " - " if it exists
            if " - " in row_norm_full:
                row_suffix = row_norm_full.split(" - ", 1)[1].strip()
                if row_suffix == localidad_norm_full:
                    return True

            return False

        matched_localidad: Optional[str] = None
        for row in costo_fijo:
            row_loc = row.get("localidad", "")
            if _loc_matches(row_loc):
                raw_servicio = row.get("servicio", "").lower().strip()
                canonical    = self._SERVICIO_MAP.get(raw_servicio)
                if canonical is None:
                    continue  # skip corrupted/unknown rows
                # Compatibilidad HR storage legacy: estos servicios históricos pueden venir en miles COP.
                raw_valor = float(row.get("valor") or 0)
                if canonical in _SERVICIOS_ESCALA_GRANDE:
                    valor = _normalizar_costo_cop(raw_valor)
                else:
                    # agua, gas, mantenimiento se preservan aunque sean < 10000
                    valor = raw_valor
                costs[canonical] = valor
                found_any = True
                matched_localidad = row_loc  # capture the resolved name for logging

        if not found_any:
            logger.warning(
                "[LOCALITY_MATCH] No match found for localidad=%r (normalized: %r). "
                "Available localities: %s",
                localidad, localidad_norm_full,
                [self._normalize_locality(r.get("localidad", ""), keep_compound=True)
                 for r in costo_fijo if r.get("localidad")]
            )
            raise LocalityNotFoundError("infrastructure", localidad)

        # Ensure all expected keys exist
        for service in ["arriendo", "energia", "agua", "gas", "aseo", "vigilancia", "mantenimiento"]:
            if service not in costs:
                costs[service] = 0.0

        resolved = matched_localidad or localidad
        if resolved != localidad:
            logger.info(
                "[LOCALITY_MATCH] Localidad '%s' resolved to '%s' (base: '%s' → '%s')",
                localidad, resolved, localidad_norm_base, localidad_norm_full
            )
        logger.info("[PARAMETRIZATION] Loaded infrastructure costs for %s from HR", resolved)
        return costs

    def get_medical_exam_cost(self, ciudad: str) -> float:
        """Get medical exam cost for a city.

        Args:
            ciudad: City name (accented or not — normalized internally).

        Returns:
            Cost in COP directo. HR-Med-Seg stores values in full COP (after master unification),
            no conversion needed — values are already in the correct currency scale.

        Raises:
            ParametrizationError: if city not found or cost invalid.
        """
        self._ensure_hr_loaded()

        med_seg = self._hr_data.get("med_seg", [])
        if not med_seg:
            logger.warning("HR-Med-Seg sheet is empty, using default")
            return 60800.0  # Default Bogotá rate

        # Find "examen medico nuevos" entry for this city
        # Normalize with accent-stripping so "Bogotá" matches "Bogota"
        ciudad_normalized = self._normalize_locality(ciudad, keep_compound=False)

        for row in med_seg:
            row_ciudad = self._normalize_locality(row.get("localidad", ""), keep_compound=False)
            row_centro = row.get("centrocosto", "").lower()

            if row_ciudad == ciudad_normalized and "examen" in row_centro and "medico" in row_centro:
                valor = row.get("valor")
                if valor is not None:
                    # HR-Med-Seg master values are in COP directo (after master unification)
                    # No conversion needed — values are already in full COP
                    cost_cop = float(valor)
                    logger.info(
                        f"[MONEY_NORMALIZATION] Loaded medical exam cost for {ciudad}: "
                        f"{cost_cop:,.0f} COP (from master HR-Med-Seg, no conversion applied)"
                    )
                    return cost_cop

        # Fallback: use 58,000 COP for cities not covered (master_data default)
        logger.warning(f"Medical exam cost not found for {ciudad}, using default 58000")
        return 58000.0

    @staticmethod
    def _normalize_locality(name: str, keep_compound: bool = True) -> str:
        """Normalize locality name for lookups: strip accents, lowercase, normalize spaces.

        Args:
            name: Locality name (may include compound suffix like "Bogota - Toberin")
            keep_compound: If True, keeps " - " compound part; if False, removes it.

        Examples with keep_compound=True:
            "Bogotá"  → "bogota"
            "Bogota - Toberin"  → "bogota - toberin"
            "Bogota - Américas"  → "bogota - americas"
            "MEDELLÍN - CENTRO"  → "medellin - centro"

        Examples with keep_compound=False:
            "Bogotá"  → "bogota"
            "Bogota - Toberin"  → "bogota"
            "Medellín - Zona"  → "medellin"
        """
        if not isinstance(name, str):
            name = str(name) if name is not None else ""

        # Strip accents via NFKD decomposition (canonical compatibility)
        nfkd = unicodedata.normalize("NFKD", name)
        ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))

        # Normalize internal spacing: replace multiple spaces/dashes with single space around dash
        ascii_str = re.sub(r'\s*-\s*', ' - ', ascii_str)

        # Remove compound suffixes if requested
        if not keep_compound:
            ascii_str = re.sub(r'\s*-\s*.*$', '', ascii_str)

        return ascii_str.lower().strip()

    @staticmethod
    def _normalize_city(name: str) -> str:
        """Deprecated: use _normalize_locality() instead."""
        return InfrastructureParametrizationRepository._normalize_locality(
            name, keep_compound=False
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
                    "Cannot load infrastructure costs: HR parametrization not found",
                    module="hr"
                ) from e
