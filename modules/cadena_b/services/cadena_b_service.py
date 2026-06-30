"""Cadena B (and C) — service layer.

Builds ParametrosCadenasBC from active OP (dispositivos requeridos)
and HR (equipo HITL). Both Cadena B and Cadena C use this service
because they share the same parametrization inputs.
"""
from __future__ import annotations

from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.cadena_b.dto.cadena_b_dto import (
    DispositivoRequerido, EquipoHITL, ParametrosCadenasBC,
)

_resolver = ParametrizationResolver()


def build_cadenas_bc_parametros() -> ParametrosCadenasBC:
    """
    Build ParametrosCadenasBC from active storage.

    Sources:
      - OP: sheet=dispositivorequerido → lista de dispositivos requeridos
      - HR: extra_sheets[HR-EquipoHITL] → equipo HITL con ratio
    """
    op = _resolver.get_active_op()
    hr = _resolver.get_active_hr()

    dispositivos = []
    for sheet in op.get("sheets", []):
        if sheet.get("key") == "dispositivorequerido":
            catalogs = sheet.get("catalogs", {}).get("dispositivorequerido", [])
            dispositivos = [DispositivoRequerido(nombre=c["name"]) for c in catalogs]
            break

    hitl_rows = hr.get("extra_sheets", {}).get("HR-EquipoHITL", [])
    equipo_hitl = [EquipoHITL(nombre=r["equipohitl"], ratio=r["ratio"]) for r in hitl_rows]

    return ParametrosCadenasBC(
        dispositivos_requeridos=dispositivos,
        equipo_hitl=equipo_hitl,
    )


__all__ = ["build_cadenas_bc_parametros"]
