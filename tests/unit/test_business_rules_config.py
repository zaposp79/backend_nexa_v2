"""
tests/unit/test_business_rules_config.py
==========================================
Tests para la configuración del modelo de riesgo.

Después de la limpieza de business_rules:
- reglas_negocio.json eliminado (era versión 2026-01 obsoleta, distinta del storage activo v2-7)
- riesgo_config.json eliminado (era duplicado del fallback histórico y del storage v2-7)

BUSINESS_RULES_FIX_2B:
- smmlv eliminado de business_rules/v2-7.json y de config/business_rules/riesgo.yaml.
- RiesgoCalculator requiere smmlv kwarg obligatorio.
- Todos los tests pasan smmlv explícitamente.

Los valores de referencia para el motor vienen de:
  - storage/parametrization/business_rules/v2-7.json (runtime via BusinessRulesRepository)
  - config/business_rules/riesgo.yaml (fallback defensivo)

Este archivo valida únicamente que RiesgoCalculator acepta inyección de config
y que el fallback YAML es internamente consistente.
"""
from __future__ import annotations

import copy

import pytest

from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
from nexa_engine.modules.shared.config.business_rules.loader import (
    load_business_rules,
)

# BUSINESS_RULES_FIX_2B: smmlv es obligatorio. HR canónico para todos los tests.
_SMMLV_HR_2026: float = 1_750_905.0


class TestRiesgoCalculatorConfigInjection:
    """RiesgoCalculator acepta config externa y aplica correctamente."""

    def test_default_config_is_internally_consistent(self):
        """El fallback YAML produce un calculador funcional con smmlv explícito."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        assert calc._smmlv == _SMMLV_HR_2026
        assert 0 < calc._umbral_aprobacion_smmlv
        assert abs(calc._peso_cliente + calc._peso_operativo - 1.0) < 1e-9
        assert calc._score_limite_alto > calc._score_limite_medio

    def test_kwarg_smmlv_es_fuente_exclusiva(self):
        """SMMLV viene exclusivamente del kwarg — no de riesgo_config. (FIX_2B)"""
        config = copy.deepcopy(load_business_rules("riesgo"))
        config["constantes_regulatorias"]["umbral_aprobacion_smmlv"] = 500.0
        calc = RiesgoCalculator(config, smmlv=_SMMLV_HR_2026)
        assert calc._smmlv == _SMMLV_HR_2026
        assert calc._umbral_aprobacion_smmlv == 500.0

    def test_custom_threshold_overrides(self):
        """Config externa sobreescribe umbrales (smmlv via kwarg)."""
        config = copy.deepcopy(load_business_rules("riesgo"))
        config["umbrales"] = {**config["umbrales"], "rotacion_alto": 0.20}
        calc = RiesgoCalculator(config, smmlv=_SMMLV_HR_2026)
        assert calc._rotacion_limite_alto == 0.20

    def test_partial_config_completes_from_canonical_yaml(self):
        """Config parcial se completa desde riesgo.yaml, no desde defaults locales."""
        calc = RiesgoCalculator(
            {
                "umbrales": {"rotacion_alto": 0.20},
                "tipos_cliente_alto": ["Cliente Especial"],
            },
            smmlv=_SMMLV_HR_2026,
        )

        assert calc._rotacion_limite_alto == 0.20
        assert calc._peso_cliente == 0.4
        assert calc._score_limite_alto == 2.5
        assert len(calc._criterios_meta) == 10
        assert "Cliente Especial" in calc._tipos_cliente_alto

    def test_default_pesos_categorias_sum_to_1(self):
        """Cliente + Operativo = 1.0 en el fallback YAML."""
        pesos = load_business_rules("riesgo")["pesos_categorias"]
        assert abs(pesos["Cliente"] + pesos["Operativo"] - 1.0) < 1e-9
