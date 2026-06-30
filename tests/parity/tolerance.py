"""Tolerance helpers for paridad ≤ 0.01% (1e-4 relative)."""
from __future__ import annotations

import math

REL_TOL = 1e-4   # 0.01 %
ABS_TOL = 1e-2   # 1 cent COP


def assert_close(actual: float, expected: float, *, rel_tol: float = REL_TOL,
                 abs_tol: float = ABS_TOL, label: str = "") -> None:
    """Assert two floats are close within `rel_tol` relative or `abs_tol` absolute.

    Raises AssertionError with a diagnostic message including the relative delta.
    """
    if actual is None or expected is None:
        raise AssertionError(f"{label}: None value (actual={actual}, expected={expected})")
    if math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol):
        return
    if expected == 0:
        delta = abs(actual)
        raise AssertionError(
            f"{label}: expected 0.0 but got {actual} (abs_delta={delta} > {abs_tol})")
    rel = abs(actual - expected) / abs(expected)
    raise AssertionError(
        f"{label}: expected={expected:,.4f}, actual={actual:,.4f}, "
        f"rel_delta={rel*100:.6f}% (> {rel_tol*100:.4f}%)")


def factor_billing(margen: float, op_cont: float = 0.0, com_cont: float = 0.0,
                    markup: float = 0.0, descuento: float = 0.0) -> float:
    """Denominador exacto del pricing WAVE 3.

    ingreso = costo / factor_billing(margen, ...)
    """
    return (1 - margen) * (1 - op_cont) * (1 - com_cont) * (1 - markup) * (1 + descuento)


def expected_ingreso(costo: float, margen: float, op_cont: float = 0.0,
                     com_cont: float = 0.0, markup: float = 0.0,
                     descuento: float = 0.0) -> float:
    fb = factor_billing(margen, op_cont, com_cont, markup, descuento)
    return costo / fb if fb else 0.0
