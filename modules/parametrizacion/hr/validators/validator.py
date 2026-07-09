"""HR Excel value validator.

Structural validation (sheet names, exact headers) is handled upstream in
:func:`read_excel_sheets` when called with :data:`HR_CONTRACT`.  This
validator focuses on *value-level* checks after the data has been parsed and
normalised.

Fuzzy matching has been removed.  Column names are validated exactly (after
normalisation) by the reader layer.  If a column is missing here it is a
genuine data problem, not a naming variant.
"""

from __future__ import annotations

from typing import Dict, List

from nexa_engine.modules.parametrizacion.enums.types import ValidationResult

# Canonical required sheet names — imported by the service to compute
# ``sheets_missing`` without duplicating the list.
REQUIRED_SHEETS = [
    "HR-LV",
    "HR-SalarioBasico",
    "HR-Nomina",
    "HR-Recargos",
    "HR-SegSocial",
    "HR-Prestaciones",
    "HR-Ratios",
    "HR-Complejidad",
    "HR-Rentabilidad",
    "HR-Campana",
    "HR-CostoFijo",
    "HR-Med-Seg",
    "HR-Ratios-HITL",
    "HR-Hora-GTR",
]

OPTIONAL_SHEETS = [
    "HR-AutRot",
    "HR-EquipoHITL",
    "HR-EquipoSoporteMantenimiento",
]

# Normalised column names expected in each sheet (post-_normalize_column).
# Used for value-level checks only — existence is guaranteed by the reader
# contract layer.
_NUMERIC_FIELDS: Dict[str, List[str]] = {
    "HR-SalarioBasico": ["valor"],
    "HR-Nomina": ["salario"],
    "HR-Recargos": ["valor"],
    "HR-SegSocial": ["proporcion"],
    "HR-Prestaciones": ["valor"],
    "HR-Ratios": ["agentes"],
    "HR-Complejidad": ["valor"],
    "HR-Campana": ["mes", "valor"],
    "HR-AutRot": ["mes", "valor"],
    "HR-CostoFijo": ["valor"],
    "HR-Med-Seg": ["valor"],
    "HR-Ratios-HITL": ["ratio"],
    "HR-Hora-GTR": ["hora"],
}


class HRValidator:
    """Validates value-level content of an HR Excel upload."""

    def validate(self, sheets: Dict[str, List[dict]]) -> ValidationResult:
        result = ValidationResult()

        found_optional = [s for s in OPTIONAL_SHEETS if s in sheets]
        if found_optional:
            result.warnings.append(
                f"Hojas opcionales presentes y cargadas: {found_optional}"
            )

        for sheet_name, rows in sheets.items():
            if not rows:
                result.warnings.append(
                    f"La hoja '{sheet_name}' no contiene filas de datos."
                )
                continue

            numeric_cols = _NUMERIC_FIELDS.get(sheet_name, [])
            actual_columns = set(rows[0].keys())

            for num_col in numeric_cols:
                if num_col not in actual_columns:
                    continue
                for i, row in enumerate(rows, start=2):
                    val = row.get(num_col)
                    if val is None or str(val).strip() == "":
                        result.warnings.append(
                            f"Hoja '{sheet_name}', fila {i}: "
                            f"columna '{num_col}' está vacía."
                        )
                    elif not isinstance(val, (int, float)):
                        result.errors.append(
                            f"INVALID_EXCEL_VALUE | hoja '{sheet_name}', fila {i}, "
                            f"columna '{num_col}': se esperaba un número, "
                            f"se recibió '{val}'."
                        )

        return result
