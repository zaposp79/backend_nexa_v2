"""Servicio consolidado: obtiene la parametrización activa de HR, GN y OP."""

from __future__ import annotations

from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.op.services.op_service import OPService

_HR_FIELDS = [
    "salariobasico",
    "nomina",
    "recargos",
    "seg_social",
    "prestaciones",
    "ratios",
    "complejidad",
    "rentabilidad",
    "campana",
    "costo_fijo",
    "med_seg",
]


class ActiveParametrizationService:
    """Combina las versiones activas de HR, GN y OP en una sola respuesta."""

    def __init__(
        self,
        hr_service: HRService,
        gn_service: GNService,
        op_service: OPService,
    ) -> None:
        self._hr = hr_service
        self._gn = gn_service
        self._op = op_service

    def get_all_active(self) -> dict:
        hr_active = self._hr.get_active()
        gn_active = self._gn.get_active()
        op_active = self._op.get_active()

        id_hr = hr_active["summary"]["version_id"] if hr_active else None
        id_gn = gn_active["summary"]["version_id"] if gn_active else None
        id_op = op_active["summary"]["version_id"] if op_active else None

        merged_catalogs: dict = {}

        if hr_active:
            hr_lv = hr_active["data"].get("lv", {})
            if isinstance(hr_lv, dict):
                merged_catalogs.update(hr_lv.get("catalogs", {}))

        if gn_active:
            gn_lv = gn_active["data"].get("lv")
            if isinstance(gn_lv, dict):
                merged_catalogs.update(gn_lv.get("catalogs", {}))

        if op_active:
            for sheet in op_active["data"].get("sheets", []):
                if sheet.get("key") == "lv" and "catalogs" in sheet:
                    merged_catalogs.update(sheet.get("catalogs", {}))

        payload: dict = {"lv": {"catalogs": merged_catalogs}}

        hr_data = hr_active["data"] if hr_active else {}
        for field in _HR_FIELDS:
            payload[field] = hr_data.get(field, [])

        if gn_active:
            for sheet in gn_active["data"].get("sheets", []):
                key = sheet.get("key")
                if key and key != "lv":
                    payload[key] = sheet.get("rows", [])

        if op_active:
            for sheet in op_active["data"].get("sheets", []):
                key = sheet.get("key")
                if not key or key == "lv":
                    continue
                if "rows" in sheet:
                    payload[key] = sheet.get("rows", [])

        return {
            "id_hr": id_hr,
            "id_gn": id_gn,
            "id_op": id_op,
            "user_id": None,
            "payload": payload,
        }
