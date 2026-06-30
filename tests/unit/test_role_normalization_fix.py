"""
Test que valida el arreglo de normalización de roles.

Este test verifica que la inconsistencia entre "Director de Performance" en nomina
y "Director de performance" en ratios se resuelve correctamente mediante normalización
de claves de diccionario en get_ratios_staff().
"""

import pytest
from unittest.mock import MagicMock, patch
from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver


class TestRoleNormalizationInRatios:
    """Validar que ratios están normalizados para búsqueda flexible."""

    @pytest.fixture
    def mock_resolver(self):
        """Mock del resolver que devuelve HR data con inconsistencia de mayúsculas."""
        resolver = MagicMock(spec=ParametrizationResolver)
        # Simular los datos HR con inconsistencia: ratios tiene "Director de performance" 
        # (minúscula) pero nomina tiene "Director de Performance" (mayúscula)
        resolver.get_active_hr.return_value = {
            "ratios": [
                {"cargo": "Director de performance", "servicio": "", "agentes": 1200.0},
                {"cargo": "Formadores", "servicio": "", "agentes": 70.0},
                {"cargo": "Monitor de Calidad", "servicio": "", "agentes": 70.0},
                {"cargo": "Supervisor", "servicio": "", "agentes": 20.0},
                {"cargo": "Validador", "servicio": "", "agentes": 50.0},
            ],
            "nomina": [
                {"tipo": "Empleado", "rol": "Director de Performance", "salario": 13000000.0},
                {"tipo": "Empleado", "rol": "Formadores", "salario": 1673000.0},
                {"tipo": "Empleado", "rol": "Monitor de Calidad", "salario": 1747300.0},
                {"tipo": "Empleado", "rol": "Supervisor", "salario": 2513000.0},
                {"tipo": "Empleado", "rol": "Validador", "salario": 1423500.0},
            ],
        }
        return resolver

    def test_ratios_staff_returns_normalized_keys(self, mock_resolver):
        """Verificar que get_ratios_staff() retorna claves normalizadas."""
        repo = PayrollParametrizationRepository(mock_resolver)
        
        ratios = repo.get_ratios_staff("")
        
        # Las claves deben estar normalizadas (lowercase)
        assert "director de performance" in ratios
        assert ratios["director de performance"] == 1200.0
        assert ratios["formadores"] == 70.0
        assert ratios["monitor de calidad"] == 70.0
        assert ratios["supervisor"] == 20.0
        assert ratios["validador"] == 50.0

    def test_normalize_matches_inconsistent_casing(self):
        """Verificar que _normalize() hace que diferentes mayúsculas sean equivalentes."""
        repo = PayrollParametrizationRepository(MagicMock())
        
        # Ambas versiones deben normalizarse a lo mismo
        norm1 = repo._normalize("Director de Performance")
        norm2 = repo._normalize("Director de performance")
        
        assert norm1 == norm2
        assert norm1 == "director de performance"

    def test_context_builder_normalize_rol_method(self):
        """Verificar que SimulationContextBuilder._normalize_rol() funciona igual."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        
        norm1 = SimulationContextBuilder._normalize_rol("Director de Performance")
        norm2 = SimulationContextBuilder._normalize_rol("Director de performance")
        
        assert norm1 == norm2
        assert norm1 == "director de performance"

    def test_ratios_lookup_with_normalized_keys(self, mock_resolver):
        """Verificar que se puede buscar en ratios con claves normalizadas."""
        repo = PayrollParametrizationRepository(mock_resolver)
        ratios = repo.get_ratios_staff("")
        
        # Buscar "Director de Performance" (como viene en nomina)
        norm_key = repo._normalize("Director de Performance")
        
        # Debe encontrar la entrada incluso con casing diferente
        assert norm_key in ratios
        assert ratios[norm_key] == 1200.0

    def test_ratios_returns_all_roles(self, mock_resolver):
        """Verificar que todos los roles se retornan con claves normalizadas."""
        repo = PayrollParametrizationRepository(mock_resolver)
        ratios = repo.get_ratios_staff("")
        
        # Todos los roles deben estar presentes (normalizados)
        expected_roles = [
            "director de performance",
            "formadores",
            "monitor de calidad",
            "supervisor",
            "validador",
        ]
        
        for role in expected_roles:
            assert role in ratios, f"Role '{role}' not found in normalized ratios"
