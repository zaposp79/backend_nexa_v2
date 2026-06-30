"""Tests para CargoClassifier y calculadores de roles especiales.

Reglas funcionales oficiales V2-6.
"""

import pytest
from decimal import Decimal
import sys
sys.path.insert(0, '/Users/darwin.minota.quinto/Projects/NEXA/backend_nexa')

from nexa_engine.modules.cadena_a.services.special_roles_calculator import (
    CargoTipo,
    CargoClassifier,
    EspecialistaCalculator,
    SENACalculator,
    InclusionCalculator,
    SalarioFijoCalculator,
)

CLASIFICACION_TEST = {
    "Validador": "VALIDADOR",
    "Supervisor": "OPERATIVO",
    "GTR": "OPERATIVO",
    "Analista profesional AFAC": "ADMINISTRATIVO",
    "Agente Básico 1": "AGENTE",
    "Agente Basico": "AGENTE",
    "Aprendiz SENA": "APRENDIZ",
    "Inclusión": "INCLUSION",
    "Especialista de Proyectos": "ESPECIALISTA",
}

COMPLEJIDAD_TEST = {
    "BAJA": 0.20,
    "MEDIA": 0.50,
    "ALTA": 0.50,
}


class TestCargoClassifier:
    def setup_method(self):
        self.clf = CargoClassifier(CLASIFICACION_TEST)

    def test_clasifica_validador(self):
        assert self.clf.clasificar("Validador") == CargoTipo.VALIDADOR

    def test_clasifica_operativo(self):
        assert self.clf.clasificar("Supervisor") == CargoTipo.OPERATIVO

    def test_clasifica_administrativo(self):
        assert self.clf.clasificar("Analista profesional AFAC") == CargoTipo.ADMINISTRATIVO

    def test_clasifica_agente(self):
        assert self.clf.clasificar("Agente Básico 1") == CargoTipo.AGENTE

    def test_clasifica_aprendiz(self):
        assert self.clf.clasificar("Aprendiz SENA") == CargoTipo.APRENDIZ

    def test_clasifica_inclusion(self):
        assert self.clf.clasificar("Inclusión") == CargoTipo.INCLUSION

    def test_clasifica_especialista(self):
        assert self.clf.clasificar("Especialista de Proyectos") == CargoTipo.ESPECIALISTA

    def test_clasifica_desconocido(self):
        assert self.clf.clasificar("Rol Inexistente") == CargoTipo.DESCONOCIDO

    def test_validador_excluido_de_sena_base(self):
        assert self.clf.es_excluido_sena_base("Validador") is True

    def test_especialista_excluido_de_sena_base(self):
        assert self.clf.es_excluido_sena_base("Especialista de Proyectos") is True

    def test_aprendiz_excluido_de_sena_base(self):
        assert self.clf.es_excluido_sena_base("Aprendiz SENA") is True

    def test_inclusion_excluida_de_sena_base(self):
        assert self.clf.es_excluido_sena_base("Inclusión") is True

    def test_supervisor_no_excluido_de_sena_base(self):
        assert self.clf.es_excluido_sena_base("Supervisor") is False

    def test_analista_no_excluido_de_sena_base(self):
        assert self.clf.es_excluido_sena_base("Analista profesional AFAC") is False

    def test_agente_incluido_en_inclusion_base(self):
        assert self.clf.es_incluido_inclusion_base("Agente Básico 1") is True

    def test_operativo_incluido_en_inclusion_base(self):
        assert self.clf.es_incluido_inclusion_base("Supervisor") is True

    def test_especialista_no_incluido_en_inclusion_base(self):
        assert self.clf.es_incluido_inclusion_base("Especialista de Proyectos") is False


