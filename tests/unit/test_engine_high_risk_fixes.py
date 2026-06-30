"""
Unit tests for ENGINE_HIGH_RISK_FIXES_01:
  Fix 1 — ValidationError import in user_input_builders_cadena_a
  Fix 2 — IParametrizationProvider.tasa_mensual_financiacion is a regular method (not @property)
"""
from __future__ import annotations

import inspect

import pytest


# ── Fix 1: ValidationError import ────────────────────────────────────────────

def test_validation_error_importable_from_builders_cadena_a():
    """ValidationError must be importable from the cadena_a builders module without NameError."""
    from nexa_engine.modules.calculator_motor.mixins import user_input_builders_cadena_a as mod
    from nexa_engine.modules.shared.exceptions import ValidationError

    assert hasattr(mod, "ValidationError"), (
        "user_input_builders_cadena_a must import ValidationError at module level; "
        "calling _perfil_a() with bad input would raise NameError otherwise"
    )
    assert mod.ValidationError is ValidationError


def test_perfil_a_raises_domain_validation_error_on_bad_field():
    """_perfil_a() must raise the domain ValidationError (not NameError) when a field is bad."""
    from nexa_engine.modules.calculator_motor.mixins.user_input_builders_cadena_a import (
        UserInputBuildersCadenaAMixin,
    )
    from nexa_engine.modules.shared.exceptions import ValidationError

    class _Stub(UserInputBuildersCadenaAMixin):
        pass

    stub = _Stub.__new__(_Stub)

    bad_input = {
        "nombre": "TestPerfil",
        "cadena_b_mensual": "not_a_number",  # triggers ValueError → should raise ValidationError
    }

    with pytest.raises(ValidationError):
        stub._perfil_a(bad_input)


# ── Fix 2: IParametrizationProvider.tasa_mensual_financiacion ────────────────

def test_tasa_mensual_financiacion_is_not_a_property_in_protocol():
    """Protocol must declare tasa_mensual_financiacion as a regular method, not @property."""
    from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider

    member = IParametrizationProvider.__protocol_attrs__ if hasattr(
        IParametrizationProvider, "__protocol_attrs__"
    ) else None

    # Direct inspection: the attribute in the class dict must NOT be a property
    attr = IParametrizationProvider.__dict__.get("tasa_mensual_financiacion")
    assert attr is not None, "tasa_mensual_financiacion must be defined on IParametrizationProvider"
    assert not isinstance(attr, property), (
        "tasa_mensual_financiacion is declared as @property in the Protocol but all callers "
        "and implementations use method call syntax (). Remove @property from Protocol."
    )


def test_provider_implementation_callable_with_parentheses():
    """A minimal IParametrizationProvider implementation must be callable with ()."""
    from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
    from unittest.mock import MagicMock

    mock_provider = MagicMock(spec=IParametrizationProvider)
    mock_provider.tasa_mensual_financiacion.return_value = 0.0088

    result = mock_provider.tasa_mensual_financiacion()
    assert result == pytest.approx(0.0088)


def test_protocol_method_signature_matches_caller_convention():
    """tasa_mensual_financiacion must be a callable (function) in the Protocol — not a property descriptor."""
    from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider

    attr = IParametrizationProvider.__dict__["tasa_mensual_financiacion"]
    assert callable(attr), "tasa_mensual_financiacion must be callable in the Protocol"
    assert inspect.isfunction(attr), "tasa_mensual_financiacion must be a function, not a property"
