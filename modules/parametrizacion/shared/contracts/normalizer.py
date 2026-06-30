"""Contract-based value normalizer for Excel uploads.

Replaces the heuristic :func:`normalize_all_sheets_values` call in services.
Each cell is converted according to the :class:`ColumnType` declared in the
module's :class:`ModuleContract`, not by guessing the type from the raw value.

Conversion rules by type
-------------------------
``string / catalog / raw_text``
    ``str(val).strip()``; preserve accents, internal spaces, embedded ``%``.
    ``"70% SMMLV - 30% IPC"`` → ``"70% SMMLV - 30% IPC"`` (not converted).

``percentage_decimal``
    If string ends with ``%``:  ``float(raw) / 100``  (``"17.00%"`` → ``0.17``).
    Otherwise: parse as float  (``"0.085"`` → ``0.085``, ``0.7`` → ``0.7``).

``decimal / factor``
    Parse as float.  No division regardless of ``%``.

``money / number``
    Parse as float.  No rounding, no division.

``int``
    Parse as ``int``.  Whole-number floats accepted (``"2026.0"`` → ``2026``).
    Non-integer decimals raise :class:`~shared.exceptions.ValidationError`.

``raw_value``
    Return the openpyxl cell value unchanged.

Columns not present in the contract fall back to generic numeric/string
detection (same as the old heuristic normalizer) so that ``extra_sheets``
and dynamically discovered catalog columns are still handled correctly.

Security
--------
Regardless of type, string values starting with ``=`` or ``@`` are rejected
with a :class:`~shared.exceptions.ValidationError` (formula / injection
prevention — defence-in-depth over the OOXML preflight).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.shared.contracts.base import (
    ColumnType,
    ModuleContract,
)
from nexa_engine.modules.shared.exceptions import ValidationError

# Injection-prefix check (defence-in-depth on top of OOXML preflight)
_INJECTION_PREFIXES = ("=", "@")

# Numeric RE used for generic fallback columns
_NUMERIC_RE = re.compile(r"^[+-]?(\d+([\.,]\d+)?|\d*[\.,]\d+)$")


class ContractValueNormalizer:
    """Normalizes cell values according to declared column types.

    Parameters
    ----------
    contract:
        The module contract that defines column types.  When a cell's column
        key is not found in the contract, generic heuristic fallback applies.
    """

    def __init__(self, contract: ModuleContract) -> None:
        # Pre-build {sheet_name: {normalized_key: ColumnType}} for fast lookup
        self._type_map: Dict[str, Dict[str, ColumnType]] = {}
        from nexa_engine.modules.parametrizacion.shared.helpers.excel_reader import (
            _normalize_column,
        )
        for sheet in contract.sheets:
            self._type_map[sheet.excel_name] = {
                _normalize_column(column.excel_header): column.col_type
                for column in sheet.columns
            }

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def normalize_sheets(
        self,
        sheets: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Normalize every cell in *sheets* using the module contract.

        Args:
            sheets: ``{sheet_name: [row_dicts]}`` with normalised column keys.

        Returns:
            New dict with the same structure but typed cell values.

        Raises:
            :class:`~shared.exceptions.ValidationError`:
                On injection attempt or int/percentage parse failure.
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        for sheet_name, rows in sheets.items():
            col_types = self._type_map.get(sheet_name, {})
            result[sheet_name] = [
                self._normalize_row(sheet_name, row_idx, row, col_types)
                for row_idx, row in enumerate(rows, start=2)
            ]
        return result

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _normalize_row(
        self,
        sheet_name: str,
        row_idx: int,
        row: Dict[str, Any],
        col_types: Dict[str, ColumnType],
    ) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for col_key, val in row.items():
            col_type = col_types.get(col_key)
            normalized[col_key] = self._normalize_cell(
                val, col_type, sheet_name, row_idx, col_key
            )
        return normalized

    def _normalize_cell(
        self,
        val: Any,
        col_type: Optional[ColumnType],
        sheet_name: str,
        row_idx: int,
        col_key: str,
    ) -> Any:
        if val is None:
            return None

        # Security: formula/injection prefix check (strings only)
        if isinstance(val, str):
            stripped = val.strip()
            if stripped.startswith(_INJECTION_PREFIXES):
                raise ValidationError(
                    f"Valor potencialmente inseguro en '{sheet_name}' "
                    f"fila {row_idx} col '{col_key}': '{stripped[:30]}'.",
                    errors=[
                        f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {row_idx}, "
                        f"col '{col_key}': valor no permitido (inicia con '=' o '@')."
                    ],
                )

        # Dispatch to type handler
        if col_type is None:
            return self._fallback(val)

        if col_type in (ColumnType.STRING, ColumnType.CATALOG, ColumnType.RAW_TEXT):
            return self._as_string(val)

        if col_type == ColumnType.PERCENTAGE_DECIMAL:
            return self._as_percentage_decimal(val, sheet_name, row_idx, col_key)

        if col_type in (ColumnType.DECIMAL, ColumnType.FACTOR):
            return self._as_float(val, sheet_name, row_idx, col_key)

        if col_type in (ColumnType.MONEY, ColumnType.NUMBER):
            return self._as_float(val, sheet_name, row_idx, col_key)

        if col_type == ColumnType.INT:
            return self._as_int(val, sheet_name, row_idx, col_key)

        # raw_value or unknown
        return val

    # ------------------------------------------------------------------
    # Type converters
    # ------------------------------------------------------------------

    @staticmethod
    def _as_string(val: Any) -> Optional[str]:
        """Trim and convert to str; return None for empty."""
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    @staticmethod
    def _as_percentage_decimal(
        val: Any,
        sheet_name: str,
        row_idx: int,
        col_key: str,
    ) -> Optional[float]:
        """Convert to decimal fraction.

        ``"17.00%"`` → ``0.17``
        ``"0.17"``    → ``0.17``
        ``0.17``      → ``0.17``
        """
        if val is None:
            return None
        if isinstance(val, bool):
            return float(val)
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            text = val.strip()
            if not text:
                return None
            if text.endswith("%"):
                # Pure percentage string: "17.00%" → 0.17
                raw = text[:-1].strip()
                raw = raw.replace(",", ".")
                try:
                    return float(Decimal(raw)) / 100.0
                except (InvalidOperation, ValueError):
                    raise ValidationError(
                        f"No se puede convertir '{text}' a porcentaje decimal "
                        f"en '{sheet_name}' fila {row_idx} col '{col_key}'.",
                        errors=[
                            f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {row_idx}, "
                            f"col '{col_key}': '{text}' no es un porcentaje válido."
                        ],
                    )
            # Plain decimal string
            return ContractValueNormalizer._parse_numeric_str(
                text, sheet_name, row_idx, col_key
            )
        raise ValidationError(
            f"Tipo inesperado {type(val).__name__!r} en '{sheet_name}' "
            f"fila {row_idx} col '{col_key}'.",
        )

    @staticmethod
    def _as_float(
        val: Any,
        sheet_name: str,
        row_idx: int,
        col_key: str,
    ) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, bool):
            return float(val)
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            text = val.strip()
            if not text:
                return None
            return ContractValueNormalizer._parse_numeric_str(
                text, sheet_name, row_idx, col_key
            )
        raise ValidationError(
            f"No se puede convertir '{val!r}' a número en "
            f"'{sheet_name}' fila {row_idx} col '{col_key}'.",
        )

    @staticmethod
    def _as_int(
        val: Any,
        sheet_name: str,
        row_idx: int,
        col_key: str,
    ) -> Optional[int]:
        if val is None:
            return None
        if isinstance(val, bool):
            return int(val)
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            if val != int(val):
                raise ValidationError(
                    f"El valor {val} no es un entero válido en "
                    f"'{sheet_name}' fila {row_idx} col '{col_key}'.",
                    errors=[
                        f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {row_idx}, "
                        f"col '{col_key}': {val} no es entero."
                    ],
                )
            return int(val)
        if isinstance(val, str):
            text = val.strip()
            if not text:
                return None
            try:
                f = float(text.replace(",", "."))
                if f != int(f):
                    raise ValidationError(
                        f"El valor '{text}' no es un entero en "
                        f"'{sheet_name}' fila {row_idx} col '{col_key}'.",
                        errors=[
                            f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {row_idx}, "
                            f"col '{col_key}': '{text}' no es entero."
                        ],
                    )
                return int(f)
            except (ValueError, TypeError):
                raise ValidationError(
                    f"No se puede convertir '{text}' a entero en "
                    f"'{sheet_name}' fila {row_idx} col '{col_key}'.",
                )
        raise ValidationError(
            f"Tipo inesperado para int: {type(val).__name__!r} en "
            f"'{sheet_name}' fila {row_idx} col '{col_key}'.",
        )

    @staticmethod
    def _parse_numeric_str(
        text: str,
        sheet_name: str,
        row_idx: int,
        col_key: str,
    ) -> float:
        """Parse a numeric string handling both decimal separators."""
        raw = text.replace(" ", "")
        if raw.count(",") and raw.count("."):
            last_comma = raw.rfind(",")
            last_dot = raw.rfind(".")
            if last_comma > last_dot:
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif raw.count(","):
            raw = raw.replace(",", ".")
        try:
            return float(Decimal(raw))
        except (InvalidOperation, ValueError):
            raise ValidationError(
                f"No se puede convertir '{text}' a número en "
                f"'{sheet_name}' fila {row_idx} col '{col_key}'.",
                errors=[
                    f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {row_idx}, "
                    f"col '{col_key}': '{text}' no es un número válido."
                ],
            )

    @staticmethod
    def _fallback(val: Any) -> Any:
        """Heuristic fallback for columns not in the contract (extra_sheets, dynamic catalogs)."""
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            # Try numeric (without % stripping — preserve "17.00%" as string in fallback)
            if _NUMERIC_RE.match(s):
                try:
                    return float(Decimal(s.replace(",", ".")))
                except (InvalidOperation, ValueError):
                    pass
            return s
        return val


def normalize_sheets_by_contract(
    sheets: Dict[str, List[Dict[str, Any]]],
    contract: ModuleContract,
) -> Dict[str, List[Dict[str, Any]]]:
    """Convenience wrapper: normalize *sheets* using *contract*."""
    return ContractValueNormalizer(contract).normalize_sheets(sheets)
