"""GN domain models (dynamic schema)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GNCatalogSheet:
    """A GN-*LV sheet stored as unique-value catalogs per column."""
    name: str
    key: str
    catalogs: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


@dataclass
class GNSheet:
    """A single GN-* sheet with its raw rows (non-LV sheets)."""
    name: str
    key: str
    rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GNMasterData:
    """Full GN master data for one uploaded version."""
    version_id: str
    lv: Optional[GNCatalogSheet] = None
    sheets: List[GNSheet] = field(default_factory=list)

    def get_sheet(self, key: str) -> Optional[GNSheet]:
        for sheet in self.sheets:
            if sheet.key == key:
                return sheet
        return None
