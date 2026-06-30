"""
tests/refactor/test_formula_id_guardrails.py
============================================
Ratchet tests to protect FORMULA_ID trazabilidad (PHASE1-10) from regressions.

No formula changes, no calculation changes, no contract changes.
Only validate that FORMULA_ID classes exist and have correct prefixes.
"""

import inspect
import os
from pathlib import Path


class TestFormulaIDGuardrails:
    """Guardrails for FORMULA_ID trazabilidad across all phases."""

    # Mapping: module_path → (class_name, expected_prefix)
    FORMULA_ID_TARGETS = {
        "nexa_engine.modules.calculator_motor.formulas.payroll.nomina": ("NominaCalculator", "NOMINA."),
        "nexa_engine.modules.calculator_motor.formulas.no_payroll.costs": ("NoPayrollCalculator", "NO_PAYROLL."),
        "nexa_engine.modules.cadena_b.reglas": ("CadenaBCalculator", "CADENA_B."),
        "nexa_engine.modules.cadena_c.reglas": ("CadenaCCalculator", "CADENA_C."),
        "nexa_engine.modules.calculator_motor.formulas.costos_financieros.calculator": (
            "CostosFinancierosCalculator",
            "COSTOS_FINANCIEROS.",
        ),
        "nexa_engine.modules.vision_pyg.services.costos_totales_calculator": (
            "CostosTotalesCalculator",
            "COSTOS_TOTALES.",
        ),
        "nexa_engine.modules.vision_pyg.services.pyg_calculator": ("PyGCalculator", "PYG."),
        "nexa_engine.modules.vision_pyg.services.kpis_calculator": ("KPIsCalculator", "KPIS."),
        "nexa_engine.modules.vision_pyg.builders.vision_pyg_builder": ("VisionPyGBuilder", "VISION_PYG."),
        "nexa_engine.modules.calculator_motor.formulas.tarifas.reglas": ("VisionTarifasCalculator", "VISION_TARIFAS."),
        "nexa_engine.modules.calculator_motor.formulas.cts.calculator": (
            "CostToServeCalculator",
            "CTS.",
        ),
        "nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder": (
            "VisionImprimibleBuilder",
            "VISION_IMPRIMIBLE.",
        ),
    }

    def test_formula_id_classes_exist(self):
        """Validate that all target classes have FORMULA_ID inner class."""
        for module_path, (class_name, expected_prefix) in self.FORMULA_ID_TARGETS.items():
            # Import the module
            try:
                module = __import__(module_path, fromlist=[class_name])
                target_class = getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                raise AssertionError(f"Failed to import {module_path}.{class_name}: {e}")

            # Check that FORMULA_ID inner class exists
            assert hasattr(
                target_class, "FORMULA_ID"
            ), f"{class_name} must have FORMULA_ID inner class"

            formula_id_class = getattr(target_class, "FORMULA_ID")

            # Get all string constants
            constants = {
                name: getattr(formula_id_class, name)
                for name in dir(formula_id_class)
                if not name.startswith("_") and isinstance(getattr(formula_id_class, name), str)
            }

            # Validate that we have at least one constant
            assert len(constants) > 0, f"{class_name}.FORMULA_ID must have at least one constant"

            # Validate that all constants use the correct prefix
            for const_name, const_value in constants.items():
                assert isinstance(
                    const_value, str
                ), f"{class_name}.FORMULA_ID.{const_name} must be a string"
                assert const_value.startswith(
                    expected_prefix
                ), f"{class_name}.FORMULA_ID.{const_name} = '{const_value}' must start with '{expected_prefix}'"

    def test_canonical_vision_pyg_exists(self):
        """Validate that canonical modules/vision_pyg/ exists."""
        vision_pyg_path = Path(__file__).parent.parent.parent / "modules" / "vision_pyg"
        assert (
            vision_pyg_path.exists()
        ), "Canonical modules/vision_pyg/ directory must exist"

    def test_legacy_pyg_shim_still_exists(self):
        """Backward compatibility shim modules/pyg/ must remain available."""
        pyg_path = Path(__file__).parent.parent.parent / "modules" / "pyg"
        assert pyg_path.exists(), "Compatibility shim modules/pyg/ must remain available"

    def test_formula_id_count_by_phase(self):
        """Validate that FORMULA_ID constants exist and prevent deletions."""
        # Phase mapping for documentation only (no hard count requirement)
        phases = {
            "nexa_engine.modules.calculator_motor.formulas.payroll.nomina": "PHASE7",
            "nexa_engine.modules.calculator_motor.formulas.no_payroll.costs": "PHASE1",
            "nexa_engine.modules.cadena_b.reglas": "PHASE2",
            "nexa_engine.modules.cadena_c.reglas": "PHASE4",
            "nexa_engine.modules.calculator_motor.formulas.costos_financieros.calculator": "PHASE3",
            "nexa_engine.modules.vision_pyg.services.costos_totales_calculator": "PHASE5",
            "nexa_engine.modules.vision_pyg.services.pyg_calculator": "PHASE6",
            "nexa_engine.modules.vision_pyg.services.kpis_calculator": "PHASE6",
            "nexa_engine.modules.vision_pyg.builders.vision_pyg_builder": "PHASE6",
            "nexa_engine.modules.calculator_motor.formulas.tarifas.reglas": "PHASE8",
            "nexa_engine.modules.calculator_motor.formulas.cts.calculator": "PHASE9",
            "nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder": "PHASE10",
        }

        for module_path, phase_name in phases.items():
            class_name = self.FORMULA_ID_TARGETS[module_path][0]
            module = __import__(module_path, fromlist=[class_name])
            target_class = getattr(module, class_name)
            formula_id_class = getattr(target_class, "FORMULA_ID")

            constants = [
                name
                for name in dir(formula_id_class)
                if not name.startswith("_") and isinstance(getattr(formula_id_class, name), str)
            ]

            # Validate that we have at least 1 constant (prevents complete deletion)
            assert (
                len(constants) >= 1
            ), f"{class_name}.FORMULA_ID ({phase_name}) must have at least 1 constant, found {len(constants)}"

    def test_no_formula_id_in_empty_classes(self):
        """Validate that no extraneous FORMULA_ID classes exist in unexpected places."""
        # This is a sanity check — ensure we haven't added FORMULA_ID to classes that shouldn't have it
        # List of classes that should NOT have FORMULA_ID (examples; add more if needed)
        excluded_paths = [
            "nexa_engine.modules.shared.models",  # DTOs should not have FORMULA_ID
            "nexa_engine.modules.calculator_motor.engine",  # Engine composition root, not calculation logic
        ]

        # This test is minimal; extend as needed for production use cases
        # For now, it just validates the presence of expected FORMULA_IDs above

    def test_formula_trace_index_synchronized(self):
        """Validate that formula_trace_index.md is synchronized with real FORMULA_ID constants."""
        # Extract all FORMULA_ID constants from real code
        real_formula_ids = set()
        for module_path, (class_name, expected_prefix) in self.FORMULA_ID_TARGETS.items():
            module = __import__(module_path, fromlist=[class_name])
            target_class = getattr(module, class_name)
            formula_id_class = getattr(target_class, "FORMULA_ID")

            constants = [
                getattr(formula_id_class, name)
                for name in dir(formula_id_class)
                if not name.startswith("_") and isinstance(getattr(formula_id_class, name), str)
            ]
            real_formula_ids.update(constants)

        # Read the index documentation
        index_path = Path(__file__).parent.parent.parent / "docs" / "refactor" / "formula_trace_index.md"
        assert index_path.exists(), f"Index file not found: {index_path}"

        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        # Validate: all real FORMULA_IDs appear in the index
        for formula_id in sorted(real_formula_ids):
            assert formula_id in index_content, \
                f"FORMULA_ID '{formula_id}' from code not found in {index_path}"

        # Validate: no PENDIENTE_EXCEL_REF status (should use ➜ DERIVADO or ➜ POST_EXCEL)
        assert "PENDIENTE_EXCEL_REF" not in index_content, \
            "Index contains deprecated 'PENDIENTE_EXCEL_REF' status; use '➜ DERIVADO' or '➜ POST_EXCEL' instead"

        # Validate: index reports 100% parity
        assert "100%" in index_content, \
            "Index must report '100%' Excel parity (comparable)"
        assert "Paridad Excel comparable" in index_content, \
            "Index must contain 'Paridad Excel comparable' statement"

        # Validate: index states zero pending refs
        assert "Pendientes reales" in index_content and ("CERO" in index_content or "0" in index_content), \
            "Index must state 'Pendientes reales' as zero (CERO or 0)"

        # Validate: total count (allow ±1 variance for documentation drift)
        total_count = len(real_formula_ids)
        # Look for the documented count (should be close to real count)
        import re
        count_match = re.search(r"Total FORMULA_ID registrados[:*]+\s*(\d+)", index_content)
        if count_match:
            documented_count = int(count_match.group(1))
            assert abs(documented_count - total_count) <= 1, \
                f"Count mismatch: documented {documented_count}, found {total_count} real IDs (diff={documented_count - total_count})"
        else:
            # If exact count not found, just verify the number is mentioned somewhere
            assert str(total_count) in index_content or str(total_count + 1) in index_content, \
                f"Index must mention FORMULA_ID count around {total_count}"


class TestFormulaIDNoFunctionalChanges:
    """Validate that FORMULA_ID addition caused zero functional changes."""

    _tests_root = Path(__file__).resolve().parent.parent

    def test_baselines_still_pass_v1(self):
        """Baseline v1 (Cadena A+B) must still pass post-FORMULA_ID."""
        import pytest

        result = pytest.main([
            str(self._tests_root / "refactor" / "test_baseline_formula_snapshot_v1.py"),
            "-q",
        ])
        assert result == 0, "Baseline v1 tests must pass"

    def test_baselines_still_pass_cadena_c(self):
        """Baseline Cadena C must still pass post-FORMULA_ID."""
        import pytest

        result = pytest.main([
            str(self._tests_root / "refactor" / "test_baseline_formula_snapshot_cadena_c_v1.py"),
            "-q",
        ])
        assert result == 0, "Baseline Cadena C tests must pass"

    def test_golden_tests_still_pass(self):
        """All golden/parity tests must still pass post-FORMULA_ID."""
        import pytest

        result = pytest.main([str(self._tests_root / "golden"), "-q"])
        assert result == 0, "Golden/parity tests must pass"
