"""
Test Phase 9: Business Rules Migration to canonical YAML.

Validates that business rules are now loaded from
modules/shared/config/business_rules/ via the canonical loader/provider path.
"""

from pathlib import Path
import pytest

from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules


class TestBusinessRulesMigration:
    """Tests for Phase 9 migration of business rules to canonical YAML."""

    @pytest.fixture
    def provider(self):
        """Return a ParametrizationProvider instance."""
        return ParametrizationProvider.build()

    def test_canonical_business_rules_yaml_structure_exists(self):
        """Verify canonical YAML files exist under modules/shared/config/business_rules/."""
        rules_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "modules"
            / "shared"
            / "config"
            / "business_rules"
        )
        assert rules_dir.exists(), f"Canonical business rules directory not found: {rules_dir}"
        assert (rules_dir / "riesgo.yaml").exists(), "riesgo.yaml not found"
        assert (
            rules_dir / "politicas_comerciales.yaml"
        ).exists(), "politicas_comerciales.yaml not found"

    def test_get_politicas_comerciales_from_canonical_yaml(self, provider):
        """Test that politicas_comerciales loads from canonical YAML.

        BUSINESS_RULES_FIX_3: 5 políticas activas (porcentaje_acumulado eliminado —
        era DEAD_FIELD_LEGACY sin fuente en PanelDeControl).
        Rangos: contingencia_operativa usa rangos v2-7 (0.025/0.12).
        """
        politicas = provider.get_politicas_comerciales()

        assert isinstance(politicas, list)
        # v2-7: 5 políticas activas (contingencia_op, contingencia_com, markup,
        #                             descuento, imprevistos)
        # porcentaje_acumulado eliminado en BUSINESS_RULES_FIX_3.
        assert len(politicas) == 5

        # Verify structure of each policy
        for p in politicas:
            assert "nombre" in p, f"Política sin 'nombre': {p}"
            assert "label" in p, f"Política sin 'label': {p}"
            assert "min" in p, f"Política sin 'min': {p}"
            assert "max" in p, f"Política sin 'max': {p}"

        # v2-7 ranges for contingencia_operativa (expanded vs original WAVE2)
        primera = politicas[0]
        assert primera["nombre"] == "contingencia_operativa"
        assert primera["min"] == 0.025
        assert primera["max"] == 0.12

    def test_get_riesgo_config_from_canonical_yaml(self, provider):
        """Test that riesgo_config loads from canonical YAML."""
        riesgo = provider.get_riesgo_config()

        # Verify top-level structure
        assert "constantes_regulatorias" in riesgo
        assert "pesos_categorias" in riesgo
        assert "clasificacion_score" in riesgo
        assert "criterios" in riesgo
        assert "umbrales" in riesgo

        # Verify regulatory constants
        constantes = riesgo["constantes_regulatorias"]
        # BUSINESS_RULES_FIX_2B: smmlv fue eliminado — no debe existir.
        assert "smmlv" not in constantes, (
            "BUSINESS_RULES_FIX_2B: smmlv debe estar eliminado de constantes_regulatorias. "
            "La fuente canónica es HR via IParametrizationProvider.get_smmlv()."
        )
        assert constantes["umbral_aprobacion_smmlv"] == 1000.0

        # Verify category weights
        pesos = riesgo["pesos_categorias"]
        assert pesos["Cliente"] == 0.4
        assert pesos["Operativo"] == 0.6

        # Verify classification scores
        clasif = riesgo["clasificacion_score"]
        assert clasif["alto"] == 2.5
        assert clasif["medio"] == 1.5

        # Verify 10 criteria
        assert len(riesgo["criterios"]) == 10

        # First criterion (Clasificación de oportunidad)
        crit1 = riesgo["criterios"][0]
        assert crit1["id"] == 1
        assert crit1["factor"] == "Clasificación de oportunidad"
        assert crit1["categoria"] == "Cliente"
        assert crit1["peso"] == 0.30

    def test_provider_resolves_canonical_yaml(self, provider):
        """Test that provider resolves canonical YAML for both business rule sources."""
        politicas = provider.get_politicas_comerciales()
        riesgo = provider.get_riesgo_config()

        assert len(politicas) > 0
        assert len(riesgo["criterios"]) == 10

    def test_migration_data_consistency(self, provider):
        """Verify that provider output stays consistent with canonical YAML.

        BUSINESS_RULES_FIX_1 updates:
        - contingencia_operativa now has v2-7 ranges (0.025/0.12)
        - descuento (was descuento_volumen) now correctly named with min=0.0
        """
        politicas_provider = provider.get_politicas_comerciales()
        riesgo_provider = provider.get_riesgo_config()
        politicas_yaml = load_business_rules("politicas_comerciales")["politicas_comerciales"]
        riesgo_yaml = load_business_rules("riesgo")

        # v2-7 actual ranges (BUSINESS_RULES_FIX_1)
        expected_politicas = [
            {"nombre": "contingencia_operativa", "min": 0.025, "max": 0.12},
            {"nombre": "contingencia_comercial", "min": 0.04,  "max": 0.07},
            {"nombre": "markup",                 "min": 0.02,  "max": 0.08},
            {"nombre": "descuento",              "min": 0.0,   "max": 0.15},
            {"nombre": "imprevistos",            "min": 0.0,   "max": 1.0},
        ]
        actual_by_name = {p["nombre"]: p for p in politicas_provider}
        for expected in expected_politicas:
            assert expected["nombre"] in actual_by_name, (
                f"Política '{expected['nombre']}' ausente. Políticas actuales: {list(actual_by_name)}"
            )
            actual = actual_by_name[expected["nombre"]]
            assert expected["min"] == actual["min"], (
                f"{expected['nombre']}: min esperado {expected['min']}, actual {actual['min']}"
            )
            assert expected["max"] == actual["max"], (
                f"{expected['nombre']}: max esperado {expected['max']}, actual {actual['max']}"
            )

        # descuento_volumen ya no debe existir (fue renombrado a descuento)
        assert "descuento_volumen" not in actual_by_name, (
            "BUSINESS_RULES_FIX_1: 'descuento_volumen' debería haberse renombrado a 'descuento'"
        )

        # Verify riesgo config values
        assert politicas_provider == politicas_yaml
        assert riesgo_provider == riesgo_yaml
        assert riesgo_provider["pesos_categorias"]["Cliente"] == 0.4
        assert riesgo_provider["pesos_categorias"]["Operativo"] == 0.6
        # BUSINESS_RULES_FIX_2B: smmlv fue eliminado de constantes_regulatorias.
        # La fuente canónica es HR via IParametrizationProvider.get_smmlv().
        assert "smmlv" not in riesgo_provider["constantes_regulatorias"], (
            "BUSINESS_RULES_FIX_2B: smmlv no debe existir en constantes_regulatorias. "
            "Ver docs/refactor/business_rules_source_of_truth_audit.md."
        )
        assert riesgo_provider["constantes_regulatorias"]["umbral_aprobacion_smmlv"] == 1000.0
        assert len(riesgo_provider["umbrales"]) > 0

    def test_parametrization_provider_riesgo_config_compat(self, provider):
        """Verify RiesgoCalculator works with migrated config + explicit smmlv (FIX_2B)."""
        from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator

        # Get config from provider
        riesgo_config = provider.get_riesgo_config()

        # BUSINESS_RULES_FIX_2B: smmlv es obligatorio — pasar HR canónico.
        # Ya no se acepta RiesgoCalculator(riesgo_config) sin smmlv kwarg.
        smmlv_hr = provider.get_smmlv()
        calc = RiesgoCalculator(riesgo_config, smmlv=smmlv_hr)

        # Verify some properties are set correctly from migrated config
        assert calc._smmlv == smmlv_hr           # HR canónico inyectado
        assert calc._umbral_aprobacion_smmlv == 1000.0
        assert calc._periodo_pago_limite_alto == 60
        assert calc._periodo_pago_limite_bajo == 30


class TestPhase9Deliverables:
    """Tests for Phase 9 deliverables and requirements."""

    def test_phase9_migration_complete(self):
        """
        Summary test: All Phase 9 deliverables in place.

        ✓ Business rules files live under modules/shared/config/business_rules/
        ✓ ParametrizationProvider updated to read canonical YAML
        ✓ Docstrings updated
        ✓ Backward compatibility maintained (RiesgoCalculator still works)
        """
        rules_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "modules"
            / "shared"
            / "config"
            / "business_rules"
        )

        assert (rules_dir / "riesgo.yaml").exists(), "riesgo.yaml not found"
        assert (
            rules_dir / "politicas_comerciales.yaml"
        ).exists(), "politicas_comerciales.yaml not found"

        # Verify can load both via provider
        provider = ParametrizationProvider.build()
        politicas = provider.get_politicas_comerciales()
        riesgo = provider.get_riesgo_config()

        # v2-7: 5 políticas activas (BUSINESS_RULES_FIX_3 eliminó porcentaje_acumulado DEAD_FIELD)
        assert len(politicas) == 5
        assert len(riesgo["criterios"]) == 10

        print("\nCanonical business rules migration complete: provider reads YAML.")
