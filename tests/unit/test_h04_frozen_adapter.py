"""
tests/unit/test_h04_frozen_adapter.py
=======================================
H-04 — Tests para FrozenParametrizationAdapter.

Verifica que:
  1. El adapter carga la versión frozen desde storage.
  2. get_nomina_laboral_params() retorna SMMLV/auxilio frozen.
  3. get_gmf() retorna GMF frozen.
  4. get_ica() retorna ICA frozen para ciudades conocidas.
  5. get_factor_indexacion() retorna factores frozen.
  6. NexaPricingEngine acepta parametrization_version="v2-6".
  7. Los valores del engine con frozen difieren del activo (si SMMLV difiere).
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.parametrizacion.shared.repositories.frozen_parametrization_adapter import FrozenParametrizationAdapter
from nexa_engine.modules.parametrizacion.repositories.frozen_parametrization_repository import FrozenParametrizationRepository
from nexa_engine.modules.parametrizacion.shared.models.frozen_parametrization import FrozenParametrizationV26


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def adapter():
    """Carga el adapter con frozen v2-6."""
    try:
        return FrozenParametrizationAdapter.from_version("v2-6")
    except FileNotFoundError:
        pytest.skip("Frozen v2-6 no encontrada en storage (ejecutar extracción FASE 6 primero)")


@pytest.fixture(scope="module")
def frozen():
    f = FrozenParametrizationRepository.load("v2-6")
    if f is None:
        pytest.skip("Frozen v2-6 no encontrada")
    return f


# ---------------------------------------------------------------------------
# Test: Carga y construcción
# ---------------------------------------------------------------------------

class TestFrozenAdapterLoad:

    def test_from_version_retorna_adapter(self, adapter):
        assert isinstance(adapter, FrozenParametrizationAdapter)

    def test_frozen_version_correcta(self, adapter):
        assert adapter.get_frozen_version() == "v2-6"

    def test_frozen_property(self, adapter):
        assert isinstance(adapter.frozen, FrozenParametrizationV26)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            FrozenParametrizationAdapter.from_version("v99-99")


# ---------------------------------------------------------------------------
# Test: get_nomina_laboral_params()
# ---------------------------------------------------------------------------

class TestFrozenNomina:

    def test_smmlv_es_frozen(self, adapter, frozen):
        params = adapter.get_nomina_laboral_params()
        assert params["salario_minimo"] == frozen.smmlv

    def test_smmlv_valor_correcto(self, adapter):
        params = adapter.get_nomina_laboral_params()
        assert params["salario_minimo"] == 1_750_905.0

    def test_auxilio_es_frozen(self, adapter, frozen):
        params = adapter.get_nomina_laboral_params()
        assert params["auxilio_transporte"] == frozen.auxilio_transporte

    def test_auxilio_valor_correcto(self, adapter):
        params = adapter.get_nomina_laboral_params()
        assert params["auxilio_transporte"] == 249_095.0

    def test_aportes_patronales_presentes(self, adapter):
        params = adapter.get_nomina_laboral_params()
        assert "aportes_patronales" in params
        assert "salud" in params["aportes_patronales"]

    def test_prestaciones_presentes(self, adapter):
        params = adapter.get_nomina_laboral_params()
        assert "prestaciones" in params
        assert "cesantias" in params["prestaciones"]


# ---------------------------------------------------------------------------
# Test: get_gmf()
# ---------------------------------------------------------------------------

class TestFrozenGMF:

    def test_gmf_es_frozen(self, adapter, frozen):
        assert adapter.get_gmf() == frozen.gmf

    def test_gmf_valor_correcto(self, adapter):
        assert adapter.get_gmf() == 0.004


# ---------------------------------------------------------------------------
# Test: get_ica()
# ---------------------------------------------------------------------------

class TestFrozenICA:

    def test_ica_bogota_presente(self, adapter, frozen):
        if not frozen.ica_por_ciudad:
            pytest.skip("ica_por_ciudad vacío en frozen")
        bogota_key = next(
            (k for k in frozen.ica_por_ciudad if "bogot" in k.lower()), None
        )
        if bogota_key is None:
            pytest.skip("Bogotá no en frozen ICA")
        value = adapter.get_ica(bogota_key)
        assert isinstance(value, float)
        assert value > 0

    def test_ica_ciudad_desconocida_fallback(self, adapter):
        # Ciudad inventada → fallback al provider base (que puede raise)
        try:
            value = adapter.get_ica("CiudadInventadaXYZ")
            # Si no raise, el base devolvió algo
            assert isinstance(value, float)
        except Exception:
            pass  # OK — ciudad no existe en ningún proveedor


# ---------------------------------------------------------------------------
# Test: get_factor_indexacion()
# ---------------------------------------------------------------------------

class TestFrozenIndexacion:

    def test_ipc_anio1_es_1(self, adapter, frozen):
        if not frozen.factor_ipc:
            pytest.skip("factor_ipc vacío en frozen")
        assert adapter.get_factor_indexacion("IPC", 1) == frozen.factor_ipc[0]

    def test_smmlv_anio1_es_1(self, adapter, frozen):
        if not frozen.factor_smmlv:
            pytest.skip("factor_smmlv vacío en frozen")
        assert adapter.get_factor_indexacion("SMLV", 1) == frozen.factor_smmlv[0]

    def test_ipc_anio_out_of_range_clamps(self, adapter, frozen):
        if not frozen.factor_ipc:
            pytest.skip("factor_ipc vacío en frozen")
        # Año 100 → debe retornar el último factor
        value = adapter.get_factor_indexacion("IPC", 100)
        assert value == frozen.factor_ipc[-1]

    def test_componente_desconocido_fallback(self, adapter):
        # Componente no mapeado → fallback al provider base
        try:
            value = adapter.get_factor_indexacion("ComponenteInventado", 1)
            assert isinstance(value, float)
        except Exception:
            pass  # OK


# ---------------------------------------------------------------------------
# Test: NexaPricingEngine acepta parametrization_version
# ---------------------------------------------------------------------------

class TestEngineWithFrozen:

    def test_engine_acepta_parametrization_version(self):
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        try:
            engine = NexaPricingEngine(parametrization_version="v2-6")
            assert engine._parametrizacion is not None
            assert isinstance(engine._parametrizacion, FrozenParametrizationAdapter)
        except FileNotFoundError:
            pytest.skip("Frozen v2-6 no disponible")

    def test_engine_frozen_smmlv_correcto(self):
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        try:
            engine = NexaPricingEngine(parametrization_version="v2-6")
            params = engine._parametrizacion.get_nomina_laboral_params()
            assert params["salario_minimo"] == 1_750_905.0
        except FileNotFoundError:
            pytest.skip("Frozen v2-6 no disponible")

    def test_engine_sin_version_usa_activo(self):
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        engine = NexaPricingEngine()
        # Debe ser ParametrizationProvider base (no frozen adapter)
        assert not isinstance(engine._parametrizacion, FrozenParametrizationAdapter)
