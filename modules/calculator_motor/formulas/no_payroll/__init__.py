"""No-payroll formulas owned by calculator_motor.

This package contains infrastructure, OPEX, and CAPEX calculations used by the
pricing pipeline.
"""

from nexa_engine.modules.calculator_motor.formulas.no_payroll.costs import NoPayrollCalculator

__all__ = ["NoPayrollCalculator"]
