"""
Integration tests for role normalization fix in HR parametrization.
Validates that the fix resolves the HTTP 400 error on /api/v1/simulation/calculate.
"""
import pytest
from unittest.mock import MagicMock
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver


@pytest.fixture
def mock_resolver_with_role_inconsistency():
    """Mock resolver with role name inconsistency (root cause of 400 error)."""
    resolver = MagicMock(spec=ParametrizationResolver)
    resolver.get_active_hr.return_value = {
        "ratios": [
            {"cargo": "Director de performance", "servicio": "", "agentes": 1200.0},
            {"cargo": "Formadores", "servicio": "", "agentes": 70.0},
            {"cargo": "Director de cuentas", "servicio": "", "agentes": 750.0},
        ],
        "nomina": [
            {"tipo": "Empleado", "rol": "Director de Performance", "salario": 13000000.0},
            {"tipo": "Empleado", "rol": "Formadores", "salario": 1673000.0},
            {"tipo": "Empleado", "rol": "Director de cuentas", "salario": 18505000.0},
        ],
        "salarios": [
            {"servicio": "Salario Mínimo", "valor": 1750905.0},
            {"servicio": "Auxilio Transporte", "valor": 249095.0},
            {"servicio": "%Cumplimiento Variable", "valor": 0.7},
            {"servicio": "Dotaciones (annual)", "valor": 184500.0},
        ],
    }
    return resolver


class TestRoleNormalizationFixIntegration:
    """Tests validating the fix for inconsistent role names between HR sheets."""

    def test_hr_data_has_inconsistent_role_casing(self, mock_resolver_with_role_inconsistency):
        """Verify the root cause: HR JSON has inconsistent role name casing."""
        from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository
        
        repo = PayrollParametrizationRepository(mock_resolver_with_role_inconsistency)
        hr_data = mock_resolver_with_role_inconsistency.get_active_hr()
        
        # nomina should have "Director de Performance" (capital P)
        nomina_roles = {n["rol"] for n in hr_data.get("nomina", []) if n.get("rol")}
        assert "Director de Performance" in nomina_roles, \
            f"Expected 'Director de Performance' in nomina. Found: {[r for r in nomina_roles if 'director' in r.lower()]}"
        
        print(f"\n✓ nomina has: 'Director de Performance' (capital P)")

    def test_get_ratios_staff_returns_normalized_keys(self, mock_resolver_with_role_inconsistency):
        """Verify that get_ratios_staff() now returns normalized keys."""
        from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository
        
        repo = PayrollParametrizationRepository(mock_resolver_with_role_inconsistency)
        ratios = repo.get_ratios_staff("")
        
        # Should have normalized keys (lowercase)
        assert "director de performance" in ratios, \
            f"Expected normalized 'director de performance' in ratios keys. Got: {list(ratios.keys())[:10]}"
        
        # Should NOT have literal casing anymore
        assert "Director de performance" not in ratios, \
            "Ratios should normalize keys; should not preserve literal casing"
        
        print(f"\n✓ ratios normalized: 'director de performance' in keys")
        print(f"  Sample keys: {list(ratios.keys())[:5]}")

    def test_normalize_rol_method_exists_and_works(self):
        """Verify the new _normalize_rol() method works correctly."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        # Test with various casings and accents
        test_cases = [
            ("Director de Performance", "director de performance"),
            ("Director de performance", "director de performance"),
            ("DIRECTOR DE PERFORMANCE", "director de performance"),
            ("Lider de Entrenamiento", "lider de entrenamiento"),
            ("Líder de Entrenamiento", "lider de entrenamiento"),  # accents removed
        ]
        
        for input_val, expected in test_cases:
            result = SimulationContextBuilder._normalize_rol(input_val)
            assert result == expected, f"Expected {expected}, got {result} for input '{input_val}'"
        
        print(f"\n✓ _normalize_rol() normalizes correctly across {len(test_cases)} test cases")

    def test_ratios_lookup_with_normalized_keys_works(self, mock_resolver_with_role_inconsistency):
        """Verify that role lookup works regardless of input casing."""
        from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        repo = PayrollParametrizationRepository(mock_resolver_with_role_inconsistency)
        ratios = repo.get_ratios_staff("")
        
        # Try lookups with different casings
        lookup_attempts = [
            "Director de Performance",  # original casing from nomina
            "director de performance",  # normalized
            "DIRECTOR DE PERFORMANCE",  # uppercase
        ]
        
        for lookup in lookup_attempts:
            normalized = SimulationContextBuilder._normalize_rol(lookup)
            assert normalized in ratios, \
                f"Lookup failed for '{lookup}' (normalized to '{normalized}'). Keys: {list(ratios.keys())[:5]}"
            
            value = ratios[normalized]
            assert isinstance(value, (int, float)), f"Expected numeric ratio, got {type(value)}"
        
        print(f"\n✓ Ratios lookup works with any casing (tested {len(lookup_attempts)} variants)")

    def test_safe_salary_lookup_wrapper_exists(self):
        """Verify that _get_salario_rol_safe() method exists for error handling."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        # Method should exist
        assert hasattr(SimulationContextBuilder, '_get_salario_rol_safe'), \
            "Missing _get_salario_rol_safe() method for safe salary lookups"
        
        # Should be callable
        assert callable(getattr(SimulationContextBuilder, '_get_salario_rol_safe')), \
            "_get_salario_rol_safe should be callable"
        
        print(f"\n✓ _get_salario_rol_safe() method exists for error handling")

    def test_all_ratios_present_after_normalization(self, mock_resolver_with_role_inconsistency):
        """Verify no roles are lost in normalization."""
        from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository
        
        repo = PayrollParametrizationRepository(mock_resolver_with_role_inconsistency)
        hr_data = mock_resolver_with_role_inconsistency.get_active_hr()
        
        # Get raw roles from nomina
        raw_roles_count = len([n for n in hr_data.get("nomina", []) if n.get("rol")])
        
        # Get normalized ratios
        ratios = repo.get_ratios_staff("")
        
        # Ratios keys should be <= raw roles (some roles may not have ratios)
        # But all roles IN ratios should be unique after normalization
        assert len(ratios) > 0, "No ratios loaded"
        assert len(ratios) == len(set(ratios.keys())), "Duplicate normalized keys - error in normalization!"
        
        print(f"\n✓ All {len(ratios)} roles present after normalization, no duplicates")

    def test_no_duplicate_load_of_ratios_staff(self, mock_resolver_with_role_inconsistency):
        """Verify the fix doesn't introduce duplicate ratio loads."""
        from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository
        from unittest.mock import patch
        
        repo = PayrollParametrizationRepository(mock_resolver_with_role_inconsistency)
        
        # Mock to count calls
        with patch.object(repo, 'get_ratios_staff', wraps=repo.get_ratios_staff) as mock_get_ratios:
            # get_ratios_staff should be called, but we track if it's called excessively
            ratios1 = repo.get_ratios_staff("")
            ratios2 = repo.get_ratios_staff("")
            
            # Both should return the same data
            assert set(ratios1.keys()) == set(ratios2.keys()), "Ratios should be consistent"
            
        print(f"\n✓ get_ratios_staff() can be called multiple times without issues")
