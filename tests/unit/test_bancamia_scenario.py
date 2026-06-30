"""
Test the exact Bancamia scenario that was failing with HTTP 400.

This test reproduces the user's issue with role name inconsistency
and verifies that the fix allows successful simulation context building.
"""
import pytest
from unittest.mock import MagicMock
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository


@pytest.fixture
def bancamia_resolver():
    """Mock resolver with Bancamia scenario including role inconsistency."""
    resolver = MagicMock(spec=ParametrizationResolver)
    
    # Roles from actual HR JSON: inconsistent casing between nomina and ratios
    resolver.get_active_hr.return_value = {
        "ratios": [
            {"cargo": "Director de cuentas", "servicio": "", "agentes": 750.0},
            {"cargo": "Director de performance", "servicio": "", "agentes": 1200.0},  # lowercase
            {"cargo": "Analista profesional AFAC", "servicio": "", "agentes": 400.0},
            {"cargo": "Agente Básico 1", "servicio": "", "agentes": 1.0},
            {"cargo": "Aprendiz SENA", "servicio": "", "agentes": 20.0},
            {"cargo": "Inclusión", "servicio": "", "agentes": 100.0},
            {"cargo": "Especialista de Proyectos", "servicio": "", "agentes": 0.0},
        ],
        "nomina": [
            {"tipo": "Empleado", "rol": "Director de cuentas", "salario": 18505000.0},
            {"tipo": "Empleado", "rol": "Director de Performance", "salario": 13000000.0},  # uppercase
            {"tipo": "Empleado", "rol": "Analista profesional AFAC", "salario": 2987680.0},
            {"tipo": "Empleado", "rol": "Agente Básico 1", "salario": 2730864.2626},
            {"tipo": "Empleado", "rol": "Aprendiz SENA", "salario": 1423500.0},
            {"tipo": "Empleado", "rol": "Inclusión", "salario": 1423500.0},
            {"tipo": "Empleado", "rol": "Especialista de Proyectos", "salario": 5134560.0},
        ],
        "salarios": [
            {"servicio": "Salario Mínimo", "valor": 1750905.0},
            {"servicio": "Auxilio Transporte", "valor": 249095.0},
            {"servicio": "%Cumplimiento Variable", "valor": 0.7},
            {"servicio": "Dotaciones (annual)", "valor": 184500.0},
        ],
        "seg_social": [
            {"ssparafiscales": "Salud", "proporcion": 0.085},
            {"ssparafiscales": "Fondo de pensión", "proporcion": 0.12},
            {"ssparafiscales": "ARL", "proporcion": 0.00522},
            {"ssparafiscales": "Caja", "proporcion": 0.04},
            {"ssparafiscales": "ICBF + Sena", "proporcion": 0.04},
        ],
        "prestaciones": [
            {"prestaciones": "Cesantías", "valor": 0.0833},
            {"prestaciones": "Primas", "valor": 0.0833},
            {"prestaciones": "Interes a la cesantía", "valor": 0.12},
            {"prestaciones": "Vacaciones", "valor": 0.0417},
        ],
    }
    
    return resolver


@pytest.fixture
def op_resolver():
    """Mock resolver for operational parametrization."""
    resolver = MagicMock()
    resolver.get_active_op.return_value = {
        "ciudades": [
            {
                "ciudad": "Bogota",
                "costo_fijo": {
                    "localidad": "Bogota - Toberin",
                    "valor": 250000.0,
                }
            }
        ]
    }
    return resolver


