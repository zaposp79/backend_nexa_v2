import inspect

from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import (
    VisionTarifasCalculator as CanonicalVisionTarifasCalculator,
)
from nexa_engine.modules.vision_tarifas import VisionTarifasCalculator
from nexa_engine.modules.vision_tarifas.api.router import get_vision_tarifas


def test_public_layer_exports_compatibility_calculator():
    assert VisionTarifasCalculator is CanonicalVisionTarifasCalculator


def test_public_api_route_imports_successfully():
    assert callable(get_vision_tarifas)


def test_public_layer_no_compat_wrapper_reglas_deleted():
    """Verify reglas.py compat wrapper was deleted (Block 30)."""
    from pathlib import Path
    reglas_file = (
        Path(__file__).parents[2] / "modules" / "vision_tarifas" / "reglas.py"
    )
    assert not reglas_file.exists(), (
        "Block 30: modules/vision_tarifas/reglas.py was deleted. "
        "VisionTarifasCalculator now imports through __init__.py directly."
    )


def test_public_mixins_init_is_read_only_export_surface():
    import nexa_engine.modules.vision_tarifas.mixins as mixins_mod

    source = inspect.getsource(mixins_mod)
    assert "VisionTarifasMethodsMixin" in source
    assert "def _factor_billing(" not in source
    assert "ProfitabilityCalculator" not in source
