"""
api-v1 → legacy adapter.

Converts :class:`EntryDataV1` to the dict shape consumed by
:class:`nexa_engine.modules.calculator_motor.adapters.user_input_loader.UserInputLoader` and to
the legacy :class:`nexa_engine.modules.calculator_motor.request_dto.SimulationRequest`.

This is the single seam through which the strict frozen contract enters
the (still untyped) historical pipeline. The engine itself is **not**
modified.
"""
from __future__ import annotations

from typing import Any, Dict

from .request.entry_data import EntryDataV1


def entry_data_v1_to_legacy_dict(entry: EntryDataV1) -> Dict[str, Any]:
    """Convert :class:`EntryDataV1` to the legacy ``user_input`` dict."""
    return entry.to_legacy_dict()


def entry_data_v1_to_simulation_request(entry: EntryDataV1):
    """
    Convert :class:`EntryDataV1` to the legacy ``SimulationRequest`` Pydantic
    model. Useful from tests/contract verification; production endpoints
    keep using :class:`UserInputLoader` directly via :func:`to_legacy_dict`.
    """
    # Import here to avoid a hard contracts→simulation cycle at import time.
    from nexa_engine.modules.calculator_motor.dto.request_dto import SimulationRequest

    legacy = entry.to_legacy_dict()
    # SimulationRequest forbids master-data keys but tolerates extras at root;
    # strip the lifted top-level cadenas_activas if any sneaked through.
    legacy.pop("cadenas_activas", None)
    # SimulationRequest.PanelDeControlRequest is strict (extra="forbid") and
    # does not declare ``cadenas_activas`` — drop it from the panel for the
    # strict-DTO path. UserInputLoader still receives the nested form via
    # :func:`entry_data_v1_to_legacy_dict`.
    panel = legacy.get("panel_de_control")
    if isinstance(panel, dict):
        panel = {k: v for k, v in panel.items() if k != "cadenas_activas"}
        legacy["panel_de_control"] = panel
    return SimulationRequest.model_validate(legacy)


def legacy_dict_to_entry_data_v1(payload: Dict[str, Any]) -> EntryDataV1:
    """
    Inverse helper: parse a legacy ``user_input`` payload as
    :class:`EntryDataV1`, applying the cross-field validators.

    Used by tests to verify the contract accepts every baseline ``request.json``.
    """
    return EntryDataV1.model_validate(payload)
