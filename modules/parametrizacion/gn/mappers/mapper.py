"""Maps raw GN Excel sheets to GN domain models."""

from __future__ import annotations

from typing import Any, Dict, List

from nexa_engine.modules.parametrizacion.gn.models.models import GNCatalogSheet, GNMasterData, GNSheet


def _sheet_key(name: str) -> str:
    """Convert 'GN-LV' → 'lv', 'GN-Clientes' → 'clientes'."""
    return name.removeprefix("GN-").lower().replace(" ", "_")


def _str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _extract_catalogs(rows: List[dict]) -> Dict[str, List[Dict[str, str]]]:
    """Extract unique non-empty values per column as {name: ...} lists."""
    if not rows:
        return {}
    seen: dict = {col: {} for col in rows[0].keys()}
    for row in rows:
        for col, val in row.items():
            v = _str(val)
            if v and v not in seen[col]:
                seen[col][v] = {"name": v}
    return {col: list(vals.values()) for col, vals in seen.items() if vals}


class GNMapper:
    """Converts raw sheet dicts to :class:`GNMasterData`."""

    def map(self, version_id: str, sheets: Dict[str, List[dict]]) -> GNMasterData:
        lv_sheet = None
        other_sheets = []

        for name, rows in sheets.items():
            key = _sheet_key(name)
            if name.endswith("-LV"):
                lv_sheet = GNCatalogSheet(
                    name=name,
                    key=key,
                    catalogs=_extract_catalogs(rows),
                )
            else:
                other_sheets.append(GNSheet(name=name, key=key, rows=rows))

        return GNMasterData(version_id=version_id, lv=lv_sheet, sheets=other_sheets)

    def to_dict(self, master: GNMasterData) -> dict:
        result: dict = {}
        if master.lv is not None:
            result[master.lv.key] = {
                "catalogs": {
                    col.lower(): items
                    for col, items in master.lv.catalogs.items()
                }
            }
        for sheet in master.sheets:
            result[sheet.key] = [
                {k.lower(): v for k, v in row.items()}
                for row in sheet.rows
            ]
        result["extra_sheets"] = {}
        return result

