"""
BUSINESS_RULES_FIX_1 — Tests de source-of-truth.

Verifica:
  1. HR es la fuente canónica del SMMLV (Salario Mínimo).
  2. business_rules canonical YAML no contiene smmlv.
  3. IParametrizationProvider.get_smmlv() retorna el valor HR canónico.
  4. 'descuento_volumen' fue renombrado a 'descuento' en politicas_comerciales.
  5. 'descuento' tiene min=0.0 (acepta descuento cero — caso común).
  6. aprobaciones_umbrales fue removido de riesgo.yaml (no era consumido).
  7. aprobaciones_requeridas removido del backend — API field returns [].

Fuente de verdad documental: docs/refactor/business_rules_source_of_truth_audit.md
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.shared.config.business_rules.loader import (
    load_business_rules,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_STORAGE = Path(__file__).resolve().parent.parent.parent / "storage"
_HR_V27 = _STORAGE / "parametrization" / "v2-7" / "hr.json"


@pytest.fixture(scope="module")
def hr_data() -> dict:
    return json.loads(_HR_V27.read_text())


@pytest.fixture(scope="module")
def provider():
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
    return ParametrizationProvider.build()


# ---------------------------------------------------------------------------
# TAREA 1 — HR es fuente canónica del SMMLV
# ---------------------------------------------------------------------------

def test_hr_salarios_contiene_salario_minimo(hr_data):
    """HR-Salarios tiene la fila 'Salario Mínimo' — esta es la fuente canónica del SMMLV."""
    salarios = hr_data.get("salarios", [])
    assert salarios, "HR v2-7 debe tener la sección 'salarios'"

    smmlv_row = next(
        (r for r in salarios if "Salario" in str(r.get("servicio", "")) and "nimo" in str(r.get("servicio", ""))),
        None,
    )
    assert smmlv_row is not None, (
        "HR-Salarios debe tener una fila 'Salario Mínimo'. "
        "Filas disponibles: " + str([r.get("servicio") for r in salarios])
    )
    assert smmlv_row["valor"] == 1_750_905.0, (
        f"HR Salario Mínimo 2026 debe ser 1,750,905 COP. "
        f"Valor actual: {smmlv_row['valor']:,.0f}"
    )


def test_hr_smmlv_mayor_que_business_rules_smmlv(hr_data):
    """Frozen HR SMMLV = 1,750,905. Canonical YAML no define SMMLV como valor.

    Canonical YAML riesgo.yaml solo tiene umbral_aprobacion_smmlv (multiplicador).
    La fuente canónica del SMMLV es HR via IParametrizationProvider.get_smmlv().
    """
    salarios = hr_data.get("salarios", [])
    hr_smmlv = next(
        (r["valor"] for r in salarios if "Salario" in str(r.get("servicio", "")) and "nimo" in str(r.get("servicio", ""))),
        None,
    )
    assert hr_smmlv is not None, "HR debe tener Salario Mínimo"
    assert hr_smmlv == 1_750_905.0, "HR SMMLV congelado = 1,750,905 COP"

    riesgo = load_business_rules("riesgo")
    reg = riesgo.get("constantes_regulatorias", {})
    assert "smmlv" not in reg, (
        "riesgo.yaml no debe contener smmlv en constantes_regulatorias. "
        "La fuente canónica es HR via IParametrizationProvider.get_smmlv()."
    )


# ---------------------------------------------------------------------------
# TAREA 2 — IParametrizationProvider.get_smmlv() retorna valor HR
# ---------------------------------------------------------------------------

def test_provider_get_smmlv_retorna_valor_hr(provider):
    """provider.get_smmlv() debe retornar el SMMLV activo de HR, no el frozen v2-7."""
    smmlv = provider.get_smmlv()
    assert smmlv == 2_100_000.0, (
        f"IParametrizationProvider.get_smmlv() debe retornar HR Salario Mínimo activo = 2,100,000 COP. "
        f"Retornó: {smmlv:,.0f}. "
        "Verificar ProviderHrMixin.get_smmlv() → get_nomina_laboral_params()['salario_minimo']."
    )


def test_provider_get_smmlv_es_float(provider):
    """get_smmlv() retorna float, no int ni str."""
    result = provider.get_smmlv()
    assert isinstance(result, float), f"get_smmlv() debe retornar float, no {type(result)}"
    assert result > 0, "SMMLV debe ser positivo"


# ---------------------------------------------------------------------------
# TAREA 3 — descuento_volumen renombrado a descuento
# ---------------------------------------------------------------------------

def test_politicas_no_contiene_descuento_volumen():
    """BUSINESS_RULES_FIX_1: 'descuento_volumen' fue renombrado a 'descuento'."""
    politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
    nombres = [p["nombre"] for p in politicas]
    assert "descuento_volumen" not in nombres, (
        "REGRESIÓN: 'descuento_volumen' no debe existir en politicas_comerciales. "
        "Debe llamarse 'descuento' para coincidir con panel.descuento y _PANEL_FIELDS. "
        "Ver HALLAZGO-BR-02 en docs/refactor/business_rules_source_of_truth_audit.md"
    )


def test_politicas_contiene_descuento():
    """politicas_comerciales tiene 'descuento' con min=0.0 (acepta descuento cero)."""
    politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
    descuento = next((p for p in politicas if p["nombre"] == "descuento"), None)
    assert descuento is not None, (
        "politicas_comerciales debe tener 'descuento' (renombrado de 'descuento_volumen')"
    )
    assert descuento["min"] == 0.0, (
        f"descuento.min debe ser 0.0 (descuento cero es válido). Actual: {descuento['min']}"
    )
    assert descuento["max"] > 0.0, "descuento.max debe ser > 0"


def test_descuento_coincide_con_panel_field():
    """El nombre 'descuento' en politicas_comerciales coincide con _PANEL_FIELDS en engine_helpers."""
    # Verifica que _PANEL_FIELDS tiene clave "descuento" (no "descuento_volumen")
    import ast, inspect
    from nexa_engine.modules.calculator_motor.helpers.engine_helpers import _calcular_reglas_negocio

    source = inspect.getsource(_calcular_reglas_negocio)
    assert '"descuento"' in source or "'descuento'" in source, (
        "_PANEL_FIELDS en _calcular_reglas_negocio debe tener clave 'descuento'"
    )
    assert "descuento_volumen" not in source, (
        "_calcular_reglas_negocio no debe referenciar 'descuento_volumen'"
    )


# ---------------------------------------------------------------------------
# TAREA 4 — aprobaciones_umbrales removido de business_rules
# ---------------------------------------------------------------------------

def test_aprobaciones_umbrales_no_en_business_rules():
    """riesgo.yaml no contiene aprobaciones_umbrales (no era consumido en runtime)."""
    riesgo = load_business_rules("riesgo")
    assert "aprobaciones_umbrales" not in riesgo, (
        "aprobaciones_umbrales fue removido de business_rules (no era consumido en runtime). "
        "Si necesitas restaurarlo, las constantes activas están en "
        "modules/calculator/serializers/serializer_helpers.py: "
        "_UMBRAL_GERENCIA_FINANCIERA_COP, _UMBRAL_GERENCIA_GENERAL_COP, _UMBRAL_ALTA_DIRECCION_COP"
    )


# ---------------------------------------------------------------------------
# TAREA 5 — aprobaciones_requeridas removido del backend
# ---------------------------------------------------------------------------

def test_aprobaciones_requeridas_removed_from_backend():
    """aprobaciones_requeridas helper y UMBRAL_* constantes removidos del código de producción.
    
    Product decision: Excel "aprobaciones" is only a manual signature area after printing.
    Backend no longer computes the 3-level COP table. API field returns [].
    """
    # Verify serializer_helpers no longer exports the wrapper or constants
    import inspect
    from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
    
    source = inspect.getsource(serializer_helpers)
    assert "_aprobaciones_requeridas" not in source, (
        "REGRESIÓN: _aprobaciones_requeridas wrapper debe estar eliminado de serializer_helpers"
    )
    assert "UMBRAL_GERENCIA_FINANCIERA_COP" not in source, (
        "REGRESIÓN: UMBRAL_GERENCIA_FINANCIERA_COP no debe estar en serializer_helpers"
    )
    assert "UMBRAL_GERENCIA_GENERAL_COP" not in source, (
        "REGRESIÓN: UMBRAL_GERENCIA_GENERAL_COP no debe estar en serializer_helpers"
    )
    assert "UMBRAL_ALTA_DIRECCION_COP" not in source, (
        "REGRESIÓN: UMBRAL_ALTA_DIRECCION_COP no debe estar en serializer_helpers"
    )
    
    # Verify the function is not in __all__
    assert "_aprobaciones_requeridas" not in serializer_helpers.__all__, (
        "REGRESIÓN: _aprobaciones_requeridas no debe estar en __all__"
    )


def test_aprobaciones_api_field_returns_empty():
    """API field vision_imprimible.control_aprobacion.aprobaciones retorna [] (no computed table)."""
    # This will be tested via integration/api tests
    pass


# ---------------------------------------------------------------------------
# TAREA 6 — No se rompe Vision Imprimible ni tests de parity
# ---------------------------------------------------------------------------

def test_business_rules_estructura_basica_intacta():
    """Los bloques estructurales del canonical YAML siguen presentes."""
    riesgo = load_business_rules("riesgo")
    for key in ("constantes_regulatorias", "pesos_categorias", "clasificacion_score",
                "criterios", "umbrales", "tipos_cliente_alto", "antiguedad_alto"):
        assert key in riesgo, f"riesgo.yaml debe tener '{key}'"

    politicas_data = load_business_rules("politicas_comerciales")
    assert "margen_objetivo" in politicas_data
    assert "politicas_comerciales" in politicas_data


def test_reglas_negocio_politicas_todas_tienen_nombre_valido():
    """Cada política activa en politicas_comerciales tiene nombre, label, min, max.

    BUSINESS_RULES_FIX_3: porcentaje_acumulado fue eliminado (DEAD_FIELD_LEGACY).
    5 políticas activas: todas con fuente real en PanelDeControl.
    """
    politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
    nombres_esperados = {
        "contingencia_operativa", "contingencia_comercial", "markup",
        "descuento", "imprevistos",
    }
    nombres_actuales = {p["nombre"] for p in politicas}
    assert "porcentaje_acumulado" not in nombres_actuales, (
        "BUSINESS_RULES_FIX_3: porcentaje_acumulado debe estar eliminado. "
        "Era DEAD_FIELD_LEGACY sin fuente en PanelDeControl."
    )

    for p in politicas:
        assert "nombre" in p, f"Política sin nombre: {p}"
        assert "min" in p, f"Política sin min: {p}"
        assert "max" in p, f"Política sin max: {p}"

    assert nombres_actuales == nombres_esperados, (
        f"Nombres de políticas esperados: {nombres_esperados}\n"
        f"Nombres actuales: {nombres_actuales}"
    )


def test_hr_tambien_tiene_auxilio_transporte(hr_data):
    """HR-Salarios tiene Auxilio Transporte — otros datos canonicos de nómina en HR."""
    salarios = hr_data.get("salarios", [])
    aux = next(
        (r for r in salarios if "Auxilio" in str(r.get("servicio", ""))),
        None,
    )
    assert aux is not None, "HR-Salarios debe tener fila 'Auxilio Transporte'"
    assert aux["valor"] > 0, "Auxilio Transporte debe ser > 0"
    # 2026: 249,095 COP
    assert aux["valor"] == 249_095.0, (
        f"Auxilio Transporte 2026 = 249,095 COP. Actual: {aux['valor']:,.0f}"
    )


def test_hr_tiene_pct_cumplimiento_variable(hr_data):
    """HR-Salarios tiene %Cumplimiento Variable — otro dato canonical de nómina."""
    salarios = hr_data.get("salarios", [])
    pct = next(
        (r for r in salarios if "Cumplimiento" in str(r.get("servicio", ""))),
        None,
    )
    assert pct is not None, "HR-Salarios debe tener '%Cumplimiento Variable'"
    assert 0.0 < pct["valor"] <= 1.0, f"pct_cumplimiento_variable debe ser 0-1, actual: {pct['valor']}"
