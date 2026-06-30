"""OP domain models (dynamic schema)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OPCatalogSheet:
    """A OP-LV sheet stored as unique-value catalogs per column."""
    name: str
    key: str
    catalogs: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


@dataclass
class OPSheet:
    name: str
    key: str
    rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class OPMasterData:
    version_id: str
    sheets: List[OPSheet] = field(default_factory=list)

    def get_sheet(self, key: str) -> Optional[Any]:
        for sheet in self.sheets:
            if sheet.key == key:
                return sheet
        return None
