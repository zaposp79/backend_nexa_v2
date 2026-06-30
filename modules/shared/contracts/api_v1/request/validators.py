"""Cross-field validators reused by EntryDataV1."""
from __future__ import annotations

from typing import Any, Dict, Set


def _has_data(section: Any, *list_attrs: str) -> bool:
    """Return True if any of the named list-attributes is non-empty."""
    if section is None:
        return False
    if isinstance(section, dict):
        for attr in list_attrs:
            val = section.get(attr)
            if val:
                return True
        return False
    for attr in list_attrs:
        val = getattr(section, attr, None)
        if val:
            return True
    return False


def infer_cadenas_activas(
    cadena_a: Any,
    cadena_b: Any,
    cadena_c: Any,
    explicit: Set[str] | None = None,
) -> Set[str]:
    """
    Return the set of active chains.

    If ``explicit`` is provided (e.g., the request set ``cadenas_activas``
    or ``panel.cadenas_activas`` was sent), it wins. Otherwise inferred
    from whichever chain has non-empty data.

    Resolves W7-OBS-3: legacy fixtures without ``cadenas_activas`` get a
    deterministic value derived from the payload contents.
    """
    if explicit:
        return {c.upper() for c in explicit if c}

    active: Set[str] = set()
    if _has_data(cadena_a, "perfiles"):
        active.add("A")
    if _has_data(cadena_b, "canales", "opex_consumo_variable", "equipo_sm"):
        active.add("B")
    if _has_data(cadena_c, "canales", "equipo_transversal"):
        active.add("C")

    if not active:
        # Default to "A" so downstream loaders that require at least one
        # active chain don't crash on minimal fixtures.
        active.add("A")
    return active


def coerce_cadenas_activas_from_panel(panel_data: Dict[str, Any]) -> Set[str] | None:
    """
    Pick up legacy nested form ``panel.cadenas_activas = {cadena_a: true, ...}``
    and lift it to the top-level ``Set[Literal["A","B","C"]]``.

    Returns None when no nested form is present.
    """
    if not isinstance(panel_data, dict):
        return None
    nested = panel_data.get("cadenas_activas")
    if not isinstance(nested, dict):
        return None
    out: Set[str] = set()
    if nested.get("cadena_a"):
        out.add("A")
    if nested.get("cadena_b"):
        out.add("B")
    if nested.get("cadena_c"):
        out.add("C")
    return out or None