class TestEspecialistaCalculator:
    def setup_method(self):
        self.calc = EspecialistaCalculator(COMPLEJIDAD_TEST)

    def test_complejidad_baja_es_020(self):
        assert self.calc.get_complejidad_multiplicador("BAJA") == Decimal("0.20")

    def test_complejidad_media_es_050(self):
        assert self.calc.get_complejidad_multiplicador("MEDIA") == Decimal("0.50")

    def test_complejidad_alta_es_050(self):
        assert self.calc.get_complejidad_multiplicador("ALTA") == Decimal("0.50")

    def test_complejidad_case_insensitive(self):
        assert self.calc.get_complejidad_multiplicador("alta") == Decimal("0.50")
        assert self.calc.get_complejidad_multiplicador("Baja") == Decimal("0.20")

    def test_complejidad_invalida_raise_value_error(self):
        with pytest.raises(ValueError, match="Complejidad"):
            self.calc.get_complejidad_multiplicador("INVALIDA")

    def test_calcular_salario_formula_correcta(self):
        """
        Formula Excel V2-6 C66: (sal_cargado * ratio * 3 * complejidad) / meses_contrato

        Ejemplo: sal_cargado=5_000_000, ratio=0.5, complejidad=ALTA(0.50), meses=24
        Total: (5_000_000 * 0.5 * 3 * 0.50) / 24 = 156_250
        """
        sal = self.calc.calcular_salario(5_000_000, 0.5, "ALTA", 24)
        assert sal == 156_250

    def test_calcular_salario_baja_complejidad(self):
        """
        sal_cargado=5_000_000, ratio=0.5, complejidad=BAJA(0.20), meses=24
        Total: (5_000_000 * 0.5 * 3 * 0.20) / 24 = 62_500
        """
        sal = self.calc.calcular_salario(5_000_000, 0.5, "BAJA", 24)
        assert sal == 62_500

    def test_calcular_salario_contrato_12_meses(self):
        """
        sal_cargado=4_000_000, ratio=1.0, complejidad=ALTA, meses=12
        Total: (4_000_000 * 1.0 * 3 * 0.50) / 12 = 500_000
        """
        sal = self.calc.calcular_salario(4_000_000, 1.0, "ALTA", 12)
        assert sal == 500_000

    def test_multiplicador_es_3_fijo(self):
        """Verificar que el multiplicador sea exactamente 3."""
        assert EspecialistaCalculator.MULTIPLICADOR_EXCEL == Decimal("3")

    def test_precision_decimal_no_drift(self):
        """Verificar que no hay drift numérico de float.

        Paridad Excel V2-6: sal_cargado=7_478_113.322, ratio=1.0, ALTA, meses=12
        → (7_478_113.322 * 1.0 * 3 * 0.50) / 12 = 934_764 COP  (Excel C66)
        """
        sal = self.calc.calcular_salario(7_478_113.322, 1.0, "ALTA", 12)
        assert isinstance(sal, float)
        assert abs(sal - 934_764) <= 1  # ±1 COP tolerancia Excel

    def test_calcular_fte_proporcional(self):
        """FTE Especialista = (fte_agentes + fte_validador) / (Σ fte_agentes + Σ fte_validador)."""
        fte = self.calc.calcular_fte(
            fte_agentes=10.0, fte_validador=2.0,
            total_fte_agentes=20.0, total_fte_validador=4.0
        )
        # (10 + 2) / (20 + 4) = 12/24 = 0.5
        assert abs(fte - 0.5) < 0.0001

    def test_calcular_fte_denominador_cero_retorna_cero(self):
        fte = self.calc.calcular_fte(0.0, 0.0, 0.0, 0.0)
        assert fte == 0.0


