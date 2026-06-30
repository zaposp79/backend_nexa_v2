"""GN Excel value validator.

Structural validation (sheet names, headers) is handled upstream in
:func:`read_excel_sheets` when called with the GN contract.  This validator
focuses on *value-level* checks on the already-parsed, normalised rows.
"""

from __future__ import annotations

from typing import Dict, List

from nexa_engine.modules.parametrizacion.enums.types import ValidationResult


class GNValidator:
    """Validates value-level content of a GN Excel upload."""

    def validate(self, sheets: Dict[str, List[dict]]) -> ValidationResult:
        """Validate GN sheet contents.

        Args:
            sheets: ``{sheet_name: [row_dicts]}`` with normalised column keys.

        Returns:
            :class:`ValidationResult`.
        """
        result = ValidationResult()

        if not sheets:
            result.errors.append("No se encontraron hojas GN-* en el archivo.")
            return result

        for sheet_name, rows in sheets.items():
            if not rows:
                result.errors.append(
                    f"La hoja '{sheet_name}' no contiene filas de datos."
                )
                continue
            if all(all(v is None for v in row.values()) for row in rows):
                result.errors.append(
                    f"La hoja '{sheet_name}' solo contiene celdas vacías."
                )

        return result
