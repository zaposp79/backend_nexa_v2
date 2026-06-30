"""Tests for HR parametrization enhancements.

Tests the new flexible mapping and automatic dotations conversion.
"""

import pytest
from unittest.mock import MagicMock
from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import PayrollParametrizationRepository


class TestPayrollParametrizationRepository:
    """Tests for PayrollParametrizationRepository enhancements."""

    def test_normalize_handles_accents(self):
        """Test that _normalize strips accents correctly."""
        repo = PayrollParametrizationRepository(None)
        
        assert repo._normalize("Salario Mínimo") == "salario minimo"
        assert repo._normalize("SALARIO MÍNIMO") == "salario minimo"
        assert repo._normalize("salario mínimo") == "salario minimo"

    def test_normalize_removes_parentheses(self):
        """Test that _normalize removes parentheses."""
        repo = PayrollParametrizationRepository(None)
        
        assert repo._normalize("Dotaciones (annual)") == "dotaciones annual"
        assert repo._normalize("Dotaciones (mensual)") == "dotaciones mensual"
        assert repo._normalize("%Cumplimiento Variable") == "cumplimiento variable"

    def test_get_base_salary_data_exact_mapping(self):
        """Test that exact mapping still works (backward compatibility)."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "salarios": [
                {"servicio": "Salario Mínimo", "valor": 1300000},
                {"servicio": "Auxilio Transporte", "valor": 120000},
                {"servicio": "Dotaciones (mensual)", "valor": 50000},
                {"%Cumplimiento Variable": "%Cumplimiento Variable", "valor": 0.10},
            ]
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_base_salary_data()
        
        assert result["salario_minimo"] == 1300000
        assert result["auxilio_transporte"] == 120000
        assert result["dotaciones_mensual"] == 50000

    def test_get_base_salary_data_normalized_mapping(self):
        """Test that normalized mapping works for case-insensitive, accent-insensitive names."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "salarios": [
                {"servicio": "salario minimo", "valor": 1300000},  # lowercase
                {"servicio": "AUXILIO TRANSPORTE", "valor": 120000},  # uppercase
                {"servicio": "Dotaciones (mensual)", "valor": 50000},
                {"servicio": "Cumplimiento Variable", "valor": 0.10},  # no %
            ]
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_base_salary_data()
        
        assert result["salario_minimo"] == 1300000
        assert result["auxilio_transporte"] == 120000
        assert result["dotaciones_mensual"] == 50000

    def test_get_base_salary_data_annual_to_monthly_conversion(self):
        """Test that 'Dotaciones (annual)' is converted to monthly by dividing by 12."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "salarios": [
                {"servicio": "Salario Mínimo", "valor": 1300000},
                {"servicio": "Auxilio Transporte", "valor": 120000},
                {"servicio": "Dotaciones (annual)", "valor": 600000},  # annual
            ]
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_base_salary_data()
        
        # 600000 / 12 = 50000
        assert result["dotaciones_mensual"] == 50000.0

    def test_get_base_salary_data_monthly_takes_precedence(self):
        """Test that 'Dotaciones (mensual)' takes precedence over 'Dotaciones (annual)'."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "salarios": [
                {"servicio": "Salario Mínimo", "valor": 1300000},
                {"servicio": "Auxilio Transporte", "valor": 120000},
                {"servicio": "Dotaciones (mensual)", "valor": 60000},  # mensual comes first
                {"servicio": "Dotaciones (annual)", "valor": 600000},  # annual comes later (should be ignored)
            ]
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_base_salary_data()
        
        # Should use the mensual value (60000), not the annual/12 (50000)
        assert result["dotaciones_mensual"] == 60000.0

    def test_get_base_salary_data_handles_none_values(self):
        """Test that None/missing valores are skipped."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "salarios": [
                {"servicio": "Salario Mínimo", "valor": 1300000},
                {"servicio": "Auxilio Transporte", "valor": None},  # None
                {"servicio": "Dotaciones (mensual)"},  # missing valor key
            ]
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_base_salary_data()
        
        assert result["salario_minimo"] == 1300000
        assert "auxilio_transporte" not in result
        assert "dotaciones_mensual" not in result

    def test_get_reglas_staff_explicit(self):
        """Test that explicit reglas_staff from JSON is used if present."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "reglas_staff": {
                "rol_jefe_comercial": "Gerente Comercial",
                "rol_aprendiz_sena": "Aprendiz SENA",
                "rol_inclusion": "Inclusión",
                "roles_especiales": ["Especialista de Proyectos"],
                "roles_excluidos_ratios": ["Validador"],
            }
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_reglas_staff()
        
        assert result["rol_jefe_comercial"] == "Gerente Comercial"
        assert result["rol_inclusion"] == "Inclusión"

    def test_get_reglas_staff_auto_constructed_from_ratios(self):
        """Test that reglas_staff is auto-constructed when missing."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {
            "ratios": [
                {"servicio": "Cobranzas", "cargo": "Director de cuentas", "agentes": 750},
                {"servicio": "Cobranzas", "cargo": "Aprendiz SENA", "agentes": 20},
                {"servicio": "Cobranzas", "cargo": "Especialista de Proyectos", "agentes": 0},
                {"servicio": "Cobranzas", "cargo": "Validador", "agentes": None},
            ]
        }
        
        repo = PayrollParametrizationRepository(resolver)
        result = repo.get_reglas_staff()
        
        # Should have default values
        assert result["rol_jefe_comercial"] == "Director de cuentas"
        assert result["rol_aprendiz_sena"] == "Aprendiz SENA"
        assert result["rol_inclusion"] == "Inclusión"
        assert "Especialista de Proyectos" in result["roles_especiales"]
        assert "Validador" in result["roles_excluidos_ratios"]

    def test_get_reglas_staff_missing_both_raises_error(self):
        """Test that error is raised if both reglas_staff and ratios are missing."""
        resolver = MagicMock()
        resolver.get_active_hr.return_value = {}
        
        repo = PayrollParametrizationRepository(resolver)
        
        with pytest.raises(Exception):
            repo.get_reglas_staff()


class TestInfrastructureParametrizationRepository:
    """Tests for InfrastructureParametrizationRepository enhancements."""

    def test_normalize_city_removes_suffix(self):
        """Test that _normalize_city removes compound suffixes like ' - Toberin'."""
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import InfrastructureParametrizationRepository
        
        # Test class method
        assert InfrastructureParametrizationRepository._normalize_city("Bogota - Toberin") == "bogota"
        assert InfrastructureParametrizationRepository._normalize_city("Bogota - Americas") == "bogota"
        assert InfrastructureParametrizationRepository._normalize_city("Bogota") == "bogota"

    def test_normalize_city_handles_accents(self):
        """Test that _normalize_city strips accents."""
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import InfrastructureParametrizationRepository
        
        assert InfrastructureParametrizationRepository._normalize_city("Bogotá") == "bogota"
        assert InfrastructureParametrizationRepository._normalize_city("Medellín") == "medellin"
        assert InfrastructureParametrizationRepository._normalize_city("Cúcuta") == "cucuta"

    def test_normalize_city_handles_compound_with_accents(self):
        """Test that _normalize_city handles compound names with accents."""
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import InfrastructureParametrizationRepository
        
        assert InfrastructureParametrizationRepository._normalize_city("Bogotá - Américas") == "bogota"
        assert InfrastructureParametrizationRepository._normalize_city("Medellín - Centro") == "medellin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
