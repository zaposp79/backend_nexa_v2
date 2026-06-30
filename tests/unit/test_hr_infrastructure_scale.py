"""Unit tests for HR infrastructure cost scale normalization.

HR-CostoFijo legacy uploads stored values in miles de COP (e.g. 415.975 = 415,975 COP).
_normalizar_costo_cop() detects and corrects this scale error at read time.
Idempotent: values already in full COP pass through unchanged.
"""

import pytest

from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import (
    _normalizar_costo_cop,
    _HR_INFRA_COST_SCALE_THRESHOLD,
)


class TestNormalizarCostoCop:
    """Tests for the legacy miles→COP normalization helper."""

    def test_normaliza_valor_legacy_miles(self):
        # 415.975 stored in miles → 415,975.0 COP
        result = _normalizar_costo_cop(415.975)
        assert result == pytest.approx(415_975.0)

    def test_normaliza_arriendo_tipico(self):
        # 191.968 miles → 191,968.0 COP (typical Barranquilla arriendo before fix)
        result = _normalizar_costo_cop(191.968)
        assert result == pytest.approx(191_968.0)

    def test_idempotente_valor_cop_grande(self):
        # 415975.0 already in COP → no change
        result = _normalizar_costo_cop(415_975.0)
        assert result == pytest.approx(415_975.0)

    def test_idempotente_valor_justo_en_threshold(self):
        # Exactly at threshold → treated as already in COP (no ×1000)
        result = _normalizar_costo_cop(_HR_INFRA_COST_SCALE_THRESHOLD)
        assert result == pytest.approx(_HR_INFRA_COST_SCALE_THRESHOLD)

    def test_idempotente_valor_sobre_threshold(self):
        # 10_001 > 10_000 → unchanged
        result = _normalizar_costo_cop(10_001.0)
        assert result == pytest.approx(10_001.0)

    def test_zero_preservado(self):
        assert _normalizar_costo_cop(0) == 0.0

    def test_zero_float_preservado(self):
        assert _normalizar_costo_cop(0.0) == 0.0

    def test_none_devuelve_cero(self):
        assert _normalizar_costo_cop(None) == 0.0

    def test_valor_grande_no_modificado(self):
        assert _normalizar_costo_cop(1_000_000.0) == pytest.approx(1_000_000.0)

    def test_valor_pequeno_positivo_escala(self):
        # 9_999.99 < 10_000 → multiplied by 1000
        result = _normalizar_costo_cop(9_999.99)
        assert result == pytest.approx(9_999_990.0)

    def test_threshold_es_10k(self):
        assert _HR_INFRA_COST_SCALE_THRESHOLD == 10_000.0


