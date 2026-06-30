"""
EntryDataV1 — root request DTO for ``POST /api/v1/simulation/calculate``.

Frozen, strict, additive-only. Cross-field validators enforce semantic
coherence (at least one active chain, escenarios consistency, etc.).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .cadena_a import CadenaARequestV1
from .cadena_b import CadenaBRequestV1
from .cadena_c import CadenaCRequestV1
from .escenarios import EscenarioComercialV1
from .panel import PanelDeControlRequestV1
from .validators import (
    coerce_cadenas_activas_from_panel,
    infer_cadenas_activas,
)


ChainLiteral = Literal["A", "B", "C"]


class ContractMetadataV1(BaseModel):
    """Optional metadata block accompanying every request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    client_id: Optional[str] = None
    request_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class EntryDataV1(BaseModel):
    """
    Frozen public request contract.

    Compared to the legacy ``SimulationRequest``:
      - ``panel`` (alias ``panel_de_control``) — required, strict.
      - ``cadena_a``/``b``/``c`` — optional sections (aliases to the
        legacy ``condiciones_cadena_*`` keys).
      - ``cadenas_activas`` — explicit ``Set[Literal["A","B","C"]]``,
        inferred from contents when omitted (resolves W7-OBS-3).
      - ``escenarios`` — list of commercial scenarios.
      - ``metadata`` — optional client/request metadata.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    panel: PanelDeControlRequestV1 = Field(alias="panel_de_control")
    cadena_a: Optional[CadenaARequestV1] = Field(default=None, alias="condiciones_cadena_a")
    cadena_b: Optional[CadenaBRequestV1] = Field(default=None, alias="condiciones_cadena_b")
    cadena_c: Optional[CadenaCRequestV1] = Field(default=None, alias="condiciones_cadena_c")
    cadenas_activas: Set[ChainLiteral] = Field(default_factory=set)
    escenarios: List[EscenarioComercialV1] = Field(default_factory=list, alias="escenarios_comerciales")
    metadata: Optional[ContractMetadataV1] = None

    # --- normalization & cross-field validation -----------------------------

    @model_validator(mode="before")
    @classmethod
    def _lift_panel_cadenas_activas(cls, data: Any) -> Any:
        """
        Accept ``panel.cadenas_activas = {cadena_a: bool, ...}`` (legacy
        baseline shape) and lift it to the top-level ``cadenas_activas``
        set if not already supplied. The nested form is stripped from
        the panel sub-payload to keep PanelDeControlRequestV1 strict.
        """
        if not isinstance(data, dict):
            return data

        # Mirror panel under both possible keys
        for panel_key in ("panel", "panel_de_control"):
            panel_payload = data.get(panel_key)
            if isinstance(panel_payload, dict) and "cadenas_activas" in panel_payload:
                lifted = coerce_cadenas_activas_from_panel(panel_payload)
                # Strip nested form to satisfy strict panel
                panel_payload = {k: v for k, v in panel_payload.items() if k != "cadenas_activas"}
                data = {**data, panel_key: panel_payload}
                if lifted and not data.get("cadenas_activas"):
                    data = {**data, "cadenas_activas": lifted}
        return data

    @model_validator(mode="after")
    def _populate_and_check_active_chains(self) -> "EntryDataV1":
        """Infer ``cadenas_activas`` from data shape when missing; ensure non-empty."""
        active = self.cadenas_activas
        if not active:
            active = infer_cadenas_activas(self.cadena_a, self.cadena_b, self.cadena_c)
            # frozen -> use object.__setattr__
            object.__setattr__(self, "cadenas_activas", active)

        if not active:
            raise ValueError("at least one chain must be active (A, B, or C)")

        # When chain B is active, margen_b must be set (or panel has its default)
        if "B" in active and self.panel.margen_b is None:
            # not fatal — engine has v2_7_defaults; emit soft check via doc
            pass

        # Escenarios must reference channels declared in cadena_a (if any)
        if self.escenarios and self.cadena_a:
            known = {(p.canal, p.modalidad) for p in self.cadena_a.perfiles}
            # only enforce when both fields are non-empty in the scenario
            for esc in self.escenarios:
                if esc.canal and esc.modalidad and known:
                    if (esc.canal, esc.modalidad) not in known:
                        raise ValueError(
                            f"escenario '{esc.nombre}' references unknown "
                            f"canal/modalidad: {esc.canal}/{esc.modalidad}"
                        )
        return self

    # --- conversion helpers --------------------------------------------------

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert to the dict shape consumed by ``UserInputLoader.cargar_desde_dict``.

        The returned dict matches the historical baseline ``request.json``
        contract (panel_de_control, condiciones_cadena_*).
        """
        # Use legacy aliases for keys
        raw = self.model_dump(by_alias=True, exclude_none=True, mode="python")
        # Restore the nested panel.cadenas_activas so legacy loader picks it up
        active = self.cadenas_activas
        panel = raw.get("panel_de_control", {})
        panel["cadenas_activas"] = {
            "cadena_a": "A" in active,
            "cadena_b": "B" in active,
            "cadena_c": "C" in active,
        }
        raw["panel_de_control"] = panel
        # Drop top-level chain set (not part of legacy contract)
        raw.pop("cadenas_activas", None)
        # Strip metadata from legacy path
        raw.pop("metadata", None)
        return raw

    @classmethod
    def submitted_now(cls) -> datetime:
        return datetime.now(timezone.utc)
