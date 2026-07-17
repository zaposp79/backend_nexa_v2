"""Cadena A — service layer.

Builds ParametrosCadenaA from active HR (ratios de personal),
OP (opex fijo, hardware/software) and GN (catálogos modalidad/canal).
"""

from __future__ import annotations
from typing import Any, Dict, List

from nexa_engine.modules.parametrizacion.services.resolver import (
    ParametrizationResolver,
)
from nexa_engine.modules.cadena_a.dto.cadena_a_dto import (
    HardSoftItem,
    OpexFijoItem,
    ParametrosCadenaA,
    Ratio,
)

_resolver = ParametrizationResolver()


def _get_sheet_rows(op_data: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    for sheet in op_data.get("sheets", []):
        if sheet.get("key") == key:
            return sheet.get("rows", [])
    # Flat format (OP mapper to_dict): data[key] is a list directly
    flat = op_data.get(key)
    if isinstance(flat, list):
        return flat
    return []


def _gn_catalog(gn: Dict[str, Any], key: str) -> List[str]:
    return [i["name"] for i in gn.get("lv", {}).get("catalogs", {}).get(key, [])]


def build_cadena_a_parametros() -> ParametrosCadenaA:
    """
    Build ParametrosCadenaA from active storage.

    Sources:
      - HR: ratios de personal por cargo/servicio
      - OP: opex fijo (sheet=opexfijo), hardware/software (sheet=hardsoft)
      - GN: catálogos de modalidad y canal
    """
    hr = _resolver.get_active_hr()
    op = _resolver.get_active_op()
    gn = _resolver.get_active_gn()

    ratios = [
        Ratio(
            cargo=r["cargo"],
            servicio=r["servicio"],
            agentes=r["agentes"],
            tipo=r.get("tipo", ""),
        )
        for r in hr.get("ratios", [])
    ]

    opex_fijo = [
        OpexFijoItem(item=r["opexitem"], valor=r["valor"])
        for r in _get_sheet_rows(op, "opexfijo")
    ]

    hardware_software = [
        HardSoftItem(
            item=r["hardwaresoftware"],
            valor=r["valor"],
            cantidad_meses=r.get("cantidadmes", 1.0),
            tipo=r.get("tipo", ""),
        )
        for r in _get_sheet_rows(op, "hardsoft")
    ]

    # canal was split into canalinbound + canaloutbound; merge and deduplicate
    canales = list(dict.fromkeys(
        _gn_catalog(gn, "canalinbound") + _gn_catalog(gn, "canaloutbound")
    ))

    return ParametrosCadenaA(
        ratios=ratios,
        opex_fijo=opex_fijo,
        hardware_software=hardware_software,
        modalidades=_gn_catalog(gn, "modalidad"),
        canales=canales,
    )


__all__ = ["build_cadena_a_parametros"]
