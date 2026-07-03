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

# Claves de estructura interna del payload — no se copian como campos de tabla
_PAYLOAD_STRUCT_KEYS = frozenset({"version_id", "lv", "sheets"})


def _extract_sheets_data(data: dict, payload: dict) -> None:
    """Extrae datos de sheets en formato anidado Y formato plano."""
    # Formato anidado: data["sheets"] = [{"key": "localidad", "rows": [...]}, ...]
    for sheet in data.get("sheets", []):
        key = sheet.get("key")
        if not key or key == "lv":
            continue
        if "rows" in sheet and key not in payload:
            payload[key] = sheet["rows"]

    # Formato plano: data["localidad"] = [...] directamente en el payload
    for key, value in data.items():
        if key not in _PAYLOAD_STRUCT_KEYS and isinstance(value, list) and key not in payload:
            payload[key] = value


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

        # LV catalogs from HR
        if hr_active:
            hr_lv = hr_active["data"].get("lv", {})
            if isinstance(hr_lv, dict):
                merged_catalogs.update(hr_lv.get("catalogs", {}))

        # LV catalogs from GN
        if gn_active:
            gn_lv = gn_active["data"].get("lv")
            if isinstance(gn_lv, dict):
                merged_catalogs.update(gn_lv.get("catalogs", {}))

        # LV catalogs from OP (inside sheets list)
        if op_active:
            op_data = op_active["data"] or {}
            for sheet in op_data.get("sheets", []):
                if sheet.get("key") == "lv" and "catalogs" in sheet:
                    merged_catalogs.update(sheet["catalogs"])
            # Also check flat format: data["lv"]["catalogs"]
            op_lv = op_data.get("lv")
            if isinstance(op_lv, dict):
                merged_catalogs.update(op_lv.get("catalogs", {}))

        payload: dict = {"lv": {"catalogs": merged_catalogs}}

        # HR table fields
        hr_data = hr_active["data"] if hr_active else {}
        for field_name in _HR_FIELDS:
            payload[field_name] = hr_data.get(field_name, [])

        # GN table fields (localidad, etc.) — both nested-sheets and flat formats
        if gn_active:
            _extract_sheets_data(gn_active["data"] or {}, payload)

        # OP table fields (opexfijo, hardsoft, reglanegocio, etc.) — both formats
        if op_active:
            _extract_sheets_data(op_active["data"] or {}, payload)

        return {
            "id_hr": id_hr,
            "id_gn": id_gn,
            "id_op": id_op,
            "user_id": None,
            "payload": payload,
        }