class TestInfrastructureCostsWhitelist:
    """Integration tests for get_infrastructure_costs() with scale normalization whitelist."""

    def test_whitelist_escala_arriendo_miles(self):
        """Arriendo en miles de COP debe escalarse (whitelist)."""
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import (
            InfrastructureParametrizationRepository,
            _SERVICIOS_ESCALA_GRANDE,
        )
        from unittest.mock import MagicMock

        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "costo_fijo": [
                {
                    "localidad": "Bogota",
                    "servicio": "arriendo",
                    "valor": 415.975,  # miles de COP
                },
                {
                    "localidad": "Bogota",
                    "servicio": "energia",
                    "valor": 45.5,  # miles de COP
                },
                {
                    "localidad": "Bogota",
                    "servicio": "agua",
                    "valor": 735.88,  # valor pequeño legítimo
                },
                {
                    "localidad": "Bogota",
                    "servicio": "gas",
                    "valor": 17.26,  # valor pequeño legítimo
                },
                {
                    "localidad": "Bogota",
                    "servicio": "vigilancia",
                    "valor": 200.0,  # miles de COP
                },
                {
                    "localidad": "Bogota",
                    "servicio": "aseo",
                    "valor": 89.99,  # miles de COP
                },
                {
                    "localidad": "Bogota",
                    "servicio": "mantenimiento",
                    "valor": 50.0,  # valor pequeño legítimo
                },
            ]
        }

        repo = InfrastructureParametrizationRepository(resolver)
        costs = repo.get_infrastructure_costs("Bogota")

        # Whitelist: must scale
        assert costs["arriendo"] == pytest.approx(415_975.0), (
            f"arriendo in whitelist should scale: 415.975 → 415,975. "
            f"Got {costs['arriendo']}"
        )
        assert costs["energia"] == pytest.approx(45_500.0), (
            f"energia in whitelist should scale: 45.5 → 45,500. Got {costs['energia']}"
        )
        assert costs["vigilancia"] == pytest.approx(200_000.0), (
            f"vigilancia in whitelist should scale: 200 → 200,000. Got {costs['vigilancia']}"
        )
        assert costs["aseo"] == pytest.approx(89_990.0), (
            f"aseo in whitelist should scale: 89.99 → 89,990. Got {costs['aseo']}"
        )

        # NOT in whitelist: must preserve as-is
        assert costs["agua"] == pytest.approx(735.88), (
            f"agua NOT in whitelist — must preserve: 735.88 → 735.88. Got {costs['agua']}"
        )
        assert costs["gas"] == pytest.approx(17.26), (
            f"gas NOT in whitelist — must preserve: 17.26 → 17.26. Got {costs['gas']}"
        )
        assert costs["mantenimiento"] == pytest.approx(50.0), (
            f"mantenimiento NOT in whitelist — must preserve: 50 → 50. Got {costs['mantenimiento']}"
        )

    def test_whitelist_idempotente_valores_ya_cop(self):
        """Valores ya en COP (> threshold) NO deben multiplicarse de nuevo."""
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import (
            InfrastructureParametrizationRepository,
        )
        from unittest.mock import MagicMock

        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "costo_fijo": [
                {
                    "localidad": "Bogota",
                    "servicio": "arriendo",
                    "valor": 415_975.0,  # Already in COP
                },
                {
                    "localidad": "Bogota",
                    "servicio": "energia",
                    "valor": 10_000.0,  # Exactly at threshold
                },
                {
                    "localidad": "Bogota",
                    "servicio": "vigilancia",
                    "valor": 50_000.0,  # Well above threshold
                },
                {
                    "localidad": "Bogota",
                    "servicio": "agua",
                    "valor": 1000.0,  # Small but legitimate
                },
                {
                    "localidad": "Bogota",
                    "servicio": "gas",
                    "valor": 500.0,  # Small but legitimate
                },
                {
                    "localidad": "Bogota",
                    "servicio": "aseo",
                    "valor": 200.0,  # Small but legitimate (no scale)
                },
                {
                    "localidad": "Bogota",
                    "servicio": "mantenimiento",
                    "valor": 300.0,  # Small but legitimate
                },
            ]
        }

        repo = InfrastructureParametrizationRepository(resolver)
        costs = repo.get_infrastructure_costs("Bogota")

        # Values already >= threshold: preserved unchanged
        assert costs["arriendo"] == pytest.approx(415_975.0)
        assert costs["energia"] == pytest.approx(10_000.0)
        assert costs["vigilancia"] == pytest.approx(50_000.0)

        # Values < threshold but NOT in whitelist: preserved unchanged
        assert costs["agua"] == pytest.approx(1000.0)
        assert costs["gas"] == pytest.approx(500.0)
        assert costs["mantenimiento"] == pytest.approx(300.0)

        # aseo is in whitelist but value is below threshold → scale
        assert costs["aseo"] == pytest.approx(200_000.0)

    def test_whitelist_preserva_zero_none(self):
        """Zero and None values deben preservarse (no escala)."""
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import (
            InfrastructureParametrizationRepository,
        )
        from unittest.mock import MagicMock

        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "costo_fijo": [
                {
                    "localidad": "Bogota",
                    "servicio": "arriendo",
                    "valor": 0,  # Zero
                },
                {
                    "localidad": "Bogota",
                    "servicio": "energia",
                    "valor": None,  # None (missing)
                },
                {
                    "localidad": "Bogota",
                    "servicio": "agua",
                    "valor": 0.0,
                },
                {
                    "localidad": "Bogota",
                    "servicio": "gas",
                    "valor": None,
                },
                {
                    "localidad": "Bogota",
                    "servicio": "vigilancia",
                    "valor": 0,
                },
                {
                    "localidad": "Bogota",
                    "servicio": "aseo",
                    "valor": None,
                },
                {
                    "localidad": "Bogota",
                    "servicio": "mantenimiento",
                    "valor": 0,
                },
            ]
        }

        repo = InfrastructureParametrizationRepository(resolver)
        costs = repo.get_infrastructure_costs("Bogota")

        # All should be 0.0 (None from row becomes 0.0)
        assert costs["arriendo"] == 0.0
        assert costs["energia"] == 0.0
        assert costs["agua"] == 0.0
        assert costs["gas"] == 0.0
        assert costs["vigilancia"] == 0.0
        assert costs["aseo"] == 0.0
        assert costs["mantenimiento"] == 0.0
