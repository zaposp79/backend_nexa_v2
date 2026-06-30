"""
tests/refactor/test_channel_name_independence.py
=================================================
Validate that channel display names do not affect calculation results.

The `canal` field should be treated as a display label, not a formula key.
Renaming channels should produce numerically identical results while only
display-related fields differ.
"""

import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest

from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder


class TestChannelNameDuplicateValidation:
    """Validate that duplicate channel names within the same section raise ValidationError."""

    @staticmethod
    def _make_data_with_inbound(canales_inbound, canales_outbound=None):
        """Build minimal request dict with given inbound/outbound canal lists."""
        return {
            "volumetria": {
                "inbound": {"canales": canales_inbound},
                "outbound": {"canales": canales_outbound or []},
            }
        }

    def test_exact_duplicate_inbound_raises(self):
        """Exact duplicate canal name within inbound must raise ValidationError."""
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
        from nexa_engine.modules.shared.exceptions import ValidationError

        loader = UserInputLoader()
        data = self._make_data_with_inbound([
            {"canal": "WhatsApp"},
            {"canal": "WhatsApp"},
        ])
        with pytest.raises(ValidationError, match="Canal duplicado"):
            loader._validar_unicidad_canales_por_seccion(data)

    def test_duplicate_with_whitespace_inbound_raises(self):
        """Canal name with leading/trailing spaces is the same as trimmed name — must raise."""
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
        from nexa_engine.modules.shared.exceptions import ValidationError

        loader = UserInputLoader()
        data = self._make_data_with_inbound([
            {"canal": "WhatsApp"},
            {"canal": " WhatsApp "},
        ])
        with pytest.raises(ValidationError, match="Canal duplicado"):
            loader._validar_unicidad_canales_por_seccion(data)

    def test_duplicate_with_different_casing_inbound_raises(self):
        """Canal name differing only in case within inbound must raise ValidationError."""
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
        from nexa_engine.modules.shared.exceptions import ValidationError

        loader = UserInputLoader()
        data = self._make_data_with_inbound([
            {"canal": "WhatsApp"},
            {"canal": "WHATSAPP"},
        ])
        with pytest.raises(ValidationError, match="Canal duplicado"):
            loader._validar_unicidad_canales_por_seccion(data)

    def test_same_name_across_sections_passes(self):
        """Same canal name in inbound AND outbound is valid (sections are independent)."""
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

        loader = UserInputLoader()
        data = self._make_data_with_inbound(
            canales_inbound=[{"canal": "WhatsApp"}],
            canales_outbound=[{"canal": "WhatsApp"}],
        )
        loader._validar_unicidad_canales_por_seccion(data)  # must not raise

    def test_similar_names_within_section_pass(self):
        """WhatsApp, WhatsApp 1, WhatsApp 2 are distinct names — must not raise."""
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

        loader = UserInputLoader()
        data = self._make_data_with_inbound([
            {"canal": "WhatsApp"},
            {"canal": "WhatsApp 1"},
            {"canal": "WhatsApp 2"},
        ])
        loader._validar_unicidad_canales_por_seccion(data)  # must not raise


