"""
nexa_engine/shared/precision.py
================================
H-05 — Capa de precisión financiera: rounding compatible con Excel.

Problema
--------
Python usa "banker's rounding" (ROUND_HALF_EVEN) para `round()`, mientras que
Excel usa rounding aritmético simétrico (ROUND_HALF_UP):

    Python: round(2.5)  → 2   (redondea al par más cercano)
    Excel:  ROUND(2.5,0)→ 3   (siempre redondea .5 hacia arriba)

En montos grandes (ej. nóminas de 100M+ COP), esto produce divergencias
acumuladas de hasta ~500 COP por fila. En 12 meses × 20 perfiles = 240 filas,
el error puede superar los 10K COP vs el Excel de referencia.

Solución
--------
`excel_round(value, decimals)` usa `Decimal` con `ROUND_HALF_UP` para replicar
exactamente el comportamiento de ROUND() en Excel.

Uso
---
    from nexa_engine.modules.shared.precision import excel_round, cop_round

    # Redondeo genérico compatible con Excel
    result = excel_round(2356789.456, 0)   # → 2356789.0

    # Redondeo a entero COP (sin decimales) — el más común en nómina
    result = cop_round(2356789.456)         # → 2356789.0

    # Redondear porcentaje a 6 decimales
    pct = excel_round(0.1234567, 6)         # → 0.123457

Cuándo usar
-----------
✅ Valores monetarios que se comparan con el Excel (nómina cargada, tarifas COP)
✅ Factores de indexación acumulados (redondeos de 6 decimales)
✅ Resultados de KPIs que se exponen en la API

❌ Cálculos intermedios puramente internos (usar float nativo por rendimiento)
❌ Porcentajes internos que no se comparan con el Excel
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union

Number = Union[int, float, Decimal]


def excel_round(value: Number, decimals: int = 0) -> float:
    """
    Redondeo aritmético simétrico (ROUND_HALF_UP), compatible con Excel ROUND().

    Args:
        value:    Valor a redondear. Puede ser int, float o Decimal.
        decimals: Número de decimales del resultado (default 0 = entero).

    Returns:
        float con el valor redondeado.

    Examples:
        >>> excel_round(2.5)      # → 3.0   (Python round(2.5) → 2)
        >>> excel_round(3.5)      # → 4.0
        >>> excel_round(-2.5)     # → -3.0  (simétrico: hacia abajo en negativo)
        >>> excel_round(2356789.456, 0)  # → 2356789.0
        >>> excel_round(0.1234567, 6)    # → 0.123457
    """
    try:
        d = Decimal(str(value))
        quantize_str = Decimal("1") if decimals == 0 else Decimal(f"1e-{decimals}")
        return float(d.quantize(quantize_str, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        # Fallback seguro: valor original sin redondear
        return float(value)


def cop_round(value: Number) -> float:
    """
    Redondea al entero COP más cercano (0 decimales) con ROUND_HALF_UP.

    Uso más común: nómina cargada, costos monetarios, tarifas COP.

    Args:
        value: Monto en COP (float o Decimal).

    Returns:
        float sin decimales, redondeado según Excel.

    Examples:
        >>> cop_round(1234567.5)   # → 1234568.0
        >>> cop_round(1234567.4)   # → 1234567.0
    """
    return excel_round(value, 0)


def pct_round(value: Number, decimals: int = 6) -> float:
    """
    Redondea un porcentaje/factor a `decimals` decimales con ROUND_HALF_UP.

    Args:
        value:    Factor o porcentaje (ej. 0.1234567).
        decimals: Decimales de precisión (default 6).

    Returns:
        float redondeado.
    """
    return excel_round(value, decimals)


def nexa_round(value: Number, decimals: int, rounding_mode: str = "excel") -> float:
    """
    Punto de entrada unificado para rounding en el motor NEXA.

    Args:
        value:         Valor a redondear.
        decimals:      Número de decimales.
        rounding_mode: "excel" (ROUND_HALF_UP, default) | "python" (banker's rounding).

    Returns:
        float redondeado.
    """
    if rounding_mode == "excel":
        return excel_round(value, decimals)
    else:
        return round(float(value), decimals)
