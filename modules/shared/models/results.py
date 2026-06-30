"""
backward-compat adapter — canonical: modules/calculator_motor/models/results.py

Ownership inversion (2026-06-10): class definitions moved to calculator_motor/models/.
This file re-exports all symbols for legacy consumers.

⚠️  STABILITY CONTRACT preserved — same classes, same identity.
"""
from nexa_engine.modules.calculator_motor.models.results import (  # noqa: F401
    ResultadoNomina,
    ResultadoNoPayroll,
    ResultadoCadenaB,
    ResultadoCadenaC,
    CostosTotalesMes,
    CostosFinancierosMes,
    PyGMensual,
    KPIsDeal,
    PricingResult,
)

__all__ = [
    "ResultadoNomina", "ResultadoNoPayroll", "ResultadoCadenaB", "ResultadoCadenaC",
    "CostosTotalesMes", "CostosFinancierosMes", "PyGMensual", "KPIsDeal", "PricingResult",
]
