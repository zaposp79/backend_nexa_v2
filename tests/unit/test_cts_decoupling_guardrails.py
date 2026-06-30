"""Guardrails: CostToServeCalculator no debe depender de calculadoras core.

Verifica que:
1. El constructor de CostToServeCalculator no acepta calc_nomina, calc_no_payroll ni calc_cadena_b.
2. CostToServeCalculator no llama calcular_para_mes() internamente.
3. El módulo vision_cost_to_serve no importa NominaCalculator ni NoPayrollCalculator.
"""
import ast
import inspect
import textwrap
from pathlib import Path

import pytest

VISION_ROOT = Path(__file__).parents[2] / "modules" / "vision_cost_to_serve"
CTS_CALC_FILE = (
    Path(__file__).parents[2]
    / "modules"
    / "calculator_motor"
    / "formulas"
    / "cts"
    / "calculator.py"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestCostToServeCalculatorNoCoreDependencies:
    _CTC_CANONICAL = "nexa_engine.modules.calculator_motor.formulas.cts.calculator"

    def test_constructor_has_no_calc_nomina_param(self) -> None:
        import importlib
        ctc = importlib.import_module(self._CTC_CANONICAL)
        sig = inspect.signature(ctc.CostToServeCalculator.__init__)
        assert "calc_nomina" not in sig.parameters, (
            "CostToServeCalculator.__init__ no debe aceptar calc_nomina. "
            "Usar CostToServeFacts en su lugar."
        )

    def test_constructor_has_no_calc_no_payroll_param(self) -> None:
        import importlib
        ctc = importlib.import_module(self._CTC_CANONICAL)
        sig = inspect.signature(ctc.CostToServeCalculator.__init__)
        assert "calc_no_payroll" not in sig.parameters, (
            "CostToServeCalculator.__init__ no debe aceptar calc_no_payroll. "
            "Usar CostToServeFacts en su lugar."
        )

    def test_constructor_has_no_calc_cadena_b_param(self) -> None:
        import importlib
        ctc = importlib.import_module(self._CTC_CANONICAL)
        sig = inspect.signature(ctc.CostToServeCalculator.__init__)
        assert "calc_cadena_b" not in sig.parameters, (
            "CostToServeCalculator.__init__ no debe aceptar calc_cadena_b. "
            "Usar CostToServeFacts en su lugar."
        )

    def test_source_does_not_call_calcular_para_mes(self) -> None:
        source = _source(CTS_CALC_FILE)
        assert "calcular_para_mes" not in source, (
            "cost_to_serve_calculator.py no debe llamar calcular_para_mes(). "
            "Los facts deben ser pre-computados por el engine."
        )

    def test_module_does_not_import_nomina_calculator(self) -> None:
        """Ningún archivo en vision_cost_to_serve debe importar NominaCalculator directamente."""
        for py_file in VISION_ROOT.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            assert "NominaCalculator" not in source, (
                f"{py_file.relative_to(VISION_ROOT)} importa NominaCalculator. "
                "vision_cost_to_serve no debe depender de calculadoras core."
            )

    def test_module_does_not_import_no_payroll_calculator(self) -> None:
        """Ningún archivo en vision_cost_to_serve debe importar NoPayrollCalculator directamente."""
        for py_file in VISION_ROOT.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            assert "NoPayrollCalculator" not in source, (
                f"{py_file.relative_to(VISION_ROOT)} importa NoPayrollCalculator. "
                "vision_cost_to_serve no debe depender de calculadoras core."
            )

    _CTS_FACTS_CANONICAL = "nexa_engine.modules.calculator_motor.formulas.cts.cts_facts"

    def test_cts_facts_model_exists(self) -> None:
        import importlib
        facts = importlib.import_module(self._CTS_FACTS_CANONICAL)
        assert facts.CostToServeFacts is not None
        assert facts.CanalCTSFacts is not None

    def test_cts_facts_has_expected_fields(self) -> None:
        import dataclasses
        import importlib
        facts = importlib.import_module(self._CTS_FACTS_CANONICAL)
        field_names = {f.name for f in dataclasses.fields(facts.CostToServeFacts)}
        assert "nomina_por_mes" in field_names
        assert "no_payroll_por_mes" in field_names
        assert "cadena_b_por_mes" in field_names
        assert "canales" in field_names
