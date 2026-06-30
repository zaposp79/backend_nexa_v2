"""
tests/unit/test_fase6_frozen_parametrization.py
================================================
FASE 6 — Pruebas de parametrización frozen (versionada).

Verifica que:
  1. FrozenParametrizationV26 se carga correctamente desde storage
  2. Contiene todos los parámetros esperados del Excel V2-6
  3. Los valores coinciden exactamente con el Excel
"""

import json
import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.parametrizacion.shared.models.frozen_parametrization import FrozenParametrizationV26
from nexa_engine.modules.parametrizacion.repositories.frozen_parametrization_repository import FrozenParametrizationRepository


# ---------------------------------------------------------------------------
# Fixture: Cargar parametrización frozen v2-6
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def frozen_v26():
    """Carga la parametrización frozen V2-6 desde storage."""
    frozen = FrozenParametrizationRepository.load("v2-6")
    assert frozen is not None, "FrozenParametrizationV26 v2-6 not found in storage"
    return frozen


# ---------------------------------------------------------------------------
# Test: Estructura y presencia de parámetros
# ---------------------------------------------------------------------------

class TestFrozenParametrizationStructure:

    def test_frozen_version_correct(self, frozen_v26):
        assert frozen_v26.version == "v2-6"

    def test_frozen_has_smmlv(self, frozen_v26):
        assert frozen_v26.smmlv > 0
        assert frozen_v26.smmlv == 1_750_905.0

    def test_frozen_has_auxilio(self, frozen_v26):
        assert frozen_v26.auxilio_transporte > 0
        assert frozen_v26.auxilio_transporte == 249_095.0

    def test_frozen_has_indexation_factors(self, frozen_v26):
        # Debe haber al menos 6 factores (años 2025-2030)
        assert len(frozen_v26.factor_ipc) == 6
        assert len(frozen_v26.factor_smmlv) == 6
        assert frozen_v26.factor_ipc[0] == 1.0  # Año 1 siempre es 1.0
        assert frozen_v26.factor_smmlv[0] == 1.0

    def test_frozen_has_poliza_rates(self, frozen_v26):
        assert frozen_v26.poliza_seriedad == 0.005
        assert frozen_v26.poliza_cumplimiento == 0.0062
        assert frozen_v26.poliza_salarios == 0.0119
        assert frozen_v26.poliza_calidad == 0.0119
        assert frozen_v26.poliza_rc_cruzada == 0.0275
        assert frozen_v26.poliza_irf == 0.0275
        assert frozen_v26.poliza_responsabilidad == 0.0069
        assert frozen_v26.poliza_admin_commission == 0.0118

    def test_frozen_has_tax_rates(self, frozen_v26):
        assert frozen_v26.ica_base == pytest.approx(0.01966, abs=0.0001)
        assert frozen_v26.gmf == 0.004
        assert frozen_v26.timbre_nacional == 0.01

    def test_frozen_has_ica_por_ciudad(self, frozen_v26):
        assert len(frozen_v26.ica_por_ciudad) >= 10
        assert "Bogota" in frozen_v26.ica_por_ciudad
        assert frozen_v26.ica_por_ciudad["Bogota"] == pytest.approx(0.00966, abs=0.0001)


# ---------------------------------------------------------------------------
# Test: Valores específicos del Excel V2-6
# ---------------------------------------------------------------------------

class TestFrozenExcelV26Values:

    def test_smmlv_exact_value(self, frozen_v26):
        """SMMLV debe ser exactamente 1,750,905 (2025)."""
        assert frozen_v26.smmlv == 1_750_905.0

    def test_auxilio_exact_value(self, frozen_v26):
        """Auxilio transporte debe ser exactamente 249,095."""
        assert frozen_v26.auxilio_transporte == 249_095.0

    def test_ipc_accumulation_factor_year_2(self, frozen_v26):
        """IPC acumulado año 2 (2026) debe ser ~1.05 (5.27% anual)."""
        assert frozen_v26.factor_ipc[1] == pytest.approx(1.05, abs=0.001)

    def test_smmlv_accumulation_year_2(self, frozen_v26):
        """SMMLV acumulado año 2 debe ser ~1.2378."""
        assert frozen_v26.factor_smmlv[1] == pytest.approx(1.2378, abs=0.001)

    def test_default_absenteeism_rate(self, frozen_v26):
        """Tasa de ausentismo default debe ser 6.5%."""
        assert frozen_v26.absenteeism_default == pytest.approx(0.065, abs=0.001)

    def test_default_rotation_rate(self, frozen_v26):
        """Tasa de rotación default debe ser 8.5%."""
        assert frozen_v26.rotation_default == pytest.approx(0.085, abs=0.001)

    def test_target_margin(self, frozen_v26):
        """Margen objetivo debe ser 18%."""
        assert frozen_v26.target_margin == 0.18

    def test_medical_exam_costs(self, frozen_v26):
        """Costos de exámenes médicos deben estar presentes."""
        assert frozen_v26.medical_exam_cost_bogota > 0
        assert frozen_v26.medical_exam_cost_other > 0
        assert frozen_v26.security_study_preliminary > 0
        assert frozen_v26.security_study_final > 0


# ---------------------------------------------------------------------------
# Test: Serialización / Desserialización
# ---------------------------------------------------------------------------

class TestFrozenSerialization:

    def test_as_dict_produces_valid_dict(self, frozen_v26):
        d = frozen_v26.as_dict()
        assert isinstance(d, dict)
        assert "version" in d
        assert "smmlv" in d
        assert "factor_ipc" in d
        assert "factor_smmlv" in d

    def test_as_dict_json_serializable(self, frozen_v26):
        d = frozen_v26.as_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 1000  # Debe tener bastante contenido

    def test_roundtrip_dict(self, frozen_v26):
        """as_dict() → from_dict() debe producir el mismo objeto."""
        d = frozen_v26.as_dict()
        frozen_reloaded = FrozenParametrizationV26.from_dict(d)
        assert frozen_reloaded.smmlv == frozen_v26.smmlv
        assert frozen_reloaded.ica_base == frozen_v26.ica_base
        assert len(frozen_reloaded.ica_por_ciudad) == len(frozen_v26.ica_por_ciudad)


# ---------------------------------------------------------------------------
# Test: Integración con repositorio
# ---------------------------------------------------------------------------

class TestFrozenRepository:

    def test_repository_loads_v26(self):
        frozen = FrozenParametrizationRepository.load("v2-6")
        assert frozen is not None
        assert frozen.version == "v2-6"

    def test_repository_list_versions(self):
        versions = FrozenParametrizationRepository.list_versions()
        assert "v2-6" in versions

    def test_repository_load_latest(self):
        frozen = FrozenParametrizationRepository.load_latest()
        assert frozen is not None
        assert frozen.version in ["v2-6"]  # Current version
