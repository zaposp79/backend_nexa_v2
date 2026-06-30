"""Guardrails: VisionTarifasCalculator no debe depender de calculadoras core.

Verifica que:
1. El constructor de VisionTarifasCalculator no acepta calc_nomina ni calc_no_payroll.
2. Ningún archivo en modules/vision_tarifas/ llama calcular_para_mes().
3. El módulo vision_tarifas no importa NominaCalculator ni NoPayrollCalculator directamente.
4. El modelo VisionTarifasFacts existe con los campos esperados.
"""
import dataclasses
import inspect
from pathlib import Path

MODULE_ROOT = Path(__file__).parents[2] / "modules" / "vision_tarifas"
MOTOR_TARIFF_ROOT = Path(__file__).parents[2] / "modules" / "calculator_motor" / "formulas" / "tarifas"
VT_INIT_FILE = MODULE_ROOT / "__init__.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestVisionTarifasCalculatorNoCoreDependencies:
    def test_constructor_has_no_calc_nomina_param(self) -> None:
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator

        sig = inspect.signature(VisionTarifasCalculator.__init__)
        assert "calc_nomina" not in sig.parameters, (
            "VisionTarifasCalculator.__init__ no debe aceptar calc_nomina. "
            "Usar VisionTarifasFacts en su lugar."
        )

    def test_constructor_has_no_calc_no_payroll_param(self) -> None:
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator

        sig = inspect.signature(VisionTarifasCalculator.__init__)
        assert "calc_no_payroll" not in sig.parameters, (
            "VisionTarifasCalculator.__init__ no debe aceptar calc_no_payroll. "
            "Usar VisionTarifasFacts en su lugar."
        )

    def test_source_does_not_call_calcular_para_mes(self) -> None:
        for py_file in MODULE_ROOT.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            assert "calcular_para_mes" not in source, (
                f"{py_file.relative_to(MODULE_ROOT)} llama calcular_para_mes(). "
                "Los facts deben ser pre-computados por el engine."
            )

    def test_module_does_not_import_nomina_calculator(self) -> None:
        """Ningún archivo en vision_tarifas debe importar NominaCalculator directamente."""
        for py_file in MODULE_ROOT.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            assert "NominaCalculator" not in source, (
                f"{py_file.relative_to(MODULE_ROOT)} importa NominaCalculator. "
                "vision_tarifas no debe depender de calculadoras core."
            )

    def test_module_does_not_import_no_payroll_calculator(self) -> None:
        """Ningún archivo en vision_tarifas debe importar NoPayrollCalculator directamente."""
        for py_file in MODULE_ROOT.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            assert "NoPayrollCalculator" not in source, (
                f"{py_file.relative_to(MODULE_ROOT)} importa NoPayrollCalculator. "
                "vision_tarifas no debe depender de calculadoras core."
            )

    def test_vt_facts_model_exists(self) -> None:
        from nexa_engine.modules.vision_tarifas.models.vt_facts import (
            EscenarioCanalFacts,
            VisionTarifasFacts,
        )

        assert VisionTarifasFacts is not None
        assert EscenarioCanalFacts is not None

    def test_vt_facts_has_expected_fields(self) -> None:
        from nexa_engine.modules.vision_tarifas.models.vt_facts import VisionTarifasFacts

        field_names = {f.name for f in dataclasses.fields(VisionTarifasFacts)}
        assert "escenarios" in field_names
        assert "canales_extension" in field_names

    def test_escenario_canal_facts_has_expected_fields(self) -> None:
        from nexa_engine.modules.vision_tarifas.models.vt_facts import EscenarioCanalFacts

        field_names = {f.name for f in dataclasses.fields(EscenarioCanalFacts)}
        assert "canal" in field_names
        assert "modalidad" in field_names
        assert "nomina_por_mes" in field_names
        assert "nomina_agente_por_mes" in field_names
        assert "no_payroll_por_mes" in field_names

    def test_canal_extension_facts_has_expected_fields(self) -> None:
        from nexa_engine.modules.vision_tarifas.models.vt_facts import CanalExtensionFacts

        field_names = {f.name for f in dataclasses.fields(CanalExtensionFacts)}
        assert "canal" in field_names
        assert "nomina_por_mes" in field_names
        assert "no_payroll_por_mes" in field_names
        assert "nomina_ultimo_mes" in field_names
        assert "no_payroll_ultimo_mes" in field_names

    def test_formula_implementation_now_lives_in_calculator_motor(self) -> None:
        """Tariff formula methods now belong to calculator_motor."""
        source_map = {
            path.name: path.read_text(encoding="utf-8")
            for path in MOTOR_TARIFF_ROOT.rglob("*.py")
        }
        expectations = {
            "reglas.py": ("def calcular(",),
            "reglas_methods_1.py": (
                "def _simular_financiero_canal(",
                "def _desglose_cadena_por_escenario(",
            ),
            "reglas_methods_2.py": (
                "def _calcular_tarifa_canal(",
                "def _costo_op_canal_decomposed(",
                "def _l50(",
                "def _factor_billing(",
            ),
        }
        for filename, method_names in expectations.items():
            source = source_map.get(filename, "")
            for method_name in method_names:
                assert method_name in source, (
                    f"Expected tariff method '{method_name}' to live in "
                    f"modules/calculator_motor/formulas/tarifas/{filename}."
                )

    def test_vision_tarifas_reglas_wrapper_deleted(self) -> None:
        """reglas.py wrapper was deleted in Block 30; __init__.py imports directly."""
        reglas_file = MODULE_ROOT / "reglas.py"
        assert not reglas_file.exists(), (
            "Block 30: modules/vision_tarifas/reglas.py was deleted. "
            "Import VisionTarifasCalculator from calculator_motor directly."
        )
        source = VT_INIT_FILE.read_text(encoding="utf-8")
        assert "from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import" in source