class TestBancamiaScenario:
    """Test suite for the exact Bancamia scenario that was causing HTTP 400."""

    def test_bancamia_ratios_have_role_inconsistency(self, bancamia_resolver):
        """Verify the root cause is present in test data."""
        hr_data = bancamia_resolver.get_active_hr()
        
        # nomina has uppercase P
        nomina_roles = {n["rol"] for n in hr_data["nomina"]}
        assert "Director de Performance" in nomina_roles
        
        # ratios has lowercase p
        ratio_cargos = {r["cargo"] for r in hr_data["ratios"]}
        assert "Director de performance" in ratio_cargos
        
        # Verify they're different strings
        assert "Director de Performance" != "Director de performance"

    def test_bancamia_get_ratios_normalizes_keys(self, bancamia_resolver):
        """Verify that get_ratios_staff() normalizes keys for case-insensitive lookup."""
        repo = PayrollParametrizationRepository(bancamia_resolver)
        ratios = repo.get_ratios_staff("Cobranzas")
        
        # Should have normalized keys
        assert "director de performance" in ratios
        assert ratios["director de performance"] == 1200.0
        
        # Should NOT have the original casing
        assert "Director de performance" not in ratios

    def test_bancamia_lookup_with_different_casings(self, bancamia_resolver):
        """Verify lookups work with both casings used in the source data."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        repo = PayrollParametrizationRepository(bancamia_resolver)
        ratios = repo.get_ratios_staff("Cobranzas")
        
        # Try both casings
        casings = [
            "Director de Performance",  # From nomina
            "director de performance",  # From ratios
        ]
        
        for casing in casings:
            normalized = SimulationContextBuilder._normalize_rol(casing)
            assert normalized in ratios, f"Lookup failed for '{casing}' (normalized: '{normalized}')"
            assert ratios[normalized] == 1200.0

    def test_bancamia_special_roles_lookup(self, bancamia_resolver):
        """Verify special roles (SENA, Inclusión, Especialista) can be found."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        repo = PayrollParametrizationRepository(bancamia_resolver)
        ratios = repo.get_ratios_staff("Cobranzas")
        
        special_roles = [
            "Aprendiz SENA",
            "Inclusión",
            "Especialista de Proyectos",
        ]
        
        for role in special_roles:
            normalized = SimulationContextBuilder._normalize_rol(role)
            assert normalized in ratios, f"Special role '{role}' not found in ratios"

    def test_bancamia_salary_lookup_for_all_roles(self, bancamia_resolver):
        """Verify salary can be looked up for all roles in nomina."""
        repo = PayrollParametrizationRepository(bancamia_resolver)
        hr_data = bancamia_resolver.get_active_hr()
        
        for nomina_entry in hr_data["nomina"]:
            rol = nomina_entry["rol"]
            
            # Should be able to get salary
            try:
                salary = repo.get_salary_for_role(rol)
                assert salary > 0, f"Salary should be positive for '{rol}'"
            except Exception as e:
                pytest.fail(f"Failed to get salary for role '{rol}': {e}")

    def test_bancamia_base_salary_data_includes_dotations(self, bancamia_resolver):
        """Verify base salary data includes calculated monthly dotations."""
        repo = PayrollParametrizationRepository(bancamia_resolver)
        
        salary_data = repo.get_base_salary_data()
        
        # Should have dotations_mensual calculated
        assert "dotaciones_mensual" in salary_data, \
            f"Missing dotaciones_mensual in salary data. Keys: {salary_data.keys()}"
        
        # Should be annual/12
        expected_monthly = 184500.0 / 12
        assert salary_data["dotaciones_mensual"] == pytest.approx(expected_monthly, rel=0.01), \
            f"Dotations monthly should be {expected_monthly}, got {salary_data['dotaciones_mensual']}"

    def test_bancamia_reglas_staff_constructs_from_ratios(self, bancamia_resolver):
        """Verify reglas_staff is auto-constructed from ratios when not explicit."""
        repo = PayrollParametrizationRepository(bancamia_resolver)
        
        # No explicit reglas in mock, should auto-construct
        try:
            reglas = repo.get_reglas_staff()
            
            # Should have constructed rules with normalized keys
            assert len(reglas) > 0, "Reglas should be auto-constructed from ratios"
            
            # Should have normalized keys
            normalized_keys = list(reglas.keys())
            assert all(key == key.lower() for key in normalized_keys), \
                f"Reglas should have normalized keys, got: {normalized_keys}"
        except Exception as e:
            pytest.fail(f"Failed to get reglas_staff: {e}")

    def test_full_bancamia_context_build_would_not_fail_on_roles(self, bancamia_resolver):
        """
        Simulate the conditions that would cause HTTP 400 in the endpoint.
        
        This test verifies that with the normalization fix, the role lookups
        that were failing would now succeed.
        """
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        repo = PayrollParametrizationRepository(bancamia_resolver)
        
        # Simulate what happens in _construir_perfiles_soporte()
        ratios = repo.get_ratios_staff("Cobranzas")
        
        # Try to find ratios for critical support roles
        critical_roles = [
            ("Director de Performance", 1200.0),  # The problematic role!
            ("Aprendiz SENA", 20.0),
            ("Inclusión", 100.0),
            ("Especialista de Proyectos", 0.0),
        ]
        
        for role, expected_ratio in critical_roles:
            normalized = SimulationContextBuilder._normalize_rol(role)
            
            # This was failing before the fix!
            try:
                actual_ratio = ratios.get(normalized)
                assert actual_ratio == expected_ratio, \
                    f"Ratio mismatch for '{role}': expected {expected_ratio}, got {actual_ratio}"
            except KeyError as e:
                pytest.fail(f"KeyError for role '{role}' (normalized '{normalized}'): {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
