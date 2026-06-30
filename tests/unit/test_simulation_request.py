"""
tests/unit/test_simulation_request.py
======================================
Tests for SimulationRequest DTO and SimulationRequestValidator.

Validates:
  - Typed DTO parses valid requests correctly
  - Forbidden master-data fields are rejected at parse time
  - Metadata (_-prefixed) fields are stripped by to_loader_dict()
  - Validator catches required field errors
  - Validator catches range/constraint warnings
  - All existing test fixtures parse through the DTO without error
  - to_loader_dict() output is compatible with UserInputLoader
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.calculator_motor.dto.request_dto import SimulationRequest
from nexa_engine.modules.calculator_motor.validation.simulation_request_validator import (
    SimulationRequestValidator,
    ValidationResult,
)
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader


# ── Paths ────────────────────────────────────────────────────────────────────

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_CASES_DIR = BACKEND_ROOT / "test_cases"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _minimal_request() -> dict:
    """Minimal valid request dict."""
    return {
        "panel_de_control": {
            "linea_negocio": "Cobranzas",
            "fecha_inicio": "2026-01-01",
            "meses_contrato": 12,
            "margen": 0.18,
            "op_cont": 0.05,
        },
        "condiciones_cadena_a": {"perfiles": []},
        "condiciones_cadena_b": {"canales": []},
        "condiciones_cadena_c": {"canales": []},
    }


def _request_with_profiles() -> dict:
    """Request with a valid Cadena A profile."""
    req = _minimal_request()
    req["condiciones_cadena_a"] = {
        "perfiles": [
            {
                "nombre": "WhatsApp Inbound",
                "rol": "Agente Basico",
                "canal": "WhatsApp",
                "modalidad": "Inbound",
                "fte": 6.0,
                "pct_presencia": 1.0,
            }
        ]
    }
    return req


# ── DTO Parsing Tests ────────────────────────────────────────────────────────

class TestSimulationRequestParsing:

    def test_minimal_request_parses(self):
        req = SimulationRequest(**_minimal_request())
        assert req.panel_de_control.linea_negocio == "Cobranzas"
        assert req.panel_de_control.meses_contrato == 12

    def test_defaults_for_empty_cadenas(self):
        data = {"panel_de_control": {"linea_negocio": "SAC", "fecha_inicio": "2026-06-01"}}
        req = SimulationRequest(**data)
        assert req.condiciones_cadena_a.perfiles == []
        assert req.condiciones_cadena_b.canales == []
        assert req.condiciones_cadena_c.canales == []

    def test_profile_fields_parsed(self):
        req = SimulationRequest(**_request_with_profiles())
        perfil = req.condiciones_cadena_a.perfiles[0]
        assert perfil.nombre == "WhatsApp Inbound"
        assert perfil.fte == 6.0
        assert perfil.modalidad == "Inbound"

    def test_panel_defaults(self):
        data = {"panel_de_control": {"linea_negocio": "SAC", "fecha_inicio": "2026-01-01"}}
        req = SimulationRequest(**data)
        p = req.panel_de_control
        assert p.periodo_pago_dias == 90
        assert p.activa_financiacion is True
        assert p.aplica_ley_1819 is True
        assert p.componente_indexacion_humano == "IPC"

    def test_cadena_b_with_channels_and_opex(self):
        data = _minimal_request()
        data["condiciones_cadena_b"] = {
            "canales": [
                {"nombre": "Inbound WhatsApp", "modalidad": "Inbound",
                 "producto": "WhatsApp", "volumen_mensual": 1000},
            ],
            "opex_consumo_variable": [
                {"nombre": "Token IA", "producto": "Token IA",
                 "modalidad": "Inbound", "canal": "WhatsApp",
                 "valor_unitario": 50.0, "cantidad": 500},
            ],
        }
        req = SimulationRequest(**data)
        assert len(req.condiciones_cadena_b.canales) == 1
        assert req.condiciones_cadena_b.canales[0].volumen_mensual == 1000
        assert len(req.condiciones_cadena_b.opex_consumo_variable) == 1


# ── Forbidden Fields Tests ───────────────────────────────────────────────────

class TestForbiddenFields:

    def test_rejects_parametros_nomina(self):
        data = _minimal_request()
        data["parametros_nomina"] = {"tarifa_dia_cap": 50000}
        with pytest.raises(ValueError, match="parametros_nomina"):
            SimulationRequest(**data)

    def test_rejects_parametros_no_payroll(self):
        data = _minimal_request()
        data["parametros_no_payroll"] = {}
        with pytest.raises(ValueError, match="parametros_no_payroll"):
            SimulationRequest(**data)

    def test_rejects_parametros_calculo(self):
        data = _minimal_request()
        data["parametros_calculo"] = {"pct_rotacion": 0.05}
        with pytest.raises(ValueError, match="parametros_calculo"):
            SimulationRequest(**data)

    def test_rejects_parametros_cadena_b(self):
        data = _minimal_request()
        data["parametros_cadena_b"] = {"costo_personal_sm": 100000}
        with pytest.raises(ValueError, match="parametros_cadena_b"):
            SimulationRequest(**data)

    def test_rejects_legacy_perfiles_cadena_a(self):
        data = _minimal_request()
        data["perfiles_cadena_a"] = [{"nombre": "test", "fte": 1}]
        with pytest.raises(ValueError, match="perfiles_cadena_a"):
            SimulationRequest(**data)

    def test_rejects_horas_formacion_mensual(self):
        data = _minimal_request()
        data["horas_formacion_mensual"] = 160
        with pytest.raises(ValueError, match="horas_formacion_mensual"):
            SimulationRequest(**data)


# ── Metadata Stripping Tests ─────────────────────────────────────────────────

class TestMetadataStripping:

    def test_top_level_metadata_stripped(self):
        data = _minimal_request()
        data["_comment"] = "This is a test scenario"
        data["_scenario"] = "bancamia_12m"
        req = SimulationRequest(**data)
        loader_dict = req.to_loader_dict()
        assert "_comment" not in loader_dict
        assert "_scenario" not in loader_dict

    def test_nested_metadata_stripped(self):
        data = _request_with_profiles()
        data["condiciones_cadena_a"]["perfiles"][0]["_comment"] = "K50 profile"
        data["condiciones_cadena_a"]["perfiles"][0]["_k50_contrib"] = 1234
        req = SimulationRequest(**data)
        loader_dict = req.to_loader_dict()
        perfil = loader_dict["condiciones_cadena_a"]["perfiles"][0]
        assert "_comment" not in perfil
        assert "_k50_contrib" not in perfil

    def test_cadena_b_metadata_stripped(self):
        data = _minimal_request()
        data["condiciones_cadena_b"]["_l50_derivation"] = "some derivation"
        req = SimulationRequest(**data)
        loader_dict = req.to_loader_dict()
        assert "_l50_derivation" not in loader_dict["condiciones_cadena_b"]

    def test_real_fields_preserved_after_stripping(self):
        data = _request_with_profiles()
        data["_comment"] = "metadata"
        req = SimulationRequest(**data)
        loader_dict = req.to_loader_dict()
        assert "panel_de_control" in loader_dict
        assert loader_dict["panel_de_control"]["linea_negocio"] == "Cobranzas"
        assert len(loader_dict["condiciones_cadena_a"]["perfiles"]) == 1


# ── Validator Tests ──────────────────────────────────────────────────────────

class TestSimulationRequestValidator:

    @pytest.fixture
    def validator(self):
        return SimulationRequestValidator()

    def test_valid_minimal_request(self, validator):
        req = SimulationRequest(**_minimal_request())
        result = validator.validate(req)
        assert result.is_valid

    def test_valid_request_with_profiles(self, validator):
        req = SimulationRequest(**_request_with_profiles())
        result = validator.validate(req)
        assert result.is_valid

    def test_missing_linea_negocio(self, validator):
        data = _minimal_request()
        data["panel_de_control"]["linea_negocio"] = ""
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("linea_negocio" in e for e in result.errors)

    def test_missing_fecha_inicio(self, validator):
        data = _minimal_request()
        data["panel_de_control"]["fecha_inicio"] = ""
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("fecha_inicio" in e for e in result.errors)

    def test_zero_meses_contrato(self, validator):
        data = _minimal_request()
        data["panel_de_control"]["meses_contrato"] = 0
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("meses_contrato" in e for e in result.errors)

    def test_negative_op_cont(self, validator):
        data = _minimal_request()
        data["panel_de_control"]["op_cont"] = -0.01
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("op_cont" in e for e in result.errors)

    def test_zero_fte_profile(self, validator):
        data = _request_with_profiles()
        data["condiciones_cadena_a"]["perfiles"][0]["fte"] = 0
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("fte" in e for e in result.errors)

    def test_negative_volume_cadena_b(self, validator):
        data = _minimal_request()
        data["condiciones_cadena_b"] = {
            "canales": [
                {"nombre": "Inbound WA", "modalidad": "Inbound",
                 "producto": "WhatsApp", "volumen_mensual": -100},
            ]
        }
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("volumen_mensual" in e for e in result.errors)

    def test_negative_device_amortization(self, validator):
        data = _minimal_request()
        data["condiciones_cadena_b"] = {
            "dispositivos_sm": [
                {"tipo": "Monitor", "costo_unitario": 500000,
                 "cantidad": 2, "meses_amortizacion": 0}
            ]
        }
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert not result.is_valid
        assert any("meses_amortizacion" in e for e in result.errors)

    def test_warning_empty_ciudad(self, validator):
        data = _minimal_request()
        data["panel_de_control"]["ciudad"] = ""
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert result.is_valid  # warning, not error
        assert any("ciudad" in w for w in result.warnings)

    def test_warning_negative_margen(self, validator):
        data = _minimal_request()
        data["panel_de_control"]["margen"] = -0.05
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert result.is_valid  # warning, not error
        assert any("margen" in w for w in result.warnings)

    def test_warning_invalid_modalidad(self, validator):
        data = _request_with_profiles()
        data["condiciones_cadena_a"]["perfiles"][0]["modalidad"] = "Bidirectional"
        req = SimulationRequest(**data)
        result = validator.validate(req)
        assert result.is_valid
        assert any("modalidad" in w for w in result.warnings)


# ── Fixture Compatibility Tests ──────────────────────────────────────────────

class TestFixtureCompatibility:
    """Ensures all existing canonical test fixtures parse through SimulationRequest."""

    CANONICAL_FIXTURES = [
        "bancamia_canonical_k50.json",
        "bancamia_excel_match.json",
        "bancamia_whatsapp_only.json",
        "bancamia_webchat_only.json",
        "bancamia_correo_only.json",
        "seguros_adl_cobranzas.json",
        "excel_v24_canonical_bancamia.json",
    ]

    @pytest.mark.parametrize("fixture_name", CANONICAL_FIXTURES)
    def test_fixture_parses_through_dto(self, fixture_name):
        path = TEST_CASES_DIR / fixture_name
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        req = SimulationRequest(**data)
        assert req.panel_de_control is not None

    @pytest.mark.parametrize("fixture_name", CANONICAL_FIXTURES)
    def test_fixture_to_loader_dict_is_valid(self, fixture_name):
        """to_loader_dict() output must be loadable by UserInputLoader."""
        path = TEST_CASES_DIR / fixture_name
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        req = SimulationRequest(**data)
        loader_dict = req.to_loader_dict()
        # Must not raise
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(loader_dict)
        assert user_input.panel is not None

    @pytest.mark.parametrize("fixture_name", CANONICAL_FIXTURES)
    def test_fixture_metadata_stripped(self, fixture_name):
        path = TEST_CASES_DIR / fixture_name
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        req = SimulationRequest(**data)
        loader_dict = req.to_loader_dict()
        # No top-level _-prefixed keys
        meta_keys = [k for k in loader_dict.keys() if k.startswith("_")]
        assert meta_keys == [], f"Metadata not stripped: {meta_keys}"


# ── Legacy Fixture Rejection Test ────────────────────────────────────────────

class TestLegacyFixtureRejection:

    def test_bancamia_cobranzas_rejected(self):
        """Legacy format with parametros_nomina must be rejected."""
        path = TEST_CASES_DIR / "bancamia_cobranzas.json"
        if not path.exists():
            pytest.skip("Legacy fixture not found")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        with pytest.raises(ValueError, match="master-data"):
            SimulationRequest(**data)