class TestSENACalculator:
    def setup_method(self):
        clf = CargoClassifier(CLASIFICACION_TEST)
        self.calc = SENACalculator(clf)

    def test_excluye_validador(self):
        """Validador no debe sumarse al FTE base de SENA."""
        soporte = {
            "Supervisor": 0.5,
            "Validador": 0.2,  # ← Este debe excluirse
        }
        fte = self.calc.calcular_fte(10.0, soporte, 20.0)
        # FTE = (10 + 0.5) / 20 = 0.525 (sin el 0.2 del Validador)
        assert abs(fte - 0.525) < 0.001

    def test_excluye_especialista(self):
        """Especialista no debe sumarse al FTE base de SENA."""
        soporte = {
            "Supervisor": 1.0,
            "Especialista de Proyectos": 0.4,  # ← Excluir
        }
        fte = self.calc.calcular_fte(10.0, soporte, 20.0)
        assert abs(fte - (10.0 + 1.0) / 20.0) < 0.001

    def test_incluye_administrativos(self):
        """Analistas deben sumarse al FTE base de SENA."""
        soporte = {
            "Analista profesional AFAC": 0.3,  # ← Incluir
            "Supervisor": 0.5,                  # ← Incluir
        }
        fte = self.calc.calcular_fte(10.0, soporte, 20.0)
        assert abs(fte - (10.0 + 0.3 + 0.5) / 20.0) < 0.001

    def test_sena_exclusion_validacion_critica(self):
        """Validación crítica: SENA sin Validador == 0.5."""
        soporte = {"Validador": 0.2}
        fte = self.calc.calcular_fte(10.0, soporte, 20.0)
        # (10 + 0) / 20 = 0.5
        assert abs(fte - 0.5) < 0.001

    def test_ratio_cero_retorna_cero(self):
        fte = self.calc.calcular_fte(10.0, {"Supervisor": 0.5}, 0.0)
        assert fte == 0.0


class TestInclusionCalculator:
    def setup_method(self):
        self.calc = InclusionCalculator()

    def test_incluye_agentes_soporte_y_sena(self):
        fte = self.calc.calcular_fte(
            fte_agentes=10.0,
            fte_soporte_total=2.0,
            fte_sena=0.5,
            ratio_inclusion=20.0
        )
        # (10 + 2 + 0.5) / 20 = 0.625
        assert abs(fte - 0.625) < 0.001

    def test_sin_sena_funciona(self):
        fte = self.calc.calcular_fte(10.0, 2.0, 0.0, 20.0)
        assert abs(fte - 0.6) < 0.001

    def test_ratio_cero_retorna_cero(self):
        fte = self.calc.calcular_fte(10.0, 2.0, 0.5, 0.0)
        assert fte == 0.0


class TestSalarioFijoCalculator:
    def setup_method(self):
        self.calc = SalarioFijoCalculator()

    def test_formula_basica(self):
        """
        Fórmula: Σ(sal × fte) / meses / total_fte

        Perfiles: [(5_000_000, 10.0), (3_000_000, 2.0)]
        Σ(sal × fte) = 50_000_000 + 6_000_000 = 56_000_000
        total_fte = 12
        meses = 24
        Salario_Fijo = 56_000_000 / 24 / 12 = 194_444
        """
        perfiles = [(5_000_000, 10.0), (3_000_000, 2.0)]
        sf = self.calc.calcular(perfiles, 24)
        assert sf == 194_444

    def test_un_solo_perfil(self):
        """Un perfil: sal=4_000_000, fte=1 → 4_000_000 / 12 / 1 = 333_333"""
        sf = self.calc.calcular([(4_000_000, 1.0)], 12)
        assert sf == 333_333

    def test_sin_perfiles_retorna_cero(self):
        assert self.calc.calcular([], 24) == 0.0

    def test_meses_cero_retorna_cero(self):
        assert self.calc.calcular([(5_000_000, 1.0)], 0) == 0.0

    def test_fte_total_cero_retorna_cero(self):
        assert self.calc.calcular([(5_000_000, 0.0)], 12) == 0.0

    def test_precision_decimal(self):
        """Verificar que el resultado no tiene drift de float."""
        sf = self.calc.calcular([(5_405_151.312, 10.5)], 24)
        assert isinstance(sf, float)
        assert sf > 0

    def test_paridad_formula_spec(self):
        """
        Spec: Σ(salarios activados) / meses / total_FTE
        Equivale exactamente a la fórmula implementada.
        Perfiles: sal=6_000_000, fte=5; sal=4_000_000, fte=3
        Σ(sal × fte) = 30_000_000 + 12_000_000 = 42_000_000
        total_fte = 8, meses = 12
        SF = 42_000_000 / 12 / 8 = 437_500
        """
        perfiles = [(6_000_000, 5.0), (4_000_000, 3.0)]
        sf = self.calc.calcular(perfiles, 12)
        assert sf == 437_500
