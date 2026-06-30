"""Excel-reference validation owned by calculator_motor.

modules/calculator_motor/validation/excel_reference_validator.py

Este validador rechaza cualquier valor que contenga referencias técnicas de
spreadsheets antes de que alcancen el motor de simulación.

El motor opera exclusivamente con valores de negocio normalizados.
Ni coordenadas Excel, ni rangos, ni nombres de hojas deben existir en runtime.
"""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Patrones de referencia Excel que deben ser rechazados
# ---------------------------------------------------------------------------

_EXCEL_PATTERNS = [
    re.compile(r'[A-Z]{1,3}\d+:[A-Z]{1,3}\d+'),       # Rango: C5:C75, A1:B20
    re.compile(r"\bHoja\s*['\"]"),                       # Hoja 'Panel de Control'
    re.compile(r"\bSheet\d+!"),                          # Sheet1!B5
    re.compile(r'[A-Z]{1,3}\d+![A-Z]{1,3}\d+'),        # Cross-sheet: Panel!C5
    re.compile(r'\bF\d{2,3}_[a-z]'),                    # F89_salario, F179_comisiones
    re.compile(r'\b[A-Z]\d{1,3}_[a-z]'),                # D88_opex, J10_tasa
    re.compile(r'vision_tarifas_[a-z]\d+_'),            # vision_tarifas_c43_costo
    re.compile(r'_[a-z]\d+_[a-z]'),                     # _f89_salario, _c43_costo
]


class ExcelReferenceError(ValueError):
    """Se lanza cuando un valor contiene una referencia técnica de Excel."""


def validar_sin_referencias_excel(valor: Any, ruta: str = "") -> None:
    """
    Verifica que `valor` no contenga referencias técnicas de Excel.

    Args:
        valor: El valor a validar (string, dict, list, dataclass, o primitivo).
        ruta:  Ruta semántica del campo (para mensajes de error claros).

    Raises:
        ExcelReferenceError: Si se detecta cualquier patrón de referencia Excel.
    """
    if isinstance(valor, str):
        _validar_string(valor, ruta)
    elif isinstance(valor, dict):
        for k, v in valor.items():
            _validar_string(k, f"{ruta}.{k}[key]")
            validar_sin_referencias_excel(v, f"{ruta}.{k}")
    elif isinstance(valor, (list, tuple)):
        for i, item in enumerate(valor):
            validar_sin_referencias_excel(item, f"{ruta}[{i}]")
    elif is_dataclass(valor) and not isinstance(valor, type):
        for f in fields(valor):
            validar_sin_referencias_excel(getattr(valor, f.name), f"{ruta}.{f.name}")


def _validar_string(s: str, ruta: str) -> None:
    for patron in _EXCEL_PATTERNS:
        if patron.search(s):
            raise ExcelReferenceError(
                f"Referencia Excel detectada en [{ruta}]: {s!r}\n"
                f"  Patrón: {patron.pattern}\n"
                f"  El motor requiere valores de negocio normalizados, "
                f"no referencias a spreadsheets."
            )


def contiene_referencia_excel(valor: Any) -> bool:
    """Retorna True si el valor contiene alguna referencia Excel."""
    try:
        validar_sin_referencias_excel(valor)
        return False
    except ExcelReferenceError:
        return True
