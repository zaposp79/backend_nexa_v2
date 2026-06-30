"""
Unit tests for Phase 5.5: Entry Data Contract Enforcement

Validates that:
1. POLLUTION fields (_prefix) are rejected
2. Unknown entry_data sections are rejected
3. Clean input files are accepted
4. Contract is enforced at loader level
"""

import json
import pytest
from pathlib import Path
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_CASES_INPUT = PROJECT_ROOT / "test_cases" / "input"


class TestPhase55ContractEnforcement:
    """Phase 5.5: Entry Data Contract Enforcement"""

    @pytest.fixture
    def loader(self):
        return UserInputLoader()

    def test_reject_pollution_fields_with_underscore(self, loader):
        """MUST reject any field starting with _"""
        data = {
            "panel_de_control": {"cliente": "Test", "linea_negocio": "Test", "meses_contrato": 12, "margen": 0.1, "op_cont": 0.02, "tasa_ica": 0.02, "tasa_gmf": 0.004},
            "_comment": "This is metadata and should be rejected",
        }

        with pytest.raises(ValueError) as exc_info:
            loader.cargar_desde_dict(data)

        assert "PHASE 5.5 CONTRACT VIOLATION" in str(exc_info.value)
        assert "POLLUTION" in str(exc_info.value)
        assert "_comment" in str(exc_info.value)

    def test_reject_multiple_pollution_fields(self, loader):
        """MUST reject multiple POLLUTION fields"""
        data = {
            "panel_de_control": {"cliente": "Test", "linea_negocio": "Test", "meses_contrato": 12, "margen": 0.1, "op_cont": 0.02, "tasa_ica": 0.02, "tasa_gmf": 0.004},
            "_excel_payroll": 30000,
            "_k50_expected": 1000,
            "_source": "Excel V2-4",
        }

        with pytest.raises(ValueError) as exc_info:
            loader.cargar_desde_dict(data)

        error_msg = str(exc_info.value)
        assert "_excel_payroll" in error_msg
        assert "_k50_expected" in error_msg
        assert "_source" in error_msg

    def test_reject_unknown_entry_data_sections(self, loader):
        """MUST reject unknown top-level sections"""
        data = {
            "panel_de_control": {"cliente": "Test", "linea_negocio": "Test", "meses_contrato": 12, "margen": 0.1, "op_cont": 0.02, "tasa_ica": 0.02, "tasa_gmf": 0.004},
            "unknown_section": {"some": "data"},  # Not in contract
        }

        with pytest.raises(ValueError) as exc_info:
            loader.cargar_desde_dict(data)

        assert "PHASE 5.5 CONTRACT VIOLATION" in str(exc_info.value)
        assert "unknown_entry_data_sections" in str(exc_info.value).lower() or "unknown" in str(exc_info.value).lower()

    def test_accept_clean_panel_only(self, loader):
        """MUST accept clean panel_de_control only"""
        data = {
            "panel_de_control": {
                "cliente": "Bancamia",
                "linea_negocio": "Cobranzas",
                "meses_contrato": 12,
                "margen": 0.1339,
                "op_cont": 0.02,
                "tasa_ica": 0.02,
                "tasa_gmf": 0.004,
            }
        }

        result = loader.cargar_desde_dict(data)
        assert result is not None
        assert result.panel.cliente == "Bancamia"

    def test_accept_all_four_cadenas(self, loader):
        """MUST accept all four valid entry_data sections"""
        data = {
            "panel_de_control": {
                "cliente": "Bancamia",
                "linea_negocio": "Cobranzas",
                "meses_contrato": 12,
                "margen": 0.1339,
                "op_cont": 0.02,
                "tasa_ica": 0.02,
                "tasa_gmf": 0.004,
            },
            "condiciones_cadena_a": {"perfiles": []},
            "condiciones_cadena_b": {"canales": []},
            "condiciones_cadena_c": {"canales": []},
        }

        result = loader.cargar_desde_dict(data)
        assert result is not None

    def test_load_clean_input_file(self, loader):
        """MUST load clean input/bancamia_whatsapp_only.json without pollution"""
        input_file = TEST_CASES_INPUT / "bancamia_whatsapp_only.json"

        if not input_file.exists():
            pytest.skip(f"Input file not found: {input_file}")

        result = loader.cargar(str(input_file))
        assert result is not None
        assert result.panel.cliente == "Bancamia"

    def test_load_all_clean_input_files(self, loader):
        """MUST load all clean input files successfully"""
        if not TEST_CASES_INPUT.exists():
            pytest.skip(f"Input directory not found: {TEST_CASES_INPUT}")

        input_files = list(TEST_CASES_INPUT.glob("*.json"))

        if not input_files:
            pytest.skip("No input files found")

        for input_file in input_files[:3]:  # Test first 3
            result = loader.cargar(str(input_file))
            assert result is not None, f"Failed to load {input_file.name}"

    def test_no_underscore_fields_in_input_files(self):
        """MUST verify no _ fields exist in input/*.json files"""
        if not TEST_CASES_INPUT.exists():
            pytest.skip(f"Input directory not found: {TEST_CASES_INPUT}")

        for input_file in TEST_CASES_INPUT.glob("*.json"):
            with open(input_file) as f:
                data = json.load(f)

            pollution_fields = [k for k in data.keys() if k.startswith("_")]
            assert not pollution_fields, f"{input_file.name} contains POLLUTION fields: {pollution_fields}"


class TestPhase55CleanFiles:
    """Verify that clean files structure is correct"""

    def test_input_files_exist(self):
        """Input files must exist after migration"""
        expected_files = [
            "bancamia_whatsapp_only.json",
            "bancamia_excel_match.json",
            "bancamia_canonical_k50.json",
        ]

        for filename in expected_files:
            filepath = TEST_CASES_INPUT / filename
            assert filepath.exists(), f"Expected input file missing: {filepath}"

    def test_input_files_are_valid_json(self):
        """All input files must be valid JSON"""
        for input_file in TEST_CASES_INPUT.glob("*.json"):
            with open(input_file) as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"{input_file.name} is not valid JSON: {e}")

    def test_input_files_have_required_panel(self):
        """All input files must have panel_de_control (legacy) o datos_operativos (NUEVO)."""
        for input_file in TEST_CASES_INPUT.glob("*.json"):
            with open(input_file) as f:
                data = json.load(f)
            # Formato NUEVO usa datos_operativos; el contrato principal sigue siendo panel_de_control.
            if "datos_operativos" in data:
                assert "cliente" in data["datos_operativos"], \
                    f"{input_file.name} datos_operativos missing cliente"
            else:
                assert "panel_de_control" in data, f"{input_file.name} missing panel_de_control"
                assert "cliente" in data["panel_de_control"], \
                    f"{input_file.name} panel missing cliente"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
