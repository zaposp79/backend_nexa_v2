"""Cadena A — Parameters Query Service.

Ensambla el read model ParametrosCadenaA a partir de los repositorios de
datos maestros HR, OP y GN. Propietario: modules/cadena_a.

Consulta parametrización a través de los repositorios tipados de cada dominio.
"""
from __future__ import annotations

from typing import Any, Dict, List

from nexa_engine.modules.cadena_a.dto.cadena_a_dto import (
    HardSoftItem,
    OpexFijoItem,
    ParametrosCadenaA,
    Ratio,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
    HRActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
    GNActiveParametrizationRepository,
)


def _get_sheet_rows(op_data: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    for sheet in op_data.get("sheets", []):
        if sheet.get("key") == key:
            return sheet.get("rows", [])
    return []


def _gn_catalog(gn: Dict[str, Any], key: str) -> List[str]:
    return [i["name"] for i in gn.get("lv", {}).get("catalogs", {}).get(key, [])]


class CadenaAParametersQueryService:
    """Agrega datos maestros HR/OP/GN en el read model de Cadena A."""

    def __init__(
        self,
        hr_repo: HRActiveParametrizationRepository,
        op_repo: OPActiveParametrizationRepository,
        gn_repo: GNActiveParametrizationRepository,
    ) -> None:
        self._hr = hr_repo
        self._op = op_repo
        self._gn = gn_repo

    def get_active_parameters(self) -> ParametrosCadenaA:
        hr = self._hr.get_active_data()
        op = self._op.get_active_data()
        gn = self._gn.get_active_data()

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


__all__ = ["CadenaAParametersQueryService"]
