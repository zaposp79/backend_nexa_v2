"""OP Excel value validator.

Structural validation (sheet names, exact headers) is handled upstream in
:func:`read_excel_sheets` when called with :data:`OP_CONTRACT`.  This
validator focuses on *value-level* sanity checks.

ICA guardrails
--------------
For rows where ``ICA == "Tasa"`` (the primary municipal tax rate):

    Valor > MAX_TASA_ICA_DECIMAL  →  **error** (blocks the upload).

    This prevents persisting anomalous values like ``0.6`` (60% ICA) that
    are clearly unit errors in the source Excel.  The backend does NOT
    auto-correct the value; the source file must be fixed and re-uploaded.

For rows where ``ICA != "Tasa"`` (sub-categories such as ``"Bomberos"``,
``"Avisos & Tableros"``, ``"Otras Sobretasas"``):

    Valor > MAX_TASA_ICA_DECIMAL  →  **warning** (non-blocking).

    Sub-category rates may legitimately exceed the main rate threshold.
    A warning is emitted so operators can review, but the upload succeeds.

The threshold is controlled by the ``MAX_TASA_ICA_DECIMAL`` environment
variable (default ``0.05`` = 5 %).  See config.py for details.
"""

from __future__ import annotations

from typing import Dict, List

from nexa_engine.modules.parametrizacion.enums.types import ValidationResult
from nexa_engine.modules.shared.config.config import MAX_TASA_ICA_DECIMAL

MAX_TASA_POLIZA_DECIMAL = 0.10


class OPValidator:
    def validate(self, sheets: Dict[str, List[dict]]) -> ValidationResult:
        result = ValidationResult()

        if not sheets:
            result.errors.append("No se encontraron hojas OP-* en el archivo.")
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

        self._validate_ica_rates(sheets, result)
        self._validate_poliza_rates(sheets, result)

        return result

    def _validate_ica_rates(
        self, sheets: Dict[str, List[dict]], result: ValidationResult
    ) -> None:
        """Validate ICA rates in OP-ICA sheet.

        * ``ICA == "Tasa"`` rows: anomalous value → **error** (blocks upload).
        * Other ICA rows (sub-categories): anomalous value → **warning** only.
        """
        ica_rows = sheets.get("OP-ICA") or []
        threshold = MAX_TASA_ICA_DECIMAL

        for row in ica_rows:
            if not isinstance(row, dict):
                continue
            ica_type_raw = row.get("ica", "")
            ica_type = str(ica_type_raw).strip().lower()
            ciudad = row.get("ciudad", "?")

            try:
                valor = float(row.get("valor") or 0)
            except (TypeError, ValueError):
                continue

            if valor <= threshold:
                continue

            pct_display = f"{valor * 100:.2f}%"
            threshold_pct = f"{threshold * 100:.0f}%"

            if ica_type == "tasa":
                # PRIMARY RATE — block the upload
                result.errors.append(
                    f"INVALID_ICA_RATE | OP-ICA ciudad '{ciudad}': "
                    f"tasa={valor} ({pct_display}) supera el máximo permitido "
                    f"de {threshold_pct}. "
                    f"Corrija el valor en el Excel fuente antes de re-cargar. "
                    f"Valor esperado para tasa municipal: ≤ {threshold} "
                    f"(ejemplo: Bogotá = 0.0097 = 0.97%)."
                )
            else:
                # SUB-CATEGORY (Bomberos, Avisos & Tableros, etc.) — warn only
                result.warnings.append(
                    f"OP-ICA ciudad '{ciudad}' subcategoría '{ica_type_raw}': "
                    f"valor={valor} ({pct_display}) supera {threshold_pct}. "
                    f"Las subcategorías pueden tener tasas más altas; "
                    f"verifique que el valor sea correcto para '{ica_type_raw}'."
                )

    def _validate_poliza_rates(
        self, sheets: Dict[str, List[dict]], result: ValidationResult
    ) -> None:
        poliza_rows = sheets.get("OP-Poliza") or []
        for row in poliza_rows:
            if not isinstance(row, dict):
                continue
            try:
                # Column renamed from 'Valor' to 'Porcentaje' in Excel V2-8
                valor = float(row.get("porcentaje") or row.get("valor") or 0)
            except (TypeError, ValueError):
                continue
            if valor > MAX_TASA_POLIZA_DECIMAL:
                poliza = row.get("poliza", "?")
                result.warnings.append(
                    f"OP-Poliza '{poliza}': tasa={valor} ({valor * 100:.2f}%) "
                    f"supera el máximo razonable de "
                    f"{MAX_TASA_POLIZA_DECIMAL * 100:.0f}%. "
                    f"Verifique que el valor sea decimal (0.0275) "
                    f"y no porcentual (2.75)."
                )
