"""Cadena C — Parameters Query Service.

Ensambla el read model ParametrosCadenaC a partir de los repositorios OP y HR.
Propietario: modules/cadena_c. Contrato independiente de Cadena B.

Consulta parametrización a través de los repositorios tipados de cada dominio.
"""
from __future__ import annotations

from nexa_engine.modules.cadena_c.dto.cadena_c_dto import (
    DispositivoRequerido,
    EquipoHITL,
    ParametrosCadenaC,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
    HRActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)


class CadenaCParametersQueryService:
    """Agrega datos maestros OP/HR en el read model de Cadena C."""

    def __init__(
        self,
        hr_repo: HRActiveParametrizationRepository,
        op_repo: OPActiveParametrizationRepository,
    ) -> None:
        self._hr = hr_repo
        self._op = op_repo

    def get_active_parameters(self) -> ParametrosCadenaC:
        op = self._op.get_active_data()
        hr = self._hr.get_active_data()

        dispositivos: list[DispositivoRequerido] = []
        for sheet in op.get("sheets", []):
            if sheet.get("key") == "dispositivorequerido":
                catalogs = sheet.get("catalogs", {}).get("dispositivorequerido", [])
                dispositivos = [DispositivoRequerido(nombre=c["name"]) for c in catalogs]
                break

        hitl_rows = hr.get("extra_sheets", {}).get("HR-EquipoHITL", [])
        equipo_hitl = [
            EquipoHITL(nombre=r["equipohitl"], ratio=r.get("ratio"))
            for r in hitl_rows
        ]

        return ParametrosCadenaC(
            dispositivos_requeridos=dispositivos,
            equipo_hitl=equipo_hitl,
        )


__all__ = ["CadenaCParametersQueryService"]
