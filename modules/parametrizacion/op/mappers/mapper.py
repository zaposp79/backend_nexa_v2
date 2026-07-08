"""Maps raw OP Excel sheets to OP domain models."""

from __future__ import annotations
from typing import Any, Dict, List
from ..models.models import OPCatalogSheet, OPMasterData, OPSheet
from ..contracts import OP_CONTRACT
from nexa_engine.modules.parametrizacion.shared.contracts.base import SheetType


def _sheet_key(name: str) -> str:
    return name.removeprefix("OP-").lower().replace(" ", "_")


def _coerce_catalog_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, str):
        stripped = val.strip()
        return stripped if stripped != "" else None
    return val


def _extract_catalogs(rows: List[dict]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract unique non-empty values per column as {name: ...} lists."""
    if not rows:
        return {}
    seen: dict = {col: {} for col in rows[0].keys()}
    for row in rows:
        for col, val in row.items():
            v = _coerce_catalog_value(val)
            if v is None:
                continue
            key = (type(v).__name__, v)
            if key not in seen[col]:
                seen[col][key] = {"name": v}
    return {col: list(vals.values()) for col, vals in seen.items() if vals}


def _is_catalog_sheet(rows: List[dict]) -> bool:
    if not rows:
        return False
    for row in rows:
        for val in row.values():
            if val is None:
                continue
            if isinstance(val, (int, float, bool)):
                return False
    return True


class OPMapper:
    def map(self, version_id: str, sheets: Dict[str, List[dict]]) -> OPMasterData:
        all_sheets: List[OPSheet] = []

        for name, rows in sheets.items():
            key = _sheet_key(name)

            # Determine sheet type from contract, fall back to heuristic
            sheet_contract = next((s for s in OP_CONTRACT.sheets if s.excel_name == name), None)
            is_catalog_by_contract = (
                sheet_contract and sheet_contract.sheet_type == SheetType.CATALOG_BY_COLUMN
            )
            is_catalog = is_catalog_by_contract or (
                sheet_contract is None and _is_catalog_sheet(rows)
            )

            if is_catalog:
                all_sheets.append(OPCatalogSheet(
                    name=name,
                    key=key,
                    catalogs=_extract_catalogs(rows),
                ))
            else:
                all_sheets.append(OPSheet(name=name, key=key, rows=rows))

        return OPMasterData(version_id=version_id, sheets=all_sheets)

    def to_dict(self, master: OPMasterData) -> dict:
        result: dict = {}
        for sheet in master.sheets:
            if isinstance(sheet, OPCatalogSheet):
                result[sheet.key] = {
                    "catalogs": {
                        col.lower(): items
                        for col, items in sheet.catalogs.items()
                    }
                }
            else:
                result[sheet.key] = [
                    {k.lower(): v for k, v in row.items()}
                    for row in sheet.rows
                ]
        result["extra_sheets"] = {}
        return result