class TestChannelNameIndependence:
    """Validate that channel names are display-only, not formula drivers."""

    @staticmethod
    def load_request_json():
        """Load the canonical request.json from project root."""
        request_path = Path(__file__).parent.parent.parent / "request" / "request.json"
        with open(request_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def clone_with_renamed_channels(request_data):
        """Clone request_data with channel names changed arbitrarily."""
        cloned = deepcopy(request_data)

        # Mapping: original name -> renamed name (V2-8 canonical deal channels).
        # Suffix "-X" preserves relative alphabetical order within each group:
        #   "Voz 1-X" stays in the V group; "WhatsApp-X" stays in the W group.
        # This validates that renaming display labels does not change numeric outputs.
        rename_map = {
            "Voz 1": "Voz 1-X",
            "WhatsApp": "WhatsApp-X",
            "Voz 2": "Voz 2-X",
        }

        # Rename in inbound canales
        for canal in cloned.get("volumetria", {}).get("inbound", {}).get("canales", []):
            original_name = canal.get("canal")
            if original_name in rename_map:
                canal["canal"] = rename_map[original_name]

        # Rename in outbound canales
        for canal in cloned.get("volumetria", {}).get("outbound", {}).get("canales", []):
            original_name = canal.get("canal")
            if original_name in rename_map:
                canal["canal"] = rename_map[original_name]

        # Rename in escenarios_comerciales (match by modal + original canal name)
        for escenario in cloned.get("escenarios_comerciales", []):
            original_canal = escenario.get("canal")
            if original_canal in rename_map:
                escenario["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_a perfiles (canal field)
        for perfil in (
            cloned.get("condiciones_cadena_a", {}).get("perfiles", [])
        ):
            original_canal = perfil.get("canal")
            if original_canal in rename_map:
                perfil["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_b opex items
        for item in cloned.get("condiciones_cadena_b", {}).get("opex", {}).get("items", []):
            original_canal = item.get("canal")
            if original_canal in rename_map:
                item["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_b inversiones_capex
        for inv in (
            cloned.get("condiciones_cadena_b", {})
            .get("inversiones_capex", [])
        ):
            original_canal = inv.get("canal")
            if original_canal in rename_map:
                inv["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_b costo_variable tarifas_por_canal inbound
        for tarifa in (
            cloned.get("condiciones_cadena_b", {})
            .get("costo_variable", {})
            .get("tarifas_por_canal", {})
            .get("inbound", [])
        ):
            original_canal = tarifa.get("canal")
            if original_canal in rename_map:
                tarifa["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_b costo_variable tarifas_por_canal outbound
        for tarifa in (
            cloned.get("condiciones_cadena_b", {})
            .get("costo_variable", {})
            .get("tarifas_por_canal", {})
            .get("outbound", [])
        ):
            original_canal = tarifa.get("canal")
            if original_canal in rename_map:
                tarifa["canal"] = rename_map[original_canal]

        # Rename in tasa_escalamiento inbound/outbound lists
        for tasa in (
            cloned.get("condiciones_cadena_b", {})
            .get("costo_variable", {})
            .get("tasa_escalamiento", {})
            .get("inbound", [])
        ):
            original_canal = tasa.get("canal")
            if original_canal in rename_map:
                tasa["canal"] = rename_map[original_canal]

        for tasa in (
            cloned.get("condiciones_cadena_b", {})
            .get("costo_variable", {})
            .get("tasa_escalamiento", {})
            .get("outbound", [])
        ):
            original_canal = tasa.get("canal")
            if original_canal in rename_map:
                tasa["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_c tarifa_proveedor_canal items
        for item in (
            cloned.get("condiciones_cadena_c", {})
            .get("tarifa_proveedor_canal", {})
            .get("items", [])
        ):
            original_canal = item.get("canal")
            if original_canal in rename_map:
                item["canal"] = rename_map[original_canal]

        # Rename in condiciones_cadena_c costo_variable tarifas_por_canal inbound
        for tarifa in (
            cloned.get("condiciones_cadena_c", {})
            .get("costo_variable", {})
            .get("tarifas_por_canal", {})
            .get("inbound", [])
        ):
            original_canal = tarifa.get("canal")
            if original_canal in rename_map:
                tarifa["canal"] = rename_map[original_canal]

        return cloned

    def test_channel_names_do_not_affect_calculations(self):
        """Execute engine with original and renamed request; verify numeric parity."""
        # Load and execute original request
        original_request_data = self.load_request_json()
        loader = UserInputLoader()
        user_input_original = loader.cargar_desde_dict(original_request_data)
        builder = SimulationContextBuilder()
        pricing_request_original = builder.construir(user_input_original)

        engine = NexaPricingEngine()
        original_result = engine.calcular(pricing_request_original)

        # Clone and rename, then execute
        renamed_request_data = self.clone_with_renamed_channels(original_request_data)
        user_input_renamed = loader.cargar_desde_dict(renamed_request_data)
        builder2 = SimulationContextBuilder()
        pricing_request_renamed = builder2.construir(user_input_renamed)

        renamed_result = engine.calcular(pricing_request_renamed)

        # Extract numeric fields (exclude display/text fields)
        def extract_numeric_fields(obj, path=""):
            """Recursively extract numeric fields from nested structures."""
            numeric = {}
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Skip display-only fields
                    if key in [
                        "canal",
                        "nombre_canal",
                        "etiqueta",
                        "label",
                        "nombre",
                        "descripcion",
                        "producto",
                        "rubro",
                        "modalidad",
                    ]:
                        continue
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        numeric[new_path] = value
                    elif isinstance(value, (dict, list)):
                        numeric.update(extract_numeric_fields(value, new_path))
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    new_path = f"{path}[{idx}]"
                    numeric.update(extract_numeric_fields(item, new_path))
            return numeric

        # Convert PricingResult to dict for comparison
        original_dict = asdict(original_result)
        renamed_dict = asdict(renamed_result)

        original_numeric = extract_numeric_fields(original_dict)
        renamed_numeric = extract_numeric_fields(renamed_dict)

        # Compare numeric fields
        assert set(original_numeric.keys()) == set(
            renamed_numeric.keys()
        ), "Numeric field structure differs between original and renamed"

        # Check numeric equality (allow small floating-point tolerance)
        tolerance = 1e-6
        mismatches = []
        for key in sorted(original_numeric.keys()):
            orig_val = original_numeric[key]
            renamed_val = renamed_numeric[key]
            if abs(orig_val - renamed_val) > tolerance:
                mismatches.append(
                    f"{key}: original={orig_val}, renamed={renamed_val}, diff={orig_val - renamed_val}"
                )

        assert not mismatches, (
            f"Numeric differences detected after channel rename:\n"
            + "\n".join(mismatches)
        )

    def test_channel_name_consistency_in_display_fields(self):
        """Verify that display names are properly propagated in results."""
        original_request_data = self.load_request_json()
        renamed_request_data = self.clone_with_renamed_channels(original_request_data)

        loader = UserInputLoader()
        user_input_original = loader.cargar_desde_dict(original_request_data)
        builder = SimulationContextBuilder()
        pricing_request_original = builder.construir(user_input_original)

        user_input_renamed = loader.cargar_desde_dict(renamed_request_data)
        builder2 = SimulationContextBuilder()
        pricing_request_renamed = builder2.construir(user_input_renamed)

        engine = NexaPricingEngine()
        original_result = engine.calcular(pricing_request_original)
        renamed_result = engine.calcular(pricing_request_renamed)

        # Extract channel names from results
        def extract_channel_names(result_dict, names=None):
            """Recursively find all 'canal' fields in result."""
            if names is None:
                names = []
            if isinstance(result_dict, dict):
                for key, value in result_dict.items():
                    if key == "canal" and isinstance(value, str):
                        names.append(value)
                    elif isinstance(value, (dict, list)):
                        extract_channel_names(value, names)
            elif isinstance(result_dict, list):
                for item in result_dict:
                    extract_channel_names(item, names)
            return names

        original_result_dict = asdict(original_result)
        renamed_result_dict = asdict(renamed_result)

        original_channels = set(extract_channel_names(original_result_dict))
        renamed_channels = set(extract_channel_names(renamed_result_dict))

        # Note: This is a soft check; exact match depends on result structure.
        # We verify that renamed labels appear in renamed result and
        # original labels appear in original result.
        assert len(original_channels) > 0, "No canal fields found in original result"
        assert len(renamed_channels) > 0, "No canal fields found in renamed result"
        # Renamed labels must appear in renamed result
        assert "Voz 1-X" in renamed_channels, "Voz 1-X should appear in renamed result"
        assert "Voz 2-X" in renamed_channels, "Voz 2-X should appear in renamed result"
        # Original labels must NOT appear in renamed result (they were replaced)
        assert "Voz 1" not in renamed_channels, "Original 'Voz 1' must not appear in renamed result"

    def test_dual_volume_zero_participacion_edge_case(self):
        """
        Validate that when valor > 0 but participacion == 0, results still match.
        This is a valid edge case (volume defined but not participating in cost calc).
        The test is skipped when the canonical deal has no such channel.
        """
        original_request_data = self.load_request_json()

        # Dynamically find any inbound channel with valor > 0 and participacion == 0
        edge_case_canal = None
        for canal in original_request_data.get("volumetria", {}).get("inbound", {}).get("canales", []):
            cadena_b = canal.get("cadena_b", {})
            if cadena_b.get("valor", 0) > 0 and cadena_b.get("participacion", 0) == 0:
                edge_case_canal = canal
                break

        if edge_case_canal is None:
            pytest.skip(
                "No inbound channel with cadena_b.valor > 0 and participacion == 0 "
                "in current canonical deal — edge case not present in V2-8 (SAC/METROCUADRADO)."
            )

        # Execute with original and verify no error
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(original_request_data)
        builder = SimulationContextBuilder()
        pricing_request = builder.construir(user_input)

        engine = NexaPricingEngine()
        result = engine.calcular(pricing_request)
        assert result is not None, "Engine should handle valor>0 + participacion==0"
        assert result.kpis is not None, "Result should have KPIs computed"
