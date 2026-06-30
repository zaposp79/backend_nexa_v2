"""Centralized value normalization for Excel-derived data.

Changes from previous version
------------------------------
* Boolean coercion from strings (``si/no``, ``y/n``, ``true/false``) is
  **disabled by default**.  Applying it globally corrupted catalog values whose
  text happened to be one of those words.  Downstream mappers that need boolean
  coercion must do it explicitly per column.

* String values that start with ``=`` or ``@`` are rejected with
  ``ValidationError`` (formula / CSV injection prevention).  This is a
  defence-in-depth measure; the primary formula check is the OOXML preflight
  that scans sheet XML for ``<f>`` elements.  Values starting with ``-`` or
  ``+`` are NOT rejected because they can represent legitimate negative / signed
  numeric strings.

* Percentage stripping (``%``) is retained from the previous implementation to
  avoid breaking existing downstream logic, but is now logged as a warning so
  the transformation is auditable.  Callers that need to preserve the ``%``
  should pass the raw value directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any, Dict, List, Optional

from nexa_engine.modules.shared.exceptions import ValidationError


_NUMERIC_RE = re.compile(r"^[+-]?(\d+([\.,]\d+)?|\d*[\.,]\d+)$")

# String prefixes that indicate formula / injection attempt in a text cell.
_INJECTION_PREFIXES = ("=", "@")


@dataclass
class NormalizedValue:
    value: Any
    detected_type: str


class ValueNormalizer:
    """Normalize values and log detailed transformations."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger("nexa.value_normalizer")

    def normalize_sheets(
        self, sheets: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        normalized: Dict[str, List[Dict[str, Any]]] = {}
        for sheet_name, rows in sheets.items():
            normalized[sheet_name] = self._normalize_rows(sheet_name, rows)
        return normalized

    def _normalize_rows(
        self, sheet_name: str, rows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        column_types: Dict[str, str] = {}

        for idx, row in enumerate(rows, start=2):
            normalized_row: Dict[str, Any] = {}

            if sheet_name == "HR-CostoFijo" and idx <= 3:
                self._logger.warning(
                    "[NORMALIZER] HR-CostoFijo row %d BEFORE: localidad=%r valor=%r",
                    idx,
                    row.get("localidad"),
                    row.get("valor"),
                )

            for col, val in row.items():
                normalized = self._normalize_value(sheet_name, idx, col, val)
                normalized_row[col] = normalized.value

                prev_type = column_types.get(col)
                if normalized.detected_type not in ("null", "empty"):
                    if prev_type is None:
                        column_types[col] = normalized.detected_type
                    elif prev_type != normalized.detected_type:
                        self._logger.warning(
                            "Type mismatch | sheet=%s row=%s col=%s prev=%s now=%s",
                            sheet_name,
                            idx,
                            col,
                            prev_type,
                            normalized.detected_type,
                        )

            if sheet_name == "HR-CostoFijo" and idx <= 3:
                self._logger.warning(
                    "[NORMALIZER] HR-CostoFijo row %d AFTER: localidad=%r valor=%r",
                    idx,
                    normalized_row.get("localidad"),
                    normalized_row.get("valor"),
                )

            result.append(normalized_row)
        return result

    def _normalize_value(
        self, sheet_name: str, row: int, col: str, val: Any
    ) -> NormalizedValue:
        if val is None:
            self._log(sheet_name, row, col, val, None, "null")
            return NormalizedValue(None, "null")

        if isinstance(val, bool):
            self._log(sheet_name, row, col, val, val, "bool")
            return NormalizedValue(val, "bool")

        if isinstance(val, (int, float)):
            num = float(val)
            self._log(sheet_name, row, col, val, num, "number")
            return NormalizedValue(num, "number")

        if isinstance(val, str):
            stripped = val.strip()
            if stripped == "":
                self._log(sheet_name, row, col, val, None, "empty")
                return NormalizedValue(None, "empty")

            # Formula / injection detection — reject = and @ prefixes.
            # Note: the OOXML preflight already blocks <f> elements in sheet XML.
            # This catches the rare case of a string cell whose value starts with
            # an injection prefix (e.g. stored as explicit string type in the XML).
            if stripped.startswith(_INJECTION_PREFIXES):
                raise ValidationError(
                    f"El archivo contiene un valor potencialmente inseguro en la hoja "
                    f"'{sheet_name}', fila {row}, columna '{col}': "
                    f"'{stripped[:20]}...' — los valores no pueden iniciar con '=' o '@'.",
                    errors=[
                        f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {row}, "
                        f"columna '{col}': valor '{stripped[:40]}' no permitido."
                    ],
                )

            # Try numeric conversion
            num = self._parse_numeric(stripped)
            if num is not None:
                self._log(sheet_name, row, col, val, num, "number")
                return NormalizedValue(num, "number")

            # Plain string — keep as-is (no boolean coercion)
            self._log(sheet_name, row, col, val, stripped, "string")
            return NormalizedValue(stripped, "string")

        self._log(sheet_name, row, col, val, val, type(val).__name__)
        return NormalizedValue(val, type(val).__name__)

    def _parse_numeric(self, text: str) -> Optional[float]:
        raw = text.replace(" ", "")
        has_percent = "%" in raw
        raw = raw.replace("%", "")

        if raw.count(",") and raw.count("."):
            last_comma = raw.rfind(",")
            last_dot = raw.rfind(".")
            if last_comma > last_dot:
                raw = raw.replace(".", "")
                raw = raw.replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif raw.count(","):
            raw = raw.replace(",", ".")

        if not _NUMERIC_RE.match(raw):
            return None

        try:
            result = float(Decimal(raw))
        except (InvalidOperation, ValueError):
            return None

        if has_percent:
            self._logger.warning(
                "Percent-stripping applied | original=%r numeric=%s "
                "(value stored as-is, not divided by 100)",
                text,
                result,
            )
        return result

    def _log(
        self,
        sheet: str,
        row: int,
        col: str,
        original: Any,
        transformed: Any,
        detected_type: str,
    ) -> None:
        self._logger.debug(
            "Normalize | sheet=%s row=%s col=%s type=%s original=%r transformed=%r",
            sheet,
            row,
            col,
            detected_type,
            original,
            transformed,
        )


def normalize_all_sheets_values(
    sheets: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Convenience wrapper for default normalization."""
    return ValueNormalizer().normalize_sheets(sheets)
