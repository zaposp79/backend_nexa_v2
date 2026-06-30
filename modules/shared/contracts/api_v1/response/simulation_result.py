"""Unified simulation result envelope (api-v1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .kpis import KpisV1
from .visions import VisionsBundleV1


class SimulationResultV1(BaseModel):
    """
    Stable wrapper around all simulation outputs.

    The legacy endpoint continues to return its existing payload shape;
    this envelope is used when the caller asks for ``api-v1`` explicitly
    (``Accept: application/vnd.nexa.v1+json`` or ``?format=v1``).

    WAVE 14 additions (additive only):
        * ``formula_set``           — version tag of the active formula set.
        * ``parametrization_hashes`` — SHA-256 of the active parametrization
          JSONs (hr/gn/op/business_rules).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    simulation_id: str
    api_version: Literal["api-v1"] = "api-v1"
    engine_version: str = "unknown"
    parametrization_version: str = "unknown"
    baseline_version: Optional[str] = None
    formula_set: str = "formula-set-v2-7"
    parametrization_hashes: Dict[str, str] = Field(default_factory=dict)
    visions: VisionsBundleV1 = Field(default_factory=VisionsBundleV1)
    kpis: KpisV1 = Field(default_factory=KpisV1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
